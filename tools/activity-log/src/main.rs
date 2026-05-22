//! vigia-log — CLI/TUI para `vigia-activity-log`.

mod audit;
mod correlator;
mod event;
mod fail2ban;
mod journal;
mod live;
mod narrator;
mod tui;

use std::fs::File;
use std::io::{self, BufRead, BufReader};

use anyhow::{Context, Result};
use clap::{Parser, ValueEnum};

use crate::event::Event;
use crate::narrator::narrate;

#[derive(Parser, Debug)]
#[command(
    name = "vigia-log",
    about = "Parseia audit.log e journald com narrativa human-readable. Parte da Vigia Suite.",
    version
)]
struct Cli {
    /// Fontes de log a carregar. Pode passar multiplas.
    /// Default: apenas audit.
    #[arg(
        short, long,
        value_enum,
        num_args = 1..,
        default_value = "audit"
    )]
    sources: Vec<Source>,

    /// Path do audit.log. Use '-' para stdin. Default: /var/log/audit/audit.log.
    /// Ignorado se 'audit' nao estiver em --sources.
    #[arg(long, default_value = "/var/log/audit/audit.log")]
    audit_path: String,

    /// Path para um snapshot JSON do journal (gerado com
    /// `journalctl -o json --no-pager > arquivo`). Se omitido, usa
    /// `journalctl` vivo. Ignorado se 'journald' nao estiver em --sources.
    #[arg(long)]
    journal_path: Option<String>,

    /// Path do log do fail2ban. Default: /var/log/fail2ban.log.
    /// Ignorado se 'fail2ban' nao estiver em --sources.
    #[arg(long, default_value = "/var/log/fail2ban.log")]
    fail2ban_path: String,

    /// Formato de saida.
    #[arg(short, long, value_enum, default_value_t = Output::Tui)]
    output: Output,

    /// Numero maximo de eventos mais recentes. 0 = todos.
    #[arg(short, long, default_value_t = 500)]
    limit: usize,

    /// Filtra por severidade minima. Default: mostra todos.
    /// Valores: routine, interesting, suspicious.
    #[arg(long)]
    min_severity: Option<SevArg>,

    /// Live tail: re-le as fontes periodicamente e adiciona eventos novos.
    /// So funciona com output=tui. Default: false.
    #[arg(short = 'f', long)]
    follow: bool,

    /// Intervalo de refresh em live mode, em segundos.
    #[arg(long, default_value_t = 2)]
    refresh_interval: u64,
}

#[derive(Copy, Clone, Debug, ValueEnum)]
enum SevArg {
    Routine,
    Interesting,
    Suspicious,
}

impl From<SevArg> for crate::event::Severity {
    fn from(s: SevArg) -> Self {
        match s {
            SevArg::Routine => crate::event::Severity::Routine,
            SevArg::Interesting => crate::event::Severity::Interesting,
            SevArg::Suspicious => crate::event::Severity::Suspicious,
        }
    }
}

#[derive(Copy, Clone, Debug, ValueEnum, PartialEq, Eq)]
enum Source {
    /// /var/log/audit/audit.log (Linux Audit)
    Audit,
    /// systemd journal (via journalctl ou arquivo)
    Journald,
    /// /var/log/fail2ban.log
    Fail2ban,
}

#[derive(Copy, Clone, Debug, ValueEnum)]
enum Output {
    /// Interface TUI interativa (default)
    Tui,
    /// Lista textual com narrativa
    Text,
    /// JSON estruturado (uma linha por evento)
    Json,
    /// Apenas correlations (narrativas sintetizadas)
    Correlations,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    let mut events = load_events(&cli)?;

    // Ordena cronologicamente para mostrar audit + journal interleavados.
    events.sort_by_key(Event::timestamp);

    // Filtro de severidade minima (aplicado ANTES do limit para nao perder
    // eventos importantes para amostragem por janela).
    if let Some(sev) = cli.min_severity {
        let min: event::Severity = sev.into();
        events.retain(|e| e.severity() >= min);
    }

    // Limita aos N mais recentes
    if cli.limit > 0 && events.len() > cli.limit {
        let skip = events.len() - cli.limit;
        events = events.into_iter().skip(skip).collect();
    }

    let correlations = correlator::correlate(&events);

    // Live mode so faz sentido em TUI
    let live = if cli.follow && matches!(cli.output, Output::Tui) {
        let mut ls = live::LiveSources::new(
            cli.sources.contains(&Source::Audit).then(|| cli.audit_path.clone()),
            cli.sources.contains(&Source::Journald).then(|| cli.journal_path.clone()),
            cli.sources.contains(&Source::Fail2ban).then(|| cli.fail2ban_path.clone()),
        );
        ls.init_with_seen(&events);
        Some((ls, std::time::Duration::from_secs(cli.refresh_interval.max(1))))
    } else {
        None
    };

    match cli.output {
        Output::Tui => tui::run(events, correlations, live)?,
        Output::Text => print_text(&events, &correlations),
        Output::Json => print_json(&events)?,
        Output::Correlations => print_correlations(&correlations),
    }
    Ok(())
}

fn load_events(cli: &Cli) -> Result<Vec<Event>> {
    let mut all: Vec<Event> = Vec::new();

    if cli.sources.contains(&Source::Audit) {
        if file_exists_or_stdin(&cli.audit_path) {
            let audit_events = load_audit(&cli.audit_path)?;
            all.extend(audit_events.into_iter().map(Event::Audit));
        } else {
            eprintln!(
                "warn: source 'audit' habilitado mas {} nao existe — pulando \
                 (instale auditd ou use --audit-path para outro arquivo)",
                cli.audit_path
            );
        }
    }

    if cli.sources.contains(&Source::Journald) {
        let journal_entries = match &cli.journal_path {
            Some(path) => {
                if file_exists_or_stdin(path) {
                    load_journal_file(path)?
                } else {
                    eprintln!("warn: source 'journald' arquivo {} nao existe — pulando", path);
                    Vec::new()
                }
            }
            None => journal::fetch_via_journalctl(cli.limit.max(500))
                .unwrap_or_else(|e| {
                    eprintln!("warn: source 'journald' falhou ({e}) — pulando");
                    Vec::new()
                }),
        };
        all.extend(journal_entries.into_iter().map(Event::Journal));
    }

    if cli.sources.contains(&Source::Fail2ban) {
        if file_exists_or_stdin(&cli.fail2ban_path) {
            let f2b = load_fail2ban(&cli.fail2ban_path)?;
            all.extend(f2b.into_iter().map(Event::Fail2ban));
        } else {
            eprintln!(
                "warn: source 'fail2ban' habilitado mas {} nao existe — pulando \
                 (instale fail2ban via rpm-ostree ou remova fail2ban de --sources)",
                cli.fail2ban_path
            );
        }
    }

    Ok(all)
}

fn file_exists_or_stdin(path: &str) -> bool {
    path == "-" || std::path::Path::new(path).exists()
}

fn load_fail2ban(path: &str) -> Result<Vec<fail2ban::Fail2banEntry>> {
    let reader: Box<dyn BufRead> = if path == "-" {
        Box::new(BufReader::new(io::stdin()))
    } else {
        let f = File::open(path).with_context(|| {
            format!(
                "abrir {} (alguns sistemas escrevem fail2ban so no journal — \
                 nesse caso use --sources journald e busque \"fail2ban\")",
                path
            )
        })?;
        Box::new(BufReader::new(f))
    };
    fail2ban::parse_log(reader)
}

fn load_audit(path: &str) -> Result<Vec<audit::AuditEvent>> {
    if path == "-" {
        let stdin = io::stdin();
        let reader = BufReader::new(stdin.lock());
        audit::parse_log(reader)
    } else {
        let f = File::open(path).with_context(|| {
            format!(
                "abrir {} (lembre que /var/log/audit/audit.log geralmente exige sudo)",
                path
            )
        })?;
        audit::parse_log(BufReader::new(f))
    }
}

fn load_journal_file(path: &str) -> Result<Vec<journal::JournalEntry>> {
    let reader: Box<dyn BufRead> = if path == "-" {
        Box::new(BufReader::new(io::stdin()))
    } else {
        let f = File::open(path).with_context(|| format!("abrir {}", path))?;
        Box::new(BufReader::new(f))
    };
    journal::parse_log(reader)
}

fn print_text(events: &[Event], correlations: &[correlator::Correlation]) {
    if !correlations.is_empty() {
        println!("=== Correlations ({}) ===", correlations.len());
        for (n, c) in correlations.iter().enumerate() {
            let sev_tag = match c.severity {
                event::Severity::Suspicious => "[SUSP]",
                event::Severity::Interesting => "[INFO]",
                event::Severity::Routine => "[----]",
            };
            println!(
                "{} {} {} ({} eventos)",
                sev_tag,
                c.timestamp.format("%H:%M:%S"),
                c.summary,
                c.contributing.len()
            );
            let _ = n;
        }
        println!("\n=== Events ({}) ===", events.len());
    }
    for ev in events {
        println!("[{}] {}", ev.source(), narrate(ev));
    }
}

fn print_correlations(correlations: &[correlator::Correlation]) {
    if correlations.is_empty() {
        println!("(nenhuma correlation detectada)");
        return;
    }
    for c in correlations {
        let sev_tag = match c.severity {
            event::Severity::Suspicious => "[SUSP]",
            event::Severity::Interesting => "[INFO]",
            event::Severity::Routine => "[----]",
        };
        println!(
            "{} {} - {} - {} (kind={}, eventos={})",
            sev_tag,
            c.timestamp.format("%Y-%m-%d %H:%M:%S"),
            c.summary,
            (c.end - c.timestamp).num_seconds(),
            c.kind,
            c.contributing.len()
        );
    }
}

fn print_json(events: &[Event]) -> Result<()> {
    use std::io::Write;
    let stdout = io::stdout();
    let mut out = stdout.lock();
    for ev in events {
        serde_json::to_writer(&mut out, ev)?;
        out.write_all(b"\n")?;
    }
    Ok(())
}
