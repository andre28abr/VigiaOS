//! Abstracao unificada de "evento" sobre as varias fontes (audit, journal, fail2ban, ...).
//!
//! Cada fonte tem seu proprio struct; a enum `Event` envelope todos para que
//! TUI, narrador e filtros possam tratar lista heterogenea de forma uniforme.

use chrono::{DateTime, Utc};
use serde::Serialize;

use crate::audit::AuditEvent;
use crate::fail2ban::{Action, Fail2banEntry};
use crate::journal::JournalEntry;

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
