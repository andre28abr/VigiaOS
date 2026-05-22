//! Live tail mode — re-le periodicamente as fontes e devolve apenas eventos novos.
//!
//! Estrategia: polling, nao inotify. Mais simples e tolerante a edge cases
//! (file rotation, atomic writes). Re-le o arquivo inteiro de audit/fail2ban
//! e filtra por timestamp > ultimo visto. Para journald, usa `--since` no
//! journalctl com o ultimo timestamp visto.
//!
//! Custo: re-parse de arquivo pequeno (<10MB) em cada refresh leva <50ms.
//! Para arquivos maiores, otimizacao com offset fica para v0.8.

use std::process::{Command, Stdio};

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};

use crate::event::Event;
use crate::{audit, fail2ban, journal};

/// Fontes habilitadas em live mode + estado do ultimo timestamp visto por source.
pub struct LiveSources {
    audit: Option<String>,
    /// None = (audit habilitado, mas nao em live)
    /// Some(None) = (live com journalctl ao vivo)
    /// Some(Some(path)) = (live com arquivo journal — pouco util, mas suportado)
    journal: Option<Option<String>>,
    fail2ban: Option<String>,
    last_audit_ts: Option<DateTime<Utc>>,
    last_journal_ts: Option<DateTime<Utc>>,
    last_fail2ban_ts: Option<DateTime<Utc>>,
}

impl LiveSources {
    pub fn new(
        audit_path: Option<String>,
        journal_path: Option<Option<String>>,
        fail2ban_path: Option<String>,
    ) -> Self {
        Self {
            audit: audit_path,
            journal: journal_path,
            fail2ban: fail2ban_path,
            last_audit_ts: None,
            last_journal_ts: None,
            last_fail2ban_ts: None,
        }
    }

    /// Inicializa os timestamps "ja visto" com o ultimo evento de cada source
    /// nos eventos carregados inicialmente. Evita re-emitir eventos no primeiro refresh.
    pub fn init_with_seen(&mut self, events: &[Event]) {
        for e in events {
            match e {
                Event::Audit(a) => {
                    if self.last_audit_ts.map(|t| a.timestamp > t).unwrap_or(true) {
                        self.last_audit_ts = Some(a.timestamp);
                    }
                }
                Event::Journal(j) => {
                    if self.last_journal_ts.map(|t| j.timestamp > t).unwrap_or(true) {
                        self.last_journal_ts = Some(j.timestamp);
                    }
                }
                Event::Fail2ban(f) => {
                    if self.last_fail2ban_ts.map(|t| f.timestamp > t).unwrap_or(true) {
                        self.last_fail2ban_ts = Some(f.timestamp);
                    }
                }
            }
        }
    }

    /// Le todas as fontes habilitadas e devolve eventos com timestamp > ultimo visto.
    /// Atualiza os "ultimo visto" para refletir os novos timestamps.
    pub fn refresh(&mut self) -> Result<Vec<Event>> {
        let mut out: Vec<Event> = Vec::new();

        if let Some(path) = self.audit.clone() {
            let all = read_audit_file(&path)?;
            let cutoff = self.last_audit_ts;
            let new: Vec<_> = all
                .into_iter()
                .filter(|e| cutoff.map(|t| e.timestamp > t).unwrap_or(true))
                .collect();
            if let Some(max) = new.iter().map(|e| e.timestamp).max() {
                self.last_audit_ts = Some(max);
            }
            out.extend(new.into_iter().map(Event::Audit));
        }

        if let Some(journal_path) = self.journal.clone() {
            let new = match journal_path {
                Some(path) => {
                    let all = read_journal_file(&path)?;
                    let cutoff = self.last_journal_ts;
                    all.into_iter()
                        .filter(|e| cutoff.map(|t| e.timestamp > t).unwrap_or(true))
                        .collect::<Vec<_>>()
                }
                None => fetch_journalctl_since(self.last_journal_ts)?,
            };
            if let Some(max) = new.iter().map(|e| e.timestamp).max() {
                self.last_journal_ts = Some(max);
            }
            out.extend(new.into_iter().map(Event::Journal));
        }

        if let Some(path) = self.fail2ban.clone() {
            let all = read_fail2ban_file(&path)?;
            let cutoff = self.last_fail2ban_ts;
            let new: Vec<_> = all
                .into_iter()
                .filter(|e| cutoff.map(|t| e.timestamp > t).unwrap_or(true))
                .collect();
            if let Some(max) = new.iter().map(|e| e.timestamp).max() {
                self.last_fail2ban_ts = Some(max);
            }
            out.extend(new.into_iter().map(Event::Fail2ban));
        }

        out.sort_by_key(|e| e.timestamp());
        Ok(out)
    }
}

fn read_audit_file(path: &str) -> Result<Vec<audit::AuditEvent>> {
    let f = std::fs::File::open(path).with_context(|| format!("abrir {path}"))?;
    audit::parse_log(std::io::BufReader::new(f))
}

fn read_journal_file(path: &str) -> Result<Vec<journal::JournalEntry>> {
    let f = std::fs::File::open(path).with_context(|| format!("abrir {path}"))?;
    journal::parse_log(std::io::BufReader::new(f))
}

fn read_fail2ban_file(path: &str) -> Result<Vec<fail2ban::Fail2banEntry>> {
    let f = std::fs::File::open(path).with_context(|| format!("abrir {path}"))?;
    fail2ban::parse_log(std::io::BufReader::new(f))
}

/// Roda `journalctl --since '@<epoch>' -o json --no-pager`. Se nao houver
/// timestamp anterior (primeiro refresh), pega so os ultimos 100 para nao
/// inundar.
fn fetch_journalctl_since(
    since: Option<DateTime<Utc>>,
) -> Result<Vec<journal::JournalEntry>> {
    let mut cmd = Command::new("journalctl");
    cmd.args(["-o", "json", "--no-pager"]);

    if let Some(ts) = since {
        // journalctl aceita "@<unix_seconds>" como --since
        cmd.arg(format!("--since=@{}", ts.timestamp()));
    } else {
        cmd.arg("-n100");
    }

    let output = cmd.stderr(Stdio::inherit()).output().context("journalctl spawn")?;
    if !output.status.success() {
        anyhow::bail!("journalctl falhou com status {}", output.status);
    }
    let cursor = std::io::Cursor::new(output.stdout);
    journal::parse_log(cursor)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use std::path::PathBuf;

    fn write_audit_line(path: &PathBuf, ts: u64, audit_id: u64) {
        let mut f = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .unwrap();
        writeln!(
            f,
            "type=SYSCALL msg=audit({ts}.0:{audit_id}): arch=x syscall=1 success=yes exit=0 comm=\"t\""
        )
        .unwrap();
    }

    #[test]
    fn refresh_only_returns_new_events() {
        let tmp = std::env::temp_dir().join(format!("vigia-live-test-{}.log", std::process::id()));
        let _ = std::fs::remove_file(&tmp);

        // 2 eventos iniciais
        write_audit_line(&tmp, 1748000000, 100);
        write_audit_line(&tmp, 1748000010, 101);

        let mut live = LiveSources::new(Some(tmp.to_string_lossy().into()), None, None);

        // Primeiro refresh: traz os 2
        let first = live.refresh().unwrap();
        assert_eq!(first.len(), 2);

        // Segundo refresh sem mudanca: 0
        let second = live.refresh().unwrap();
        assert_eq!(second.len(), 0);

        // Adiciona 1 evento novo (timestamp posterior)
        write_audit_line(&tmp, 1748000020, 102);

        // Terceiro refresh: traz so o novo
        let third = live.refresh().unwrap();
        assert_eq!(third.len(), 1, "deveria trazer so o evento novo");

        let _ = std::fs::remove_file(&tmp);
    }
}
