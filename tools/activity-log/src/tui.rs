//! Interface TUI para navegar nos eventos parseados.
//!
//! Layout:
//!   ┌─────────────────────────────────────────────────────────┐
//!   │ VIGIA·OS Activity Log · {n}/{total} eventos             │
//!   ├─────────────────────────────────────────────────────────┤
//!   │ > 14:23:12 [A] AVC        SELinux bloqueou httpd...     │
//!   │   14:23:15 [J] ERR        kernel: usb 1-2: error -110   │
//!   │   ...                                                    │
//!   ├─────────────────────────────────────────────────────────┤
//!   │ Detalhes do evento selecionado (records/fields raw)     │
//!   ├─────────────────────────────────────────────────────────┤
//!   │ [filter: AVC] [search: "denied"]   ↑↓ jk  / f  q        │
//!   └─────────────────────────────────────────────────────────┘
//!
//! Atalhos (modo normal):
//!   ↑↓ / jk         navegar lista
//!   PgUp/PgDn       pular 10
//!   Home/End        primeiro/ultimo
//!   f               cycle filter por tipo
//!   /               entrar em modo de busca
//!   Esc             limpar filtros e busca
//!   q               sair

use std::io::{self, Stdout};
use std::time::Duration;

use anyhow::Result;
use crossterm::event::{self, Event as CtEvent, KeyCode, KeyEventKind, KeyModifiers};
use crossterm::execute;
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Constraint, Direction, Layout};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Wrap};
use ratatui::Terminal;

use crate::event::Event;
use crate::narrator::narrate;

// Paleta VigiaOS (Tailwind zinc + emerald)
const COLOR_ACCENT: Color = Color::Rgb(0x34, 0xd3, 0x99);
const COLOR_DIM: Color = Color::Rgb(0x71, 0x71, 0x7a);
const COLOR_FG: Color = Color::Rgb(0xfa, 0xfa, 0xfa);
const COLOR_FG_DIM: Color = Color::Rgb(0xa1, 0xa1, 0xaa);
const COLOR_WARN: Color = Color::Rgb(0xfb, 0xbf, 0x24);
const COLOR_ERROR: Color = Color::Rgb(0xf8, 0x71, 0x71);
const COLOR_HIGHLIGHT_BG: Color = Color::Rgb(0x18, 0x18, 0x1b);

type Backend = CrosstermBackend<Stdout>;

/// Filtros cycleaveis com `f`. Cobre tipos comuns de audit + priorities journal.
const FILTER_CYCLE: &[&str] = &[
    // Audit
    "AVC",
    "USER_AUTH",
    "USER_LOGIN",
    "ANOM_ABEND",
    "ANOM_PROMISCUOUS",
    "SYSCALL",
    // Journal priorities
    "EMERG",
    "ALERT",
    "CRIT",
    "ERR",
    "WARNING",
    "NOTICE",
    "INFO",
    "DEBUG",
];

#[derive(Debug, PartialEq)]
enum Mode {
    Normal,
    Searching,
}

struct App {
    events: Vec<Event>,
    visible: Vec<usize>,
    list_state: ListState,
    mode: Mode,
    filter: Option<String>,
    search: String,
}

impl App {
    fn new(events: Vec<Event>) -> Self {
        let visible: Vec<usize> = (0..events.len()).collect();
        let mut list_state = ListState::default();
        if !visible.is_empty() {
            list_state.select(Some(0));
        }
        Self {
            events,
            visible,
            list_state,
            mode: Mode::Normal,
            filter: None,
            search: String::new(),
        }
    }

    fn recompute_visible(&mut self) {
        let needle = self.search.to_lowercase();
        self.visible = self
            .events
            .iter()
            .enumerate()
            .filter(|(_, ev)| {
                if let Some(t) = &self.filter {
                    if &ev.primary_type() != t {
                        return false;
                    }
                }
                if !needle.is_empty() {
                    let n = narrate(ev).to_lowercase();
                    if !n.contains(&needle) {
                        return false;
                    }
                }
                true
            })
            .map(|(i, _)| i)
            .collect();

        match self.list_state.selected() {
            None if !self.visible.is_empty() => self.list_state.select(Some(0)),
            Some(_) if self.visible.is_empty() => self.list_state.select(None),
            Some(cur) if cur >= self.visible.len() => {
                self.list_state.select(Some(self.visible.len() - 1));
            }
            _ => {}
        }
    }

    fn cycle_filter(&mut self) {
        self.filter = match &self.filter {
            None => Some(FILTER_CYCLE[0].to_string()),
            Some(cur) => {
                let pos = FILTER_CYCLE.iter().position(|t| t == cur);
                match pos {
                    Some(i) if i + 1 < FILTER_CYCLE.len() => {
                        Some(FILTER_CYCLE[i + 1].to_string())
                    }
                    _ => None,
                }
            }
        };
        self.recompute_visible();
    }

    fn clear_filters(&mut self) {
        self.filter = None;
        self.search.clear();
        self.recompute_visible();
    }

    fn move_selection(&mut self, delta: i32) {
        if self.visible.is_empty() {
            return;
        }
        let cur = self.list_state.selected().unwrap_or(0) as i32;
        let max = (self.visible.len() - 1) as i32;
        let new = (cur + delta).clamp(0, max);
        self.list_state.select(Some(new as usize));
    }

    fn selected_event(&self) -> Option<&Event> {
        self.list_state
            .selected()
            .and_then(|i| self.visible.get(i))
            .and_then(|&idx| self.events.get(idx))
    }
}

pub fn run(events: Vec<Event>) -> Result<()> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let mut terminal = Terminal::new(CrosstermBackend::new(stdout))?;

    let app = App::new(events);
    let res = main_loop(&mut terminal, app);

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;
    res
}

fn main_loop(terminal: &mut Terminal<Backend>, mut app: App) -> Result<()> {
    loop {
        terminal.draw(|f| draw(f, &mut app))?;

        if !event::poll(Duration::from_millis(200))? {
            continue;
        }
        if let CtEvent::Key(key) = event::read()? {
            if key.kind != KeyEventKind::Press {
                continue;
            }
            if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
                return Ok(());
            }

            match app.mode {
                Mode::Normal => match key.code {
                    KeyCode::Char('q') => return Ok(()),
                    KeyCode::Esc => app.clear_filters(),
                    KeyCode::Char('f') => app.cycle_filter(),
                    KeyCode::Char('/') => app.mode = Mode::Searching,
                    KeyCode::Down | KeyCode::Char('j') => app.move_selection(1),
                    KeyCode::Up | KeyCode::Char('k') => app.move_selection(-1),
                    KeyCode::PageDown => app.move_selection(10),
                    KeyCode::PageUp => app.move_selection(-10),
                    KeyCode::Home => {
                        if !app.visible.is_empty() {
                            app.list_state.select(Some(0));
                        }
                    }
                    KeyCode::End => {
                        if !app.visible.is_empty() {
                            app.list_state.select(Some(app.visible.len() - 1));
                        }
                    }
                    _ => {}
                },
                Mode::Searching => match key.code {
                    KeyCode::Esc => {
                        app.search.clear();
                        app.mode = Mode::Normal;
                        app.recompute_visible();
                    }
                    KeyCode::Enter => app.mode = Mode::Normal,
                    KeyCode::Backspace => {
                        app.search.pop();
                        app.recompute_visible();
                    }
                    KeyCode::Char(c) => {
                        app.search.push(c);
                        app.recompute_visible();
                    }
                    KeyCode::Down => app.move_selection(1),
                    KeyCode::Up => app.move_selection(-1),
                    _ => {}
                },
            }
        }
    }
}

fn draw(f: &mut ratatui::Frame, app: &mut App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // header
            Constraint::Min(8),     // event list
            Constraint::Length(16), // detail panel
            Constraint::Length(1),  // status bar
        ])
        .split(f.area());

    // ===== Header =====
    let (audit_count, journal_count) = count_by_source(&app.events);
    let header = Paragraph::new(Line::from(vec![
        Span::styled("VIGIA", Style::default().fg(COLOR_ACCENT).add_modifier(Modifier::BOLD)),
        Span::styled("·OS", Style::default().fg(COLOR_FG).add_modifier(Modifier::BOLD)),
        Span::styled(" Activity Log  ", Style::default().fg(COLOR_FG)),
        Span::styled(
            format!("· {}/{} eventos  ", app.visible.len(), app.events.len()),
            Style::default().fg(COLOR_DIM),
        ),
        Span::styled(format!("audit:{audit_count} "), Style::default().fg(COLOR_DIM)),
        Span::styled(format!("journal:{journal_count}"), Style::default().fg(COLOR_DIM)),
    ]))
    .block(Block::default().borders(Borders::BOTTOM));
    f.render_widget(header, chunks[0]);

    // ===== Event list =====
    let items: Vec<ListItem> = app
        .visible
        .iter()
        .map(|&idx| {
            let e = &app.events[idx];
            render_event_row(e, &app.search)
        })
        .collect();

    let list_title = match (&app.filter, app.search.is_empty()) {
        (None, true) => " eventos ".to_string(),
        (Some(t), true) => format!(" eventos · filter={} ", t),
        (None, false) => format!(" eventos · search=\"{}\" ", app.search),
        (Some(t), false) => format!(" eventos · filter={} search=\"{}\" ", t, app.search),
    };

    let list = List::new(items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(list_title)
                .border_style(Style::default().fg(COLOR_DIM)),
        )
        .highlight_style(
            Style::default()
                .bg(COLOR_HIGHLIGHT_BG)
                .add_modifier(Modifier::BOLD),
        )
        .highlight_symbol("> ");
    f.render_stateful_widget(list, chunks[1], &mut app.list_state);

    // ===== Detail panel =====
    let detail_text = app
        .selected_event()
        .map(format_event_detail)
        .unwrap_or_else(|| "Nenhum evento (filtros podem estar excluindo tudo)".to_string());

    let detail = Paragraph::new(detail_text)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(" detalhes ")
                .border_style(Style::default().fg(COLOR_DIM)),
        )
        .style(Style::default().fg(COLOR_FG))
        .wrap(Wrap { trim: false });
    f.render_widget(detail, chunks[2]);

    // ===== Status bar =====
    let status_line = match app.mode {
        Mode::Searching => Line::from(vec![
            Span::styled("/", Style::default().fg(COLOR_ACCENT).add_modifier(Modifier::BOLD)),
            Span::styled(&app.search, Style::default().fg(COLOR_FG)),
            Span::styled("_", Style::default().fg(COLOR_ACCENT)),
            Span::styled("   Enter=confirma  Esc=cancela", Style::default().fg(COLOR_DIM)),
        ]),
        Mode::Normal => Line::from(vec![
            Span::styled(" ↑↓jk ", Style::default().fg(COLOR_ACCENT)),
            Span::styled("nav  ", Style::default().fg(COLOR_DIM)),
            Span::styled("f ", Style::default().fg(COLOR_ACCENT)),
            Span::styled("filter  ", Style::default().fg(COLOR_DIM)),
            Span::styled("/ ", Style::default().fg(COLOR_ACCENT)),
            Span::styled("search  ", Style::default().fg(COLOR_DIM)),
            Span::styled("Esc ", Style::default().fg(COLOR_ACCENT)),
            Span::styled("clear  ", Style::default().fg(COLOR_DIM)),
            Span::styled("q ", Style::default().fg(COLOR_ACCENT)),
            Span::styled("sai", Style::default().fg(COLOR_DIM)),
        ]),
    };
    f.render_widget(Paragraph::new(status_line), chunks[3]);
}

fn render_event_row<'a>(e: &'a Event, search: &str) -> ListItem<'a> {
    let ts = e.timestamp().format("%H:%M:%S").to_string();
    let primary = e.primary_type();
    let type_color = color_for_type(&primary);
    let source_tag = match e.source() {
        "audit" => "[A]",
        "journal" => "[J]",
        other => other,
    };

    let mut spans = vec![
        Span::styled(ts, Style::default().fg(COLOR_DIM)),
        Span::raw(" "),
        Span::styled(source_tag, Style::default().fg(COLOR_FG_DIM)),
        Span::raw(" "),
        Span::styled(
            format!("{:14}", truncate(&primary, 14)),
            Style::default().fg(type_color).add_modifier(Modifier::BOLD),
        ),
        Span::raw(" "),
    ];

    let narration = narrate(e);
    if search.is_empty() {
        spans.push(Span::styled(narration, Style::default().fg(COLOR_FG)));
    } else {
        push_highlighted(&mut spans, &narration, search);
    }
    ListItem::new(Line::from(spans))
}

/// Adiciona spans destacando substring `needle` em `haystack`.
fn push_highlighted(out: &mut Vec<Span<'static>>, haystack: &str, needle: &str) {
    let lower = haystack.to_lowercase();
    let needle_lower = needle.to_lowercase();
    let mut pos = 0usize;
    while let Some(rel) = lower[pos..].find(&needle_lower) {
        let abs = pos + rel;
        if abs > pos {
            out.push(Span::styled(
                haystack[pos..abs].to_string(),
                Style::default().fg(COLOR_FG),
            ));
        }
        let end = abs + needle.len();
        out.push(Span::styled(
            haystack[abs..end].to_string(),
            Style::default()
                .fg(COLOR_HIGHLIGHT_BG)
                .bg(COLOR_ACCENT)
                .add_modifier(Modifier::BOLD),
        ));
        pos = end;
    }
    if pos < haystack.len() {
        out.push(Span::styled(
            haystack[pos..].to_string(),
            Style::default().fg(COLOR_FG),
        ));
    }
}

fn color_for_type(t: &str) -> Color {
    match t {
        // Audit: criticidade alta
        "AVC" => COLOR_ERROR,
        "ANOM_PROMISCUOUS" | "ANOM_ABEND" => COLOR_WARN,
        // Audit: autenticacao (accent)
        "USER_AUTH" | "USER_LOGIN" | "USER_ACCT" => COLOR_ACCENT,
        // Journal: priorities syslog
        "EMERG" | "ALERT" | "CRIT" | "ERR" => COLOR_ERROR,
        "WARNING" => COLOR_WARN,
        "NOTICE" => COLOR_FG,
        "INFO" => COLOR_FG_DIM,
        "DEBUG" => COLOR_DIM,
        _ => COLOR_FG,
    }
}

fn truncate(s: &str, n: usize) -> String {
    if s.len() <= n {
        s.to_string()
    } else {
        s.chars().take(n).collect()
    }
}

fn count_by_source(events: &[Event]) -> (usize, usize) {
    let mut audit = 0;
    let mut journal = 0;
    for e in events {
        match e {
            Event::Audit(_) => audit += 1,
            Event::Journal(_) => journal += 1,
        }
    }
    (audit, journal)
}

fn format_event_detail(ev: &Event) -> String {
    match ev {
        Event::Audit(a) => {
            let mut s = format!(
                "[audit] audit_id: {}    timestamp: {}    records: {}\n",
                a.audit_id,
                a.timestamp.format("%Y-%m-%d %H:%M:%S UTC"),
                a.records.len()
            );
            for r in &a.records {
                s.push_str(&format!("\n[{}]\n", r.record_type));
                let mut keys: Vec<&String> = r.fields.keys().collect();
                keys.sort();
                for k in keys {
                    s.push_str(&format!("  {} = {}\n", k, r.fields[k]));
                }
            }
            s
        }
        Event::Journal(j) => {
            let mut s = format!(
                "[journal] timestamp: {}    priority: {}\n",
                j.timestamp.format("%Y-%m-%d %H:%M:%S UTC"),
                j.priority.as_str()
            );
            if let Some(u) = &j.unit {
                s.push_str(&format!("unit: {u}\n"));
            }
            if let Some(c) = &j.comm {
                s.push_str(&format!("comm: {c}\n"));
            }
            if let Some(p) = j.pid {
                s.push_str(&format!("pid:  {p}\n"));
            }
            if let Some(u) = j.uid {
                s.push_str(&format!("uid:  {u}\n"));
            }
            if let Some(h) = &j.hostname {
                s.push_str(&format!("host: {h}\n"));
            }
            s.push_str(&format!("\nmessage:\n  {}\n", j.message));
            if !j.extra.is_empty() {
                s.push_str("\nextras:\n");
                let mut keys: Vec<&String> = j.extra.keys().collect();
                keys.sort();
                for k in keys {
                    s.push_str(&format!("  {} = {}\n", k, j.extra[k]));
                }
            }
            s
        }
    }
}
