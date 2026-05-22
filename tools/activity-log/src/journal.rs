//! Parser e loader para `systemd-journald`.
//!
//! Estrategia: spawn `journalctl -o json --no-pager` e parse line-by-line
//! como JSON. Mais simples e portavel que ligar em libsystemd via FFI.
//!
//! Para testes (e dev em Mac sem systemd), aceita tambem um arquivo
//! ou stdin com mesmo formato JSON-lines.
//!
//! Formato journalctl JSON: cada linha eh um objeto. Valores sao SEMPRE
//! strings (mesmo numericos), e `__REALTIME_TIMESTAMP` eh microssegundos
//! desde epoch.

use std::collections::HashMap;
use std::io::BufRead;
use std::process::{Command, Stdio};

use anyhow::{bail, Context, Result};
use chrono::{DateTime, TimeZone, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Niveis syslog (RFC 3164). Ordem do mais critico para o menos.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[serde(rename_all = "lowercase")]
pub enum Priority {
    Emerg,
    Alert,
    Crit,
    Err,
    Warning,
    Notice,
    Info,
    Debug,
}

impl Priority {
    pub fn from_syslog_num(p: u8) -> Priority {
        match p {
            0 => Priority::Emerg,
            1 => Priority::Alert,
            2 => Priority::Crit,
            3 => Priority::Err,
            4 => Priority::Warning,
            5 => Priority::Notice,
            6 => Priority::Info,
            _ => Priority::Debug,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Priority::Emerg => "emerg",
            Priority::Alert => "alert",
            Priority::Crit => "crit",
            Priority::Err => "err",
            Priority::Warning => "warning",
            Priority::Notice => "notice",
            Priority::Info => "info",
            Priority::Debug => "debug",
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct JournalEntry {
    pub timestamp: DateTime<Utc>,
    pub priority: Priority,
    pub message: String,
    pub unit: Option<String>,
    pub comm: Option<String>,
    pub pid: Option<u32>,
    pub uid: Option<u32>,
    pub hostname: Option<String>,
    /// Outras chaves do journal nao mapeadas explicitamente.
    pub extra: HashMap<String, String>,
}

/// Chaves que mapeamos para campos top-level. Nao vao para `extra`.
const TOP_LEVEL_KEYS: &[&str] = &[
    "__REALTIME_TIMESTAMP",
    "PRIORITY",
    "MESSAGE",
    "_SYSTEMD_UNIT",
    "UNIT",
    "_COMM",
    "_PID",
    "_UID",
    "_HOSTNAME",
];

pub fn parse_json_line(line: &str) -> Result<JournalEntry> {
    let json: Value = serde_json::from_str(line).context("invalid json line")?;
    let obj = json.as_object().context("expected json object")?;

    // timestamp: __REALTIME_TIMESTAMP eh microssegundos
    let ts_str = obj
        .get("__REALTIME_TIMESTAMP")
        .and_then(Value::as_str)
        .context("missing __REALTIME_TIMESTAMP")?;
    let ts_us: i64 = ts_str.parse().context("invalid timestamp")?;
    let secs = ts_us / 1_000_000;
    let nsecs = ((ts_us % 1_000_000) * 1000) as u32;
    let timestamp = Utc
        .timestamp_opt(secs, nsecs)
        .single()
        .context("epoch out of range")?;

    let priority = obj
        .get("PRIORITY")
        .and_then(Value::as_str)
        .and_then(|s| s.parse::<u8>().ok())
        .map(Priority::from_syslog_num)
        .unwrap_or(Priority::Info);

    let message = obj
        .get("MESSAGE")
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string();

    let unit = obj
        .get("_SYSTEMD_UNIT")
        .or_else(|| obj.get("UNIT"))
        .and_then(Value::as_str)
        .map(String::from);
    let comm = obj.get("_COMM").and_then(Value::as_str).map(String::from);
    let pid = obj
        .get("_PID")
        .and_then(Value::as_str)
        .and_then(|s| s.parse().ok());
    let uid = obj
        .get("_UID")
        .and_then(Value::as_str)
        .and_then(|s| s.parse().ok());
    let hostname = obj
        .get("_HOSTNAME")
        .and_then(Value::as_str)
        .map(String::from);

    let mut extra = HashMap::new();
    for (k, v) in obj {
        if TOP_LEVEL_KEYS.contains(&k.as_str()) {
            continue;
        }
        let v_str = match v {
            Value::String(s) => s.clone(),
            other => other.to_string(),
        };
        extra.insert(k.clone(), v_str);
    }

    Ok(JournalEntry {
        timestamp,
        priority,
        message,
        unit,
        comm,
        pid,
        uid,
        hostname,
        extra,
    })
}

/// Le entries de um BufRead (JSON-lines). Linhas malformadas sao avisadas e puladas.
pub fn parse_log<R: BufRead>(reader: R) -> Result<Vec<JournalEntry>> {
    let mut entries = Vec::new();
    for (i, line) in reader.lines().enumerate() {
        let line = line.with_context(|| format!("read line {}", i + 1))?;
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        match parse_json_line(line) {
            Ok(e) => entries.push(e),
            Err(e) => eprintln!("warn: journal line {} ignored: {}", i + 1, e),
        }
    }
    entries.sort_by_key(|e| e.timestamp);
    Ok(entries)
}

/// Roda `journalctl -o json --no-pager -n LIMIT` e parseia o output.
pub fn fetch_via_journalctl(limit: usize) -> Result<Vec<JournalEntry>> {
    if Command::new("journalctl").arg("--version").output().is_err() {
        bail!(
            "journalctl nao encontrado. Em sistemas sem systemd (ex: Mac), \
             use --journal-path FILE com um snapshot JSON do journal."
        );
    }

    let limit_arg = format!("-n{limit}");
    let output = Command::new("journalctl")
        .args(["-o", "json", "--no-pager", &limit_arg])
        .stderr(Stdio::inherit())
        .output()
        .context("spawning journalctl")?;

    if !output.status.success() {
        bail!("journalctl falhou com status {}", output.status);
    }

    let cursor = std::io::Cursor::new(output.stdout);
    parse_log(cursor)
}

#[cfg(test)]
mod tests {
    use super::*;
    use pretty_assertions::assert_eq;

    #[test]
    fn parses_basic_journal_entry() {
        let line = r#"{"__REALTIME_TIMESTAMP":"1748000000123456","PRIORITY":"6","MESSAGE":"Started Daily apt-update.service.","_SYSTEMD_UNIT":"systemd","_COMM":"systemd","_PID":"1","_UID":"0","_HOSTNAME":"fedora","SYSLOG_IDENTIFIER":"systemd"}"#;
        let e = parse_json_line(line).unwrap();
        assert_eq!(e.priority, Priority::Info);
        assert_eq!(e.message, "Started Daily apt-update.service.");
        assert_eq!(e.unit.as_deref(), Some("systemd"));
        assert_eq!(e.comm.as_deref(), Some("systemd"));
        assert_eq!(e.pid, Some(1));
        assert_eq!(e.hostname.as_deref(), Some("fedora"));
        assert_eq!(e.extra.get("SYSLOG_IDENTIFIER").map(String::as_str), Some("systemd"));
    }

    #[test]
    fn maps_syslog_priority_correctly() {
        assert_eq!(Priority::from_syslog_num(0), Priority::Emerg);
        assert_eq!(Priority::from_syslog_num(3), Priority::Err);
        assert_eq!(Priority::from_syslog_num(4), Priority::Warning);
        assert_eq!(Priority::from_syslog_num(7), Priority::Debug);
        assert_eq!(Priority::from_syslog_num(99), Priority::Debug);
    }

    #[test]
    fn parses_error_priority() {
        let line = r#"{"__REALTIME_TIMESTAMP":"1748000010000000","PRIORITY":"3","MESSAGE":"usb 1-2: device descriptor read/64, error -110","_COMM":"kernel"}"#;
        let e = parse_json_line(line).unwrap();
        assert_eq!(e.priority, Priority::Err);
        assert!(e.message.contains("device descriptor"));
    }
}
