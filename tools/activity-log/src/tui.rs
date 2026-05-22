//! Interface TUI para navegar nos eventos parseados.
//!
//! Layout:
//!   ┌─────────────────────────────────────────────────────────┐
//!   │ Vigia Activity Log — {n} eventos                        │
//!   ├─────────────────────────────────────────────────────────┤
//!   │ > 14:23:12  AVC          SELinux bloqueou httpd...      │
//!   │   14:23:15  USER_AUTH    autenticacao via sudo: OK      │
//!   │   ...                                                    │
//!   ├─────────────────────────────────────────────────────────┤
//!   │ Detalhes do evento selecionado (records raw)            │
//!   ├─────────────────────────────────────────────────────────┤
//!   │ ↑↓ navega   q sai                                       │
//!   └─────────────────────────────────────────────────────────┘
//!
//! Cores: VigiaOS-style (zinc bg + emerald accent).

use std::io::{self, Stdout};
use std::time::Duration;

use anyhow::Result;
use crossterm::event::{self, Event, KeyCode, KeyEventKind};
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

use crate::audit::AuditEvent;
use crate::narrator::narrate;

// Paleta VigiaOS (Tailwind zinc + emerald)
const COLOR_ACCENT: Color = Color::Rgb(0x34, 0xd3, 0x99); // emerald-400
const COLOR_DIM: Color = Color::Rgb(0x71, 0x71, 0x7a);    // zinc-500
const COLOR_FG: Color = Color::Rgb(0xfa, 0xfa, 0xfa);     // zinc-50
const COLOR_WARN: Color = Color::Rgb(0xfb, 0xbf, 0x24);   // amber-400
const COLOR_ERROR: Color = Color::Rgb(0xf8, 0x71, 0x71);  // red-400

type Backend = CrosstermBackend<Stdout>;

pub fn run(events: Vec<AuditEvent>) -> Result<()> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let mut terminal = Terminal::new(CrosstermBackend::new(stdout))?;

    let res = main_loop(&mut terminal, events);

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;
    res
}

fn main_loop(terminal: &mut Terminal<Backend>, events: Vec<AuditEvent>) -> Result<()> {
    let mut list_state = ListState::default();
    if !events.is_empty() {
        list_state.select(Some(0));
    }

    loop {
        terminal.draw(|f| draw(f, &events, &mut list_state))?;

        if !event::poll(Duration::from_millis(200))? {
            continue;
        }
        if let Event::Key(key) = event::read()? {
            if key.kind != KeyEventKind::Press {
                continue;
            }
            match key.code {
                KeyCode::Char('q') | KeyCode::Esc => return Ok(()),
                KeyCode::Down | KeyCode::Char('j') => move_selection(&mut list_state, &events, 1),
                KeyCode::Up | KeyCode::Char('k') => move_selection(&mut list_state, &events, -1),
                KeyCode::PageDown => move_selection(&mut list_state, &events, 10),
                KeyCode::PageUp => move_selection(&mut list_state, &events, -10),
                KeyCode::Home => {
                    if !events.is_empty() {
                        list_state.select(Some(0));
                    }
                }
                KeyCode::End => {
                    if !events.is_empty() {
                        list_state.select(Some(events.len() - 1));
                    }
                }
                _ => {}
            }
        }
    }
}

fn move_selection(state: &mut ListState, events: &[AuditEvent], delta: i32) {
    if events.is_empty() {
        return;
    }
    let cur = state.selected().unwrap_or(0) as i32;
    let max = (events.len() - 1) as i32;
    let new = (cur + delta).clamp(0, max);
    state.select(Some(new as usize));
}

fn draw(f: &mut ratatui::Frame, events: &[AuditEvent], state: &mut ListState) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // header
            Constraint::Min(5),     // event list
            Constraint::Length(10), // detail panel
            Constraint::Length(1),  // status bar
        ])
        .split(f.area());

    // Header
    let header = Paragraph::new(Line::from(vec![
        Span::styled("VIGIA", Style::default().fg(COLOR_ACCENT).add_modifier(Modifier::BOLD)),
        Span::styled("·OS", Style::default().fg(COLOR_FG).add_modifier(Modifier::BOLD)),
        Span::styled(" Activity Log  ", Style::default().fg(COLOR_FG)),
        Span::styled(
            format!("· {} eventos", events.len()),
            Style::default().fg(COLOR_DIM),
        ),
    ]))
    .block(Block::default().borders(Borders::BOTTOM));
    f.render_widget(header, chunks[0]);

    // Event list
    let items: Vec<ListItem> = events
        .iter()
        .map(|e| {
            let ts = e.timestamp.format("%H:%M:%S").to_string();
            let type_color = color_for_type(e.primary_type());
            let line = Line::from(vec![
                Span::styled(ts, Style::default().fg(COLOR_DIM)),
                Span::raw("  "),
                Span::styled(
                    format!("{:14}", e.primary_type()),
                    Style::default().fg(type_color).add_modifier(Modifier::BOLD),
                ),
                Span::raw(" "),
                Span::styled(narrate(e), Style::default().fg(COLOR_FG)),
            ]);
            ListItem::new(line)
        })
        .collect();

    let list = List::new(items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(" eventos ")
                .border_style(Style::default().fg(COLOR_DIM)),
        )
        .highlight_style(
            Style::default()
                .bg(Color::Rgb(0x18, 0x18, 0x1b))
                .add_modifier(Modifier::BOLD),
        )
        .highlight_symbol("> ");
    f.render_stateful_widget(list, chunks[1], state);

    // Detail panel
    let detail_text = state
        .selected()
        .and_then(|i| events.get(i))
        .map(format_event_detail)
        .unwrap_or_else(|| "Nenhum evento selecionado".to_string());

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

    // Status bar
    let status = Paragraph::new(Line::from(vec![
        Span::styled(" ↑↓/jk ", Style::default().fg(COLOR_ACCENT)),
        Span::styled("navega", Style::default().fg(COLOR_DIM)),
        Span::styled("  PgUp/PgDn ", Style::default().fg(COLOR_ACCENT)),
        Span::styled("rapido", Style::default().fg(COLOR_DIM)),
        Span::styled("  q ", Style::default().fg(COLOR_ACCENT)),
        Span::styled("sai", Style::default().fg(COLOR_DIM)),
    ]));
    f.render_widget(status, chunks[3]);
}

fn color_for_type(t: &str) -> Color {
    match t {
        "AVC" => COLOR_ERROR,
        "USER_AUTH" | "USER_LOGIN" | "USER_ACCT" => COLOR_ACCENT,
        "ANOM_PROMISCUOUS" | "ANOM_ABEND" => COLOR_WARN,
        _ => COLOR_FG,
    }
}

fn format_event_detail(ev: &AuditEvent) -> String {
    let mut s = format!(
        "audit_id: {}    timestamp: {}    records: {}\n",
        ev.audit_id,
        ev.timestamp.format("%Y-%m-%d %H:%M:%S UTC"),
        ev.records.len()
    );
    for r in &ev.records {
        s.push_str(&format!("\n[{}]\n", r.record_type));
        let mut keys: Vec<&String> = r.fields.keys().collect();
        keys.sort();
        for k in keys {
            s.push_str(&format!("  {} = {}\n", k, r.fields[k]));
        }
    }
    s
}
