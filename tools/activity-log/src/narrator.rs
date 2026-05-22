//! Converte `AuditEvent`s em frases human-readable em portugues.
//!
//! Mapeamento simples para os tipos mais comuns. Casos nao mapeados
//! caem no fallback generico.

use crate::audit::AuditEvent;

pub fn narrate(event: &AuditEvent) -> String {
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
        "ANOM_ABEND" => format!(
            "{ts} — processo terminou anormalmente (crash)"
        ),
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

/// Extrai a acao do AVC (campo virtual `avc_op` setado pelo parser).
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::audit::{parse_line, group_into_events};

    #[test]
    fn narrates_user_auth_success() {
        let line = r#"type=USER_AUTH msg=audit(1748000000.0:1): pid=1 uid=0 acct="andre" exe="/usr/bin/sudo" res=success"#;
        let r = parse_line(line).unwrap();
        let ev = group_into_events(vec![r]).remove(0);
        let s = narrate(&ev);
        assert!(s.contains("usuario `andre`"));
        assert!(s.contains("OK"));
    }
}
