//! Abstracao unificada de "evento" sobre as varias fontes (audit, journal, fail2ban, ...).
//!
//! Cada fonte tem seu proprio struct; a enum `Event` envelope todos para que
//! TUI, narrador e filtros possam tratar lista heterogenea de forma uniforme.

use chrono::{DateTime, Utc};
use serde::Serialize;

use crate::audit::AuditEvent;
use crate::fail2ban::{Action, Fail2banEntry, Level as F2bLevel};
use crate::journal::{JournalEntry, Priority};

/// Nivel de relevancia de um evento ou correlation.
/// Ordenado para permitir comparacoes (Suspicious > Interesting > Routine).
#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    Routine,
    Interesting,
    Suspicious,
}

impl Severity {
    pub fn as_str(self) -> &'static str {
        match self {
            Severity::Routine => "routine",
            Severity::Interesting => "interesting",
            Severity::Suspicious => "suspicious",
        }
    }
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "source", rename_all = "lowercase")]
pub enum Event {
    Audit(AuditEvent),
    Journal(JournalEntry),
    Fail2ban(Fail2banEntry),
}

impl Event {
    pub fn timestamp(&self) -> DateTime<Utc> {
        match self {
            Event::Audit(e) => e.timestamp,
            Event::Journal(e) => e.timestamp,
            Event::Fail2ban(e) => e.timestamp,
        }
    }

    pub fn source(&self) -> &'static str {
        match self {
            Event::Audit(_) => "audit",
            Event::Journal(_) => "journal",
            Event::Fail2ban(_) => "fail2ban",
        }
    }

    /// Categoria para filtros e cores.
    pub fn primary_type(&self) -> String {
        match self {
            Event::Audit(e) => e.primary_type().to_string(),
            Event::Journal(e) => e.priority.as_str().to_uppercase(),
            Event::Fail2ban(e) => fail2ban_category(&e.action).to_string(),
        }
    }

    /// Classifica o evento individual em Routine/Interesting/Suspicious.
    /// Regras conservadoras — granularidade pode evoluir com feedback de uso real.
    pub fn severity(&self) -> Severity {
        match self {
            Event::Audit(e) => audit_severity(e),
            Event::Journal(e) => journal_severity(e),
            Event::Fail2ban(e) => fail2ban_severity(e),
        }
    }
}

// ============================================================================
// regras de classificacao por source
// ============================================================================

fn audit_severity(e: &AuditEvent) -> Severity {
    match e.primary_type() {
        // SELinux / anomalias
        "AVC" => match e.field("permissive") {
            Some("0") => Severity::Suspicious,
            _ => Severity::Interesting,
        },
        "USER_SELINUX_ERR" => Severity::Suspicious,
        "ANOM_PROMISCUOUS" => Severity::Suspicious,
        "ANOM_ABEND" => Severity::Interesting,

        // Autenticacao / sessao — sucesso eh rotineiro, falha eh suspeito
        "USER_AUTH" | "USER_LOGIN" | "LOGIN" => match e.field("res") {
            Some("success") | Some("1") => Severity::Routine,
            _ => Severity::Suspicious,
        },
        "USER_ACCT" => match e.field("res") {
            Some("success") => Severity::Routine,
            _ => Severity::Interesting,
        },
        // sudo / execucao de comando como root — Interesting mesmo no sucesso
        "USER_CMD" => match e.field("res") {
            Some("success") => Severity::Interesting,
            _ => Severity::Suspicious,
        },
        "USER_START" | "USER_END" | "USER_TTY" | "USER_ROLE_CHANGE" => Severity::Routine,

        // Credenciais (PAM): success eh rotineiro
        "CRED_ACQ" | "CRED_DISP" | "CRED_REFR" => match e.field("res") {
            Some("success") => Severity::Routine,
            _ => Severity::Interesting,
        },

        // Servicos systemd
        "SERVICE_START" | "SERVICE_STOP" => match e.field("res") {
            Some("failed") => Severity::Interesting,
            _ => Severity::Routine,
        },

        // Kernel
        "BPF" => Severity::Routine,
        "SYSCALL" => match e.field("success") {
            Some("yes") => Severity::Routine,
            Some(_) => Severity::Interesting,
            None => Severity::Routine,
        },

        _ => Severity::Routine,
    }
}

fn journal_severity(e: &JournalEntry) -> Severity {
    match e.priority {
        Priority::Emerg | Priority::Alert | Priority::Crit => Severity::Suspicious,
        Priority::Err => Severity::Interesting,
        Priority::Warning => Severity::Interesting,
        Priority::Notice | Priority::Info | Priority::Debug => Severity::Routine,
    }
}

fn fail2ban_severity(e: &Fail2banEntry) -> Severity {
    match &e.action {
        Action::Ban => Severity::Suspicious,
        Action::Found => Severity::Interesting,
        Action::Unban => Severity::Routine,
        Action::JailStarted | Action::JailStopped => Severity::Routine,
        Action::Other { .. } => match e.level {
            F2bLevel::Critical | F2bLevel::Error => Severity::Suspicious,
            F2bLevel::Warning => Severity::Interesting,
            _ => Severity::Routine,
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::audit::{group_into_events, parse_line};

    fn make_audit_event(line: &str) -> Event {
        Event::Audit(group_into_events(vec![parse_line(line).unwrap()]).remove(0))
    }

    #[test]
    fn severity_order_comparable() {
        assert!(Severity::Suspicious > Severity::Interesting);
        assert!(Severity::Interesting > Severity::Routine);
    }

    #[test]
    fn avc_denial_is_suspicious() {
        let line = r#"type=AVC msg=audit(1748000000.0:1): avc:  denied  { write } for  pid=1 comm="x" name="y" scontext=a tcontext=b tclass=dir permissive=0"#;
        let e = make_audit_event(line);
        assert_eq!(e.severity(), Severity::Suspicious);
    }

    #[test]
    fn avc_permissive_is_interesting() {
        let line = r#"type=AVC msg=audit(1748000000.0:1): avc:  denied  { write } for  pid=1 comm="x" name="y" scontext=a tcontext=b tclass=dir permissive=1"#;
        let e = make_audit_event(line);
        assert_eq!(e.severity(), Severity::Interesting);
    }

    #[test]
    fn user_auth_success_is_routine() {
        let line = r#"type=USER_AUTH msg=audit(1748000000.0:1): pid=1 uid=0 acct="andre" exe="/usr/bin/sudo" res=success"#;
        let e = make_audit_event(line);
        assert_eq!(e.severity(), Severity::Routine);
    }

    #[test]
    fn user_auth_failure_is_suspicious() {
        let line = r#"type=USER_AUTH msg=audit(1748000000.0:1): pid=1 uid=0 acct="andre" exe="/usr/bin/sudo" res=failed"#;
        let e = make_audit_event(line);
        assert_eq!(e.severity(), Severity::Suspicious);
    }

    #[test]
    fn syscall_success_is_routine() {
        let line = r#"type=SYSCALL msg=audit(1748000000.0:1): arch=x syscall=1 success=yes exit=0 comm="x""#;
        let e = make_audit_event(line);
        assert_eq!(e.severity(), Severity::Routine);
    }
}


fn fail2ban_category(a: &Action) -> &'static str {
    match a {
        Action::Ban => "BAN",
        Action::Unban => "UNBAN",
        Action::Found => "FOUND",
        Action::JailStarted => "JAIL_START",
        Action::JailStopped => "JAIL_STOP",
        Action::Other { .. } => "F2B_OTHER",
    }
}
