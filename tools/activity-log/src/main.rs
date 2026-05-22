//! vigia-log — CLI/TUI para `vigia-activity-log`.

mod audit;
mod narrator;
mod tui;

use std::fs::File;
use std::io::{self, BufReader};

use anyhow::{Context, Result};
use clap::{Parser, ValueEnum};

use crate::audit::{parse_log, AuditEvent};
use crate::narrator::narrate;

#[derive(Parser, Debug)]
#[command(
    name = "vigia-log",
    about = "Parseia audit.log com narrativa human-readable. Parte da Vigia Suite.",
    version
)]
struct Cli {
    /// Caminho do audit.log. Use '-' para ler de stdin. Default: /var/log/audit/audit.log
    #[arg(short, long, default_value = "/var/log/audit/audit.log")]
    path: String,

    /// Formato de saida.
    #[arg(short, long, value_enum, default_value_t = Output::Tui)]
    output: Output,

    /// Numero maximo de eventos a mostrar (mais recentes). 0 = todos.
    #[arg(short, long, default_value_t = 500)]
    limit: usize,
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

    let events = load_events(&cli.path)?;
    let events = if cli.limit > 0 && events.len() > cli.limit {
        let skip = events.len() - cli.limit;
        events.into_iter().skip(skip).collect()
    } else {
        events
    };

    match cli.output {
        Output::Tui => tui::run(events)?,
        Output::Text => print_text(&events),
        Output::Json => print_json(&events)?,
    }
    Ok(())
}

fn load_events(path: &str) -> Result<Vec<AuditEvent>> {
    if path == "-" {
        let stdin = io::stdin();
        let reader = BufReader::new(stdin.lock());
        parse_log(reader)
    } else {
        let f = File::open(path).with_context(|| {
            format!(
                "abrir {} (lembre que /var/log/audit/audit.log geralmente \
                 exige sudo para leitura)",
                path
            )
        })?;
        parse_log(BufReader::new(f))
    }
}

fn print_text(events: &[AuditEvent]) {
    for ev in events {
        println!("{}", narrate(ev));
    }
}

fn print_json(events: &[AuditEvent]) -> Result<()> {
    let stdout = io::stdout();
    let mut out = stdout.lock();
    for ev in events {
        serde_json::to_writer(&mut out, ev)?;
        use std::io::Write;
        out.write_all(b"\n")?;
    }
    Ok(())
}
