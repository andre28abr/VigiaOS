//! Parseador de linhas do audit log do Linux (`/var/log/audit/audit.log`).
//!
//! Formato tipico:
//!     type=SYSCALL msg=audit(1748000000.123:456): arch=c00000b7 syscall=257 ...
//!     type=AVC msg=audit(1748000000.123:456): avc:  denied  { write } for ...
//!
//! Uma "operacao" pode aparecer como varias linhas com o mesmo audit_id —
//! por exemplo SYSCALL + PATH + CWD + PROCTITLE compartilham o id. O
//! `EventBuilder` agrupa por id.

use std::collections::HashMap;

use anyhow::{Context, Result};
use chrono::{DateTime, TimeZone, Utc};
use serde::Serialize;

/// Uma unica linha do audit.log parseada.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct AuditRecord {
    pub timestamp: DateTime<Utc>,
    pub audit_id: u64,
    pub record_type: String,
    pub fields: HashMap<String, String>,
}

/// Conjunto de records com o mesmo audit_id, representando uma operacao.
#[derive(Debug, Clone, Serialize)]
pub struct AuditEvent {
    pub audit_id: u64,
    pub timestamp: DateTime<Utc>,
    pub records: Vec<AuditRecord>,
}

impl AuditEvent {
    /// Tipo "primario" do evento — o que melhor representa a operacao.
    /// Heuristica: AVC > USER_* > SYSCALL > primeiro record.
    pub fn primary_type(&self) -> &str {
        const PRIORITY: &[&str] = &[
            "AVC", "USER_AUTH", "USER_LOGIN", "USER_ACCT",
            "ANOM_PROMISCUOUS", "ANOM_ABEND", "SYSCALL",
        ];
        for t in PRIORITY {
            if self.records.iter().any(|r| r.record_type == *t) {
                return t;
            }
        }
        self.records
            .first()
            .map(|r| r.record_type.as_str())
            .unwrap_or("UNKNOWN")
    }

    /// Retorna o primeiro valor encontrado para uma chave em qualquer record.
    pub fn field(&self, key: &str) -> Option<&str> {
        self.records
            .iter()
            .find_map(|r| r.fields.get(key).map(String::as_str))
    }
}

/// Parseia uma unica linha do audit.log.
pub fn parse_line(line: &str) -> Result<AuditRecord> {
    // Localiza " msg=audit(" para split type prefix vs. resto
    let (type_part, rest) = line
        .split_once(" msg=audit(")
        .context("missing ' msg=audit(' separator")?;

    // type=SYSCALL -> "SYSCALL"
    let record_type = type_part
        .strip_prefix("type=")
        .context("line does not start with 'type='")?
        .to_string();

    // rest: "1748000000.123:456): arch=... key=value ..."
    let (id_part, fields_part) = rest
        .split_once("): ")
        .context("missing '): ' after audit id")?;

    // id_part: "1748000000.123:456"
    let (epoch_str, id_str) = id_part
        .split_once(':')
        .context("missing ':' between epoch and audit id")?;

    let epoch_seconds: f64 = epoch_str.parse().context("invalid epoch")?;
    let audit_id: u64 = id_str.parse().context("invalid audit id")?;

    let secs = epoch_seconds.trunc() as i64;
    let nsecs = (epoch_seconds.fract() * 1_000_000_000.0) as u32;
    let timestamp = Utc
        .timestamp_opt(secs, nsecs)
        .single()
        .context("invalid epoch -> datetime")?;

    let mut fields = parse_fields(fields_part);

    // AVC records tem `avc: denied { write } for ...` — o "write" nao e' key=value,
    // entao parse_fields ignora. Extraimos manualmente para field virtual `avc_op`.
    if record_type == "AVC" {
        if let Some(op) = extract_braced(fields_part) {
            fields.insert("avc_op".to_string(), op);
        }
        if fields_part.contains(" denied ") {
            fields.insert("avc_result".to_string(), "denied".to_string());
        } else if fields_part.contains(" granted ") {
            fields.insert("avc_result".to_string(), "granted".to_string());
        }
    }

    Ok(AuditRecord {
        timestamp,
        audit_id,
        record_type,
        fields,
    })
}

/// Extrai o conteudo entre `{` e `}` mais externos (ex: `{ write }` -> `write`).
fn extract_braced(s: &str) -> Option<String> {
    let start = s.find('{')?;
    let end_rel = s[start..].find('}')?;
    let inner = s[start + 1..start + end_rel].trim();
    if inner.is_empty() {
        None
    } else {
        Some(inner.to_string())
    }
}

/// Parseia a porcao `key=value key="value with spaces" ...` em HashMap.
/// Suporta valores aspas-duplas (que podem conter espacos).
fn parse_fields(s: &str) -> HashMap<String, String> {
    let mut out = HashMap::new();
    let bytes = s.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        // pula whitespace
        while i < bytes.len() && bytes[i] == b' ' {
            i += 1;
        }
        if i >= bytes.len() {
            break;
        }

        // captura key ate '='
        let key_start = i;
        while i < bytes.len() && bytes[i] != b'=' && bytes[i] != b' ' {
            i += 1;
        }
        if i >= bytes.len() || bytes[i] != b'=' {
            // key sem '=' — pula
            continue;
        }
        let key = &s[key_start..i];
        i += 1; // pula '='

        // captura valor — suporta double-quoted, single-quoted (com aninhamento) ou unquoted
        let (value, recurse_inner) = if i < bytes.len() && bytes[i] == b'"' {
            // double-quoted: ler ate proxima aspa
            i += 1;
            let v_start = i;
            while i < bytes.len() && bytes[i] != b'"' {
                i += 1;
            }
            let v = &s[v_start..i];
            if i < bytes.len() {
                i += 1; // pula closing "
            }
            (v, false)
        } else if i < bytes.len() && bytes[i] == b'\'' {
            // single-quoted: typical do USER_* msg='op=X acct="Y" res=success'.
            // Capturamos o valor inteiro E recursamos para expandir key=value internos.
            i += 1;
            let v_start = i;
            while i < bytes.len() && bytes[i] != b'\'' {
                i += 1;
            }
            let v = &s[v_start..i];
            if i < bytes.len() {
                i += 1; // pula closing '
            }
            (v, true)
        } else {
            // unquoted: ler ate proximo espaco
            let v_start = i;
            while i < bytes.len() && bytes[i] != b' ' {
                i += 1;
            }
            (&s[v_start..i], false)
        };

        out.insert(key.to_string(), value.to_string());

        // Achatar key=values aninhados em single-quoted (audit format quirk).
        // Sub-fields tem prioridade BAIXA — nao sobrescrevem se ja existir.
        if recurse_inner {
            for (k, v) in parse_fields(value) {
                out.entry(k).or_insert(v);
            }
        }
    }
    out
}

/// Agrupa records por audit_id, mantendo ordem cronologica.
pub fn group_into_events(records: Vec<AuditRecord>) -> Vec<AuditEvent> {
    let mut by_id: HashMap<u64, Vec<AuditRecord>> = HashMap::new();
    for r in records {
        by_id.entry(r.audit_id).or_default().push(r);
    }

    let mut events: Vec<AuditEvent> = by_id
        .into_iter()
        .map(|(audit_id, recs)| {
            let timestamp = recs
                .iter()
                .map(|r| r.timestamp)
                .min()
                .expect("group has at least one record");
            AuditEvent {
                audit_id,
                timestamp,
                records: recs,
            }
        })
        .collect();
    events.sort_by_key(|e| e.timestamp);
    events
}

/// Le um audit.log (ou stream com formato equivalente) e devolve eventos.
pub fn parse_log<R: std::io::BufRead>(reader: R) -> Result<Vec<AuditEvent>> {
    let mut records = Vec::new();
    for (i, line) in reader.lines().enumerate() {
        let line = line.with_context(|| format!("read line {}", i + 1))?;
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        match parse_line(line) {
            Ok(r) => records.push(r),
            Err(e) => {
                // log e segue — uma linha malformada nao pode quebrar o resto
                eprintln!("warn: line {} ignored: {}", i + 1, e);
            }
        }
    }
    Ok(group_into_events(records))
}

#[cfg(test)]
mod tests {
    use super::*;
    use pretty_assertions::assert_eq;

    #[test]
    fn parses_syscall_line() {
        let line = r#"type=SYSCALL msg=audit(1748000000.123:456): arch=c00000b7 syscall=257 success=yes exit=3 a0=ffffff9c comm="systemd" exe="/usr/lib/systemd/systemd""#;
        let r = parse_line(line).unwrap();
        assert_eq!(r.record_type, "SYSCALL");
        assert_eq!(r.audit_id, 456);
        assert_eq!(r.fields.get("syscall").map(String::as_str), Some("257"));
        assert_eq!(r.fields.get("comm").map(String::as_str), Some("systemd"));
        assert_eq!(
            r.fields.get("exe").map(String::as_str),
            Some("/usr/lib/systemd/systemd")
        );
    }

    #[test]
    fn parses_avc_denial() {
        let line = r#"type=AVC msg=audit(1748000123.456:789): avc:  denied  { write } for  pid=1234 comm="httpd" name="uploads" scontext=system_u:system_r:httpd_t:s0 tcontext=unconfined_u:object_r:default_t:s0 tclass=dir permissive=0"#;
        let r = parse_line(line).unwrap();
        assert_eq!(r.record_type, "AVC");
        assert_eq!(r.audit_id, 789);
        assert_eq!(r.fields.get("pid").map(String::as_str), Some("1234"));
        assert_eq!(r.fields.get("comm").map(String::as_str), Some("httpd"));
        assert_eq!(r.fields.get("permissive").map(String::as_str), Some("0"));
    }

    #[test]
    fn expands_single_quoted_nested_fields() {
        // Pattern comum em USER_AUTH: msg='op=X acct="Y" res=success'
        let line = r#"type=USER_AUTH msg=audit(1748000000.0:50): pid=1 uid=0 msg='op=PAM:authentication grantors=pam_unix acct="andre" exe="/usr/bin/sudo" res=success'"#;
        let r = parse_line(line).unwrap();
        // Top-level: msg captura o conteudo aspeado inteiro
        assert!(r.fields.get("msg").unwrap().contains("op=PAM"));
        // Inner key=values tambem expandidos
        assert_eq!(r.fields.get("acct").map(String::as_str), Some("andre"));
        assert_eq!(r.fields.get("res").map(String::as_str), Some("success"));
        assert_eq!(r.fields.get("grantors").map(String::as_str), Some("pam_unix"));
    }

    #[test]
    fn groups_records_by_audit_id() {
        let lines = vec![
            r#"type=SYSCALL msg=audit(1748000000.0:100): syscall=2 comm="cat""#,
            r#"type=PATH msg=audit(1748000000.0:100): item=0 name="/etc/passwd""#,
            r#"type=PROCTITLE msg=audit(1748000000.0:100): proctitle="cat /etc/passwd""#,
            r#"type=SYSCALL msg=audit(1748000001.0:101): syscall=59 comm="zsh""#,
        ];
        let records: Vec<_> = lines.iter().map(|l| parse_line(l).unwrap()).collect();
        let events = group_into_events(records);
        assert_eq!(events.len(), 2);
        assert_eq!(events[0].audit_id, 100);
        assert_eq!(events[0].records.len(), 3);
        assert_eq!(events[1].audit_id, 101);
        assert_eq!(events[1].records.len(), 1);
    }
}
