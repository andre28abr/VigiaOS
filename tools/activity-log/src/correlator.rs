//! Detecta padroes cross-source nos eventos e gera "correlations" —
//! narrativas que sintetizam multiplos eventos relacionados em uma frase.
//!
//! Padroes implementados:
//!
//! 1. **Fail2ban burst**: N x Found para mesmo IP, seguido de Ban do mesmo IP
//!    dentro de janela de 2min. "fail2ban baniu X.X.X.X apos N tentativas em Ts"
//!
//! 2. **OOM kill**: journal CRIT "Out of memory: Killed X". Eventualmente
//!    pareado com audit ANOM_ABEND para mesmo processo dentro de 30s.
//!
//! 3. **SELinux burst**: 3+ AVC denials para mesmo `comm` dentro de 60s.
//!    "Processo X teve N tentativas bloqueadas em Ts (problema de policy)"
//!
//! 4. **SSH login suspeito**: journal "Accepted publickey for X from IP",
//!    com Found anterior em fail2ban para mesmo IP dentro de 10min.
//!    "Login OK por X de IP que tinha tentativas falhas recentes"

use std::collections::HashMap;

use chrono::{DateTime, Duration, Utc};
use serde::Serialize;

use crate::event::Event;
use crate::fail2ban::Action as F2bAction;
use crate::journal::{JournalEntry, Priority};

#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
#[allow(dead_code)] // Routine reservado para uso futuro (classificador v0.6)
pub enum Severity {
    Routine,
    Interesting,
    Suspicious,
}

#[derive(Debug, Clone, Serialize)]
pub struct Correlation {
    pub kind: &'static str,
    pub timestamp: DateTime<Utc>,
    pub end: DateTime<Utc>,
    pub severity: Severity,
    pub summary: String,
    /// Indices em events[] que contribuem para essa correlation.
    pub contributing: Vec<usize>,
}

pub fn correlate(events: &[Event]) -> Vec<Correlation> {
    let mut out = Vec::new();
    out.extend(detect_fail2ban_burst(events));
    out.extend(detect_oom_kill(events));
    out.extend(detect_selinux_burst(events));
    out.extend(detect_suspicious_ssh_login(events));
    out.sort_by_key(|c| c.timestamp);
    out
}

// ============================================================================
// 1. fail2ban burst
// ============================================================================

fn detect_fail2ban_burst(events: &[Event]) -> Vec<Correlation> {
    let window = Duration::seconds(120);
    let mut out = Vec::new();

    for (i, e) in events.iter().enumerate() {
        let (ban_ip, ban_jail, ban_ts) = match e {
            Event::Fail2ban(f) if matches!(f.action, F2bAction::Ban) => (
                f.ip.clone().unwrap_or_else(|| "?".into()),
                f.jail.clone().unwrap_or_else(|| "?".into()),
                f.timestamp,
            ),
            _ => continue,
        };

        // Olha para tras em ate `window` por Found do mesmo IP
        let mut found_idx = Vec::new();
        for j in (0..i).rev() {
            if events[j].timestamp() < ban_ts - window {
                break;
            }
            if let Event::Fail2ban(prev) = &events[j] {
                if matches!(prev.action, F2bAction::Found)
                    && prev.ip.as_deref() == Some(ban_ip.as_str())
                {
                    found_idx.push(j);
                }
            }
        }

        // Burst de verdade exige multiplas tentativas (>= 2). Ban com 1 Found
        // pode ser maxretry=1 e nao agrega narrativa.
        if found_idx.len() < 2 {
            continue;
        }

        let mut contrib = found_idx.clone();
        contrib.push(i);
        contrib.sort();
        let earliest = events[contrib[0]].timestamp();
        let span = (ban_ts - earliest).num_seconds();

        out.push(Correlation {
            kind: "fail2ban_burst",
            timestamp: earliest,
            end: ban_ts,
            severity: Severity::Suspicious,
            summary: format!(
                "fail2ban baniu {} apos {} tentativas em {}s (jail {})",
                ban_ip,
                found_idx.len(),
                span,
                ban_jail
            ),
            contributing: contrib,
        });
    }

    out
}

// ============================================================================
// 2. OOM kill
// ============================================================================

fn detect_oom_kill(events: &[Event]) -> Vec<Correlation> {
    let window = Duration::seconds(30);
    let mut out = Vec::new();

    for (i, e) in events.iter().enumerate() {
        let (oom_proc, oom_ts) = match e {
            Event::Journal(j) if is_oom_kill(j) => match parse_oom_process(&j.message) {
                Some(p) => (p, j.timestamp),
                None => continue,
            },
            _ => continue,
        };

        let mut contrib = vec![i];

        // Olha para frente em ate `window` por ANOM_ABEND com mesmo comm
        for j in (i + 1)..events.len() {
            if events[j].timestamp() > oom_ts + window {
                break;
            }
            if let Event::Audit(a) = &events[j] {
                if a.primary_type() == "ANOM_ABEND" {
                    if a.field("comm").map(|c| c == oom_proc).unwrap_or(false) {
                        contrib.push(j);
                    }
                }
            }
        }

        let end = contrib
            .iter()
            .map(|&idx| events[idx].timestamp())
            .max()
            .unwrap_or(oom_ts);

        let summary = if contrib.len() > 1 {
            format!(
                "Sistema sem memoria matou processo `{}` (kernel OOM); confirmado por audit ANOM_ABEND",
                oom_proc
            )
        } else {
            format!(
                "Sistema sem memoria matou processo `{}` (kernel OOM)",
                oom_proc
            )
        };

        out.push(Correlation {
            kind: "oom_kill",
            timestamp: oom_ts,
            end,
            severity: Severity::Interesting,
            summary,
            contributing: contrib,
        });
    }

    out
}

fn is_oom_kill(j: &JournalEntry) -> bool {
    j.priority <= Priority::Crit
        && j.message.contains("Out of memory")
        && (j.message.contains("Killed") || j.message.contains("Kill process"))
}

fn parse_oom_process(msg: &str) -> Option<String> {
    let after = msg.split_once("process").map(|(_, r)| r).unwrap_or(msg);
    let open = after.find('(')?;
    let close = after[open + 1..].find(')')?;
    Some(after[open + 1..open + 1 + close].to_string())
}

// ============================================================================
// 3. SELinux burst
// ============================================================================

fn detect_selinux_burst(events: &[Event]) -> Vec<Correlation> {
    let window = Duration::seconds(60);
    let min_count = 3;
    let mut out = Vec::new();

    // Agrupa indices de AVC por comm
    let mut by_comm: HashMap<String, Vec<usize>> = HashMap::new();
    for (i, e) in events.iter().enumerate() {
        if let Event::Audit(a) = e {
            if a.primary_type() == "AVC" {
                if let Some(comm) = a.field("comm") {
                    by_comm.entry(comm.to_string()).or_default().push(i);
                }
            }
        }
    }

    // Para cada comm, sliding window de window segundos
    for (comm, indices) in &by_comm {
        if indices.len() < min_count {
            continue;
        }
        // Sliding window — varre, mantem indices cujo timestamp esta dentro da window do mais recente
        let mut cluster_start = 0usize;
        let mut best: Option<(usize, usize)> = None; // (start, end) com maior cluster
        for end in 0..indices.len() {
            while events[indices[cluster_start]].timestamp()
                < events[indices[end]].timestamp() - window
            {
                cluster_start += 1;
            }
            let size = end - cluster_start + 1;
            if size >= min_count {
                if best.map(|(s, e)| e - s + 1 < size).unwrap_or(true) {
                    best = Some((cluster_start, end));
                }
            }
        }

        if let Some((s, e)) = best {
            let contrib: Vec<usize> = indices[s..=e].to_vec();
            let earliest = events[contrib[0]].timestamp();
            let latest = events[*contrib.last().unwrap()].timestamp();
            let span = (latest - earliest).num_seconds();
            out.push(Correlation {
                kind: "selinux_burst",
                timestamp: earliest,
                end: latest,
                severity: Severity::Interesting,
                summary: format!(
                    "SELinux bloqueou processo `{}` {} vezes em {}s (provavel problema de policy)",
                    comm,
                    contrib.len(),
                    span.max(1)
                ),
                contributing: contrib,
            });
        }
    }

    out
}

// ============================================================================
// 4. SSH login suspeito (login OK + tentativas falhas anteriores do mesmo IP)
// ============================================================================

fn detect_suspicious_ssh_login(events: &[Event]) -> Vec<Correlation> {
    let window = Duration::minutes(10);
    let mut out = Vec::new();

    for (i, e) in events.iter().enumerate() {
        let (user, ip, ts) = match e {
            Event::Journal(j) => match parse_ssh_accept(&j.message) {
                Some((u, ip)) => (u, ip, j.timestamp),
                None => continue,
            },
            _ => continue,
        };

        // Procura por Found em fail2ban para o mesmo IP antes da janela
        let mut prior_failures = Vec::new();
        for k in (0..i).rev() {
            if events[k].timestamp() < ts - window {
                break;
            }
            if let Event::Fail2ban(f) = &events[k] {
                if matches!(f.action, F2bAction::Found)
                    && f.ip.as_deref() == Some(ip.as_str())
                {
                    prior_failures.push(k);
                }
            }
        }

        if prior_failures.is_empty() {
            continue;
        }

        let mut contrib = prior_failures.clone();
        contrib.push(i);
        contrib.sort();

        out.push(Correlation {
            kind: "suspicious_ssh_login",
            timestamp: events[contrib[0]].timestamp(),
            end: ts,
            severity: Severity::Suspicious,
            summary: format!(
                "Login SSH OK por `{}` de {}, mas teve {} tentativas falhas recentes do mesmo IP",
                user,
                ip,
                prior_failures.len()
            ),
            contributing: contrib,
        });
    }

    out
}

fn parse_ssh_accept(msg: &str) -> Option<(String, String)> {
    // "Accepted publickey for andre from 192.0.2.42 port 51234 ssh2: RSA SHA256:abc"
    let start = msg.find("Accepted ")?;
    let rest = &msg[start..];
    let _method_end = rest.find(" for ")?;
    let after_for = &rest[rest.find(" for ")? + 5..];
    let user_end = after_for.find(' ')?;
    let user = after_for[..user_end].to_string();
    let from_pos = after_for.find(" from ")?;
    let ip_start = from_pos + 6;
    let ip_part = &after_for[ip_start..];
    let ip_end = ip_part.find(' ').unwrap_or(ip_part.len());
    let ip = ip_part[..ip_end].to_string();
    Some((user, ip))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::audit::{group_into_events, parse_line as audit_parse};
    use crate::fail2ban::parse_line as f2b_parse;
    use crate::journal::parse_json_line;

    fn make_events_for_burst() -> Vec<Event> {
        let lines = vec![
            "2025-05-23 11:33:35,100 fail2ban.filter [123]: INFO [sshd] Found 192.0.2.42",
            "2025-05-23 11:33:38,200 fail2ban.filter [123]: INFO [sshd] Found 192.0.2.42",
            "2025-05-23 11:33:42,300 fail2ban.filter [123]: INFO [sshd] Found 192.0.2.42",
            "2025-05-23 11:33:45,400 fail2ban.actions [123]: NOTICE [sshd] Ban 192.0.2.42",
        ];
        lines.into_iter().map(|l| Event::Fail2ban(f2b_parse(l).unwrap())).collect()
    }

    #[test]
    fn detects_fail2ban_burst() {
        let events = make_events_for_burst();
        let corrs = detect_fail2ban_burst(&events);
        assert_eq!(corrs.len(), 1);
        let c = &corrs[0];
        assert_eq!(c.kind, "fail2ban_burst");
        assert_eq!(c.severity, Severity::Suspicious);
        assert!(c.summary.contains("192.0.2.42"));
        assert!(c.summary.contains("3 tentativas"));
        assert_eq!(c.contributing.len(), 4);
    }

    #[test]
    fn detects_oom_kill() {
        let line = r#"{"__REALTIME_TIMESTAMP":"1748000045000000","PRIORITY":"2","MESSAGE":"kernel: Out of memory: Killed process 9876 (chromium)","_COMM":"kernel"}"#;
        let journal = parse_json_line(line).unwrap();
        let events = vec![Event::Journal(journal)];
        let corrs = detect_oom_kill(&events);
        assert_eq!(corrs.len(), 1);
        assert!(corrs[0].summary.contains("chromium"));
    }

    #[test]
    fn detects_selinux_burst() {
        let line_tpl = |ts: u64| {
            format!(
                "type=AVC msg=audit({}.000:{}): avc:  denied  {{ write }} for  pid=2345 comm=\"httpd\" name=\"uploads\" scontext=x tcontext=y tclass=dir permissive=0",
                ts, ts
            )
        };
        let lines = vec![
            line_tpl(1748000000),
            line_tpl(1748000010),
            line_tpl(1748000020),
        ];
        let records: Vec<_> = lines.iter().map(|l| audit_parse(l).unwrap()).collect();
        let audit_events = group_into_events(records);
        let events: Vec<Event> = audit_events.into_iter().map(Event::Audit).collect();
        let corrs = detect_selinux_burst(&events);
        assert_eq!(corrs.len(), 1);
        assert!(corrs[0].summary.contains("httpd"));
        assert!(corrs[0].summary.contains("3 vezes"));
    }

    #[test]
    fn parses_ssh_accept_correctly() {
        let msg = "Accepted publickey for andre from 192.0.2.42 port 51234 ssh2: RSA SHA256:abc";
        let (user, ip) = parse_ssh_accept(msg).unwrap();
        assert_eq!(user, "andre");
        assert_eq!(ip, "192.0.2.42");
    }

    #[test]
    fn parses_oom_process_correctly() {
        let msg = "kernel: Out of memory: Killed process 9876 (chromium) total-vm:...";
        assert_eq!(parse_oom_process(msg).as_deref(), Some("chromium"));
    }
}
