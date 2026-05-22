//! Parser para o log do fail2ban (`/var/log/fail2ban.log`).
//!
//! Formato tipico (uma linha por evento):
//!
//!     2026-05-22 14:23:45,123 fail2ban.filter         [12345]: INFO    [sshd] Found 192.0.2.42
//!     2026-05-22 14:23:50,456 fail2ban.actions        [12345]: NOTICE  [sshd] Ban 192.0.2.42
//!     2026-05-22 15:00:00,789 fail2ban.actions        [12345]: NOTICE  [sshd] Unban 192.0.2.42
//!
//! Estrutura por whitespace:
//!     <date> <time>,<ms>  <logger>  [<pid>]:  <level>  [<jail>] <action> <args...>
//!
//! Em alguns sistemas, fail2ban escreve apenas via syslog (journal). Nesses
//! casos, prefira `--sources journald` e busque por "fail2ban" na TUI.

use std::io::BufRead;

use anyhow::{Context, Result};
use chrono::{DateTime, NaiveDateTime, TimeZone, Utc};
use serde::Serialize;

#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Level {
    Debug,
    Info,
    Notice,
    Warning,
    Error,
    Critical,
}

impl Level {
    fn parse(s: &str) -> Level {
        match s.trim() {
            "DEBUG" => Level::Debug,
            "NOTICE" => Level::Notice,
            "WARNING" => Level::Warning,
            "ERROR" => Level::Error,
            "CRITICAL" => Level::Critical,
            _ => Level::Info,
        }
    }
}

/// Acao do fail2ban. Mapeamento conservador — desconhecidos viram `Other(raw)`.
#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(tag = "kind", rename_all = "lowercase")]
pub enum Action {
    Ban,
    Unban,
    /// IP detectado mas ainda nao banido (counting toward maxretry)
    Found,
    /// fail2ban iniciou jail
    JailStarted,
    /// fail2ban encerrou jail
    JailStopped,
    /// Algum outro evento
    Other { raw: String },
}

impl Action {
    fn parse(first_word: &str, rest: &str) -> Action {
        match first_word {
            "Ban" => Action::Ban,
            "Unban" => Action::Unban,
            "Found" => Action::Found,
            "Jail" if rest.contains("started") => Action::JailStarted,
            "Jail" if rest.contains("stopped") => Action::JailStopped,
            other => Action::Other { raw: other.to_string() },
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct Fail2banEntry {
    pub timestamp: DateTime<Utc>,
    pub level: Level,
    pub logger: String,
    pub pid: Option<u32>,
    pub jail: Option<String>,
    pub action: Action,
    pub ip: Option<String>,
    pub raw_message: String,
}

pub fn parse_line(line: &str) -> Result<Fail2banEntry> {
    // Split por whitespace, mantendo o resto como mensagem
    let mut tokens = line.split_whitespace();
    let date = tokens.next().context("missing date")?;
    let time = tokens.next().context("missing time")?;
    let logger = tokens.next().context("missing logger")?;
    let pid_token = tokens.next().context("missing pid token")?;
    let level_str = tokens.next().context("missing level")?;

    // Junta o resto para preservar espacos internos da mensagem
    let rest: Vec<&str> = tokens.collect();
    let rest_str = rest.join(" ");

    // Timestamp: "YYYY-MM-DD HH:MM:SS,SSS"
    let ts_str = format!("{date} {time}");
    let naive =
        NaiveDateTime::parse_from_str(&ts_str, "%Y-%m-%d %H:%M:%S,%3f")
            .with_context(|| format!("invalid fail2ban timestamp: {ts_str}"))?;
    let timestamp = Utc.from_utc_datetime(&naive);

    // PID: token e' "[12345]:" — extrai os digitos
    let pid = pid_token
        .trim_matches(|c: char| !c.is_ascii_digit())
        .parse()
        .ok();

    let level = Level::parse(level_str);

    // Parse "[jail] <Action> <args>"
    let (jail, action_part) = if let Some(stripped) = rest_str.strip_prefix('[') {
        if let Some(close) = stripped.find(']') {
            let jail = stripped[..close].to_string();
            let after = stripped[close + 1..].trim().to_string();
            (Some(jail), after)
        } else {
            (None, rest_str.clone())
        }
    } else {
        (None, rest_str.clone())
    };

    let mut action_tokens = action_part.split_whitespace();
    let action_word = action_tokens.next().unwrap_or("");
    let action_rest: String = action_tokens.clone().collect::<Vec<_>>().join(" ");
    let action = Action::parse(action_word, &action_rest);

    // IP: primeiro token apos a acao que pareca IP
    let ip = action_tokens.find(|t| looks_like_ip(t)).map(String::from);

    Ok(Fail2banEntry {
        timestamp,
        level,
        logger: logger.to_string(),
        pid,
        jail,
        action,
        ip,
        raw_message: rest_str,
    })
}

fn looks_like_ip(s: &str) -> bool {
    // Heuristica simples: tem ponto OU dois-pontos (IPv4 ou IPv6) e algum digito.
    let has_dot = s.contains('.');
    let has_colon = s.contains(':');
    let has_digit = s.chars().any(|c| c.is_ascii_digit());
    (has_dot || has_colon) && has_digit
}

pub fn parse_log<R: BufRead>(reader: R) -> Result<Vec<Fail2banEntry>> {
    let mut entries = Vec::new();
    for (i, line) in reader.lines().enumerate() {
        let line = line.with_context(|| format!("line {}", i + 1))?;
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        match parse_line(line) {
            Ok(e) => entries.push(e),
            Err(e) => eprintln!("warn: fail2ban line {} ignored: {}", i + 1, e),
        }
    }
    entries.sort_by_key(|e| e.timestamp);
    Ok(entries)
}

#[cfg(test)]
mod tests {
    use super::*;
    use pretty_assertions::assert_eq;

    #[test]
    fn parses_ban_line() {
        let line = "2026-05-22 14:23:50,456 fail2ban.actions        [12345]: NOTICE  [sshd] Ban 192.0.2.42";
        let e = parse_line(line).unwrap();
        assert_eq!(e.level, Level::Notice);
        assert_eq!(e.logger, "fail2ban.actions");
        assert_eq!(e.pid, Some(12345));
        assert_eq!(e.jail.as_deref(), Some("sshd"));
        assert_eq!(e.action, Action::Ban);
        assert_eq!(e.ip.as_deref(), Some("192.0.2.42"));
    }

    #[test]
    fn parses_unban_line() {
        let line = "2026-05-22 15:00:00,789 fail2ban.actions        [12345]: NOTICE  [sshd] Unban 192.0.2.42";
        let e = parse_line(line).unwrap();
        assert_eq!(e.action, Action::Unban);
        assert_eq!(e.ip.as_deref(), Some("192.0.2.42"));
    }

    #[test]
    fn parses_found_line() {
        let line = "2026-05-22 14:23:45,123 fail2ban.filter         [12345]: INFO    [sshd] Found 192.0.2.42";
        let e = parse_line(line).unwrap();
        assert_eq!(e.action, Action::Found);
        assert_eq!(e.level, Level::Info);
    }

    #[test]
    fn parses_jail_started() {
        let line = "2026-05-22 14:00:00,000 fail2ban.jail           [12345]: INFO    Jail 'sshd' started";
        let e = parse_line(line).unwrap();
        assert_eq!(e.action, Action::JailStarted);
    }

    #[test]
    fn parses_ipv6() {
        let line = "2026-05-22 14:23:50,456 fail2ban.actions        [12345]: NOTICE  [sshd] Ban 2001:db8::1";
        let e = parse_line(line).unwrap();
        assert_eq!(e.action, Action::Ban);
        assert_eq!(e.ip.as_deref(), Some("2001:db8::1"));
    }
}
