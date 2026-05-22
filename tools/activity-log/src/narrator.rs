//! Converte `Event`s em frases human-readable em portugues.
//!
//! Dispatch entre audit e journal; cada tipo tem seu proprio templater.

use crate::audit::AuditEvent;
use crate::event::Event;
use crate::journal::{JournalEntry, Priority};

pub fn narrate(event: &Event) -> String {
    match event {
        Event::Audit(e) => narrate_audit(e),
        Event::Journal(j) => narrate_journal(j),
    }
}

// ============================================================================
// audit
// ============================================================================

fn narrate_audit(event: &AuditEvent) -> String {
    let ts = event.timestamp.format("%H:%M:%S").to_string();
    let primary = event.primary_type();

    match primary {
        "AVC" => narrate_avc(event, &ts),
        "USER_AUTH" => narrate_user_auth(event, &ts),
        "USER_LOGIN" => narrate_user_login(event, &ts),
        "USER_ACCT" => narrate_user_acct(event, &ts),
        "ANOM_PROMISCUOUS" => format!(
            "{ts} — interface entrou em modo promiscuo (anomalia de captura)"
        ),
        "ANOM_ABEND" => format!("{ts} — processo terminou anormalmente (crash)"),
        "SYSCALL" => narrate_syscall(event, &ts),
        other => format!("{ts} — evento {} (id {})", other, event.audit_id),
    }
}

fn narrate_avc(event: &AuditEvent, ts: &str) -> String {
    let comm = event.field("comm").unwrap_or("?");
    let pid = event.field("pid").unwrap_or("?");
    let name = event.field("name").unwrap_or("?");
    let permissive = event.field("permissive").unwrap_or("0");
    let mode = if permissive == "1" {
        "permitiu mas registrou"
    } else {
        "BLOQUEOU"
    };

    let action = extract_avc_action(event).unwrap_or_else(|| "<acao>".to_string());

    format!(
        "{ts} — SELinux {mode}: processo `{comm}` (pid {pid}) tentou {action} em `{name}`"
    )
}

fn extract_avc_action(event: &AuditEvent) -> Option<String> {
    event.field("avc_op").map(|op| format!("`{}`", op))
}

fn narrate_user_auth(event: &AuditEvent, ts: &str) -> String {
    let acct = event.field("acct").unwrap_or("?");
    let exe = event.field("exe").unwrap_or("?");
    let res = event.field("res").unwrap_or("?");
    let outcome = if res == "success" { "OK" } else { "FALHOU" };
    format!("{ts} — autenticacao via {exe}: usuario `{acct}` {outcome}")
}

fn narrate_user_login(event: &AuditEvent, ts: &str) -> String {
    let acct = event.field("acct").unwrap_or("?");
    let res = event.field("res").unwrap_or("?");
    let outcome = if res == "success" { "logou" } else { "tentou logar (falha)" };
    format!("{ts} — usuario `{acct}` {outcome}")
}

fn narrate_user_acct(event: &AuditEvent, ts: &str) -> String {
    let acct = event.field("acct").unwrap_or("?");
    let res = event.field("res").unwrap_or("?");
    format!("{ts} — verificacao de conta `{acct}` ({res})")
}

fn narrate_syscall(event: &AuditEvent, ts: &str) -> String {
    let comm = event.field("comm").unwrap_or("?");
    let syscall = event.field("syscall").unwrap_or("?");
    let success = event.field("success").unwrap_or("?");
    let exe = event.field("exe").unwrap_or("?");
    format!(
        "{ts} — syscall {syscall} por `{comm}` ({exe}) — sucesso={success}"
    )
}

// ============================================================================
// journal
// ============================================================================

fn narrate_journal(e: &JournalEntry) -> String {
    let ts = e.timestamp.format("%H:%M:%S").to_string();
    let source = journal_source_label(e);
    let priority_tag = priority_tag(e.priority);
    if priority_tag.is_empty() {
        format!("{ts} — {source}: {}", trim_message(&e.message))
    } else {
        format!("{ts} — {priority_tag} {source}: {}", trim_message(&e.message))
    }
}

/// Label compacto do que gerou o log: unit (sem sufixo .service) > comm > "system".
fn journal_source_label(e: &JournalEntry) -> String {
    if let Some(unit) = &e.unit {
        return strip_unit_suffix(unit);
    }
    if let Some(comm) = &e.comm {
        return comm.clone();
    }
    "system".to_string()
}

fn strip_unit_suffix(s: &str) -> String {
    for suf in [".service", ".socket", ".target", ".timer", ".mount", ".scope"] {
        if let Some(stripped) = s.strip_suffix(suf) {
            return stripped.to_string();
        }
    }
    s.to_string()
}

fn priority_tag(p: Priority) -> &'static str {
    match p {
        Priority::Emerg => "[EMERG]",
        Priority::Alert => "[ALERT]",
        Priority::Crit => "[CRIT]",
        Priority::Err => "[ERR]",
        Priority::Warning => "[WARN]",
        Priority::Notice => "[NOTICE]",
        Priority::Info | Priority::Debug => "",
    }
}

/// Trunca mensagens muito longas para nao quebrar layout da TUI.
fn trim_message(msg: &str) -> String {
    const MAX: usize = 240;
    if msg.len() > MAX {
        let mut s = msg.chars().take(MAX).collect::<String>();
        s.push_str(" …");
        s
    } else {
        msg.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::audit::{group_into_events, parse_line};

    #[test]
    fn narrates_user_auth_success() {
        let line = r#"type=USER_AUTH msg=audit(1748000000.0:1): pid=1 uid=0 acct="andre" exe="/usr/bin/sudo" res=success"#;
        let r = parse_line(line).unwrap();
        let ev = group_into_events(vec![r]).remove(0);
        let s = narrate(&Event::Audit(ev));
        assert!(s.contains("usuario `andre`"));
        assert!(s.contains("OK"));
    }

    #[test]
    fn narrates_journal_error() {
        use chrono::TimeZone;
        let entry = JournalEntry {
            timestamp: chrono::Utc.timestamp_opt(1748000000, 0).unwrap(),
            priority: Priority::Err,
            message: "device descriptor read/64, error -110".into(),
            unit: None,
            comm: Some("kernel".into()),
            pid: None,
            uid: None,
            hostname: None,
            extra: Default::default(),
        };
        let s = narrate(&Event::Journal(entry));
        assert!(s.contains("[ERR]"));
        assert!(s.contains("kernel"));
        assert!(s.contains("device descriptor"));
    }

    #[test]
    fn strips_service_suffix() {
        assert_eq!(strip_unit_suffix("sshd.service"), "sshd");
        assert_eq!(strip_unit_suffix("network.target"), "network");
        assert_eq!(strip_unit_suffix("foo.bar"), "foo.bar");
    }
}
