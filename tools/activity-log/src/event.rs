//! Abstracao unificada de "evento" sobre as varias fontes (audit, journal, ...).
//!
//! Cada fonte tem seu proprio struct (ver `audit::AuditEvent`,
//! `journal::JournalEntry`); a enum `Event` envelope ambos para que TUI,
//! narrador e filtros possam tratar lista heterogenea de forma uniforme.

use chrono::{DateTime, Utc};
use serde::Serialize;

use crate::audit::AuditEvent;
use crate::journal::JournalEntry;

/// Container de qualquer evento parseado.
#[derive(Debug, Clone, Serialize)]
#[serde(tag = "source", rename_all = "lowercase")]
pub enum Event {
    Audit(AuditEvent),
    Journal(JournalEntry),
}

impl Event {
    pub fn timestamp(&self) -> DateTime<Utc> {
        match self {
            Event::Audit(e) => e.timestamp,
            Event::Journal(e) => e.timestamp,
        }
    }

    /// Identifica a origem (para filtros e UI).
    pub fn source(&self) -> &'static str {
        match self {
            Event::Audit(_) => "audit",
            Event::Journal(_) => "journal",
        }
    }

    /// Categoria principal — para audit retorna o record_type (AVC, USER_AUTH...);
    /// para journal retorna a priority em uppercase (ERR, WARNING, INFO...).
    pub fn primary_type(&self) -> String {
        match self {
            Event::Audit(e) => e.primary_type().to_string(),
            Event::Journal(e) => e.priority.as_str().to_uppercase(),
        }
    }
}
