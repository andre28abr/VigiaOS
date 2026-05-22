//! vigia-log — CLI/TUI para `vigia-activity-log`.

mod audit;
mod event;
mod fail2ban;
mod journal;
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
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    let mut events = load_events(&cli)?;

    // Ordena cronologicamente para mostrar audit + journal interleavados.
    events.sort_by_key(Event::timestamp);

    // Limita aos N mais recentes
    if cli.limit > 0 && events.len() > cli.limit {
        let skip = events.len() - cli.limit;
        events = events.into_iter().skip(skip).collect();
    }

    match cli.output {
        Output::Tui => tui::run(events)?,
        Output::Text => print_text(&events),
        Output::Json => print_json(&events)?,
    }
    Ok(())
}

fn load_events(cli: &Cli) -> Result<Vec<Event>> {
    let mut all: Vec<Event> = Vec::new();

    if cli.sources.contains(&Source::Audit) {
        let audit_events = load_audit(&cli.audit_path)?;
        all.extend(audit_events.into_iter().map(Event::Audit));
    }

    if cli.sources.contains(&Source::Journald) {
        let journal_entries = match &cli.journal_path {
            Some(path) => load_journal_file(path)?,
            None => journal::fetch_via_journalctl(cli.limit.max(500))?,
        };
        all.extend(journal_entries.into_iter().map(Event::Journal));
    }

    if cli.sources.contains(&Source::Fail2ban) {
        let f2b = load_fail2ban(&cli.fail2ban_path)?;
        all.extend(f2b.into_iter().map(Event::Fail2ban));
    }

    Ok(all)
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

fn print_text(events: &[Event]) {
    for ev in events {
        println!("[{}] {}", ev.source(), narrate(ev));
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
