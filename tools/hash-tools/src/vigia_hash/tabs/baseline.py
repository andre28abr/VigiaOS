"""Tab Baseline: cria snapshot de diretorio + compara contra estado atual."""

from __future__ import annotations

import threading
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, make_file_picker_row, show_error, show_info


class BaselineTab(Adw.Bin):
    """Snapshot de diretorio + diff contra estado atual."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._last_compare: backend.CompareResult | None = None

        # Header
        header_lbl = Gtk.Label(label="Baseline & comparativo")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(4)

        header_desc = Gtk.Label(
            label=(
                "Cria um <b>baseline</b> (snapshot de hashes) de um diretorio. "
                "Depois compara contra o estado atual e mostra arquivos "
                "<i>adicionados</i>, <i>removidos</i> ou <i>modificados</i>.\n\n"
                "<b>Caso de uso</b>: voce tem o diretorio <tt>/etc/</tt> ou "
                "pasta de configs critica de uma aplicacao. Cria baseline. "
                "Apos algum tempo, roda comparativo — qualquer diff e' suspeito."
            )
        )
        header_desc.set_use_markup(True)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(16)

        # Create baseline group
        create_group = Adw.PreferencesGroup()
        create_group.set_title("Criar baseline")
        create_group.set_description(
            "Salvo em ~/.local/share/vigia-hash/ com permissoes 0600 (LGPD)."
        )

        self._cdir_entry = Gtk.Entry()
        self._cdir_entry.set_placeholder_text("/caminho/para/diretorio")
        self._cdir_entry.set_hexpand(True)
        create_group.add(make_file_picker_row("Diretorio", self._cdir_entry, folder_only=True))

        self._create_algo = Gtk.DropDown.new_from_strings(backend.list_algorithms())
        self._create_algo.set_selected(0)
        algo_row = Adw.ActionRow(title="Algoritmo")
        algo_row.add_suffix(self._create_algo)
        create_group.add(algo_row)

        # Create action
        create_btn_row = Adw.ActionRow()
        create_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        create_btn_box.set_halign(Gtk.Align.END)
        self._create_btn = Gtk.Button(label="Criar baseline")
        self._create_btn.add_css_class("suggested-action")
        self._create_btn.add_css_class("pill")
        self._create_btn.connect("clicked", lambda _b: self._start_create())
        create_btn_box.append(self._create_btn)
        self._create_spinner = Gtk.Spinner()
        create_btn_box.append(self._create_spinner)
        create_btn_row.set_child(create_btn_box)
        create_btn_row.set_activatable(False)
        create_group.add(create_btn_row)

        self._create_status = Gtk.Label(label="")
        self._create_status.add_css_class("dim-label")
        self._create_status.set_halign(Gtk.Align.START)
        self._create_status.set_wrap(True)
        self._create_status.set_xalign(0)

        # Compare group
        compare_group = Adw.PreferencesGroup()
        compare_group.set_title("Comparar contra baseline")

        self._baseline_entry = Gtk.Entry()
        self._baseline_entry.set_placeholder_text("baseline JSON")
        self._baseline_entry.set_hexpand(True)
        compare_group.add(make_file_picker_row("Baseline file", self._baseline_entry))

        cmp_btn_row = Adw.ActionRow()
        cmp_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cmp_btn_box.set_halign(Gtk.Align.END)
        self._compare_btn = Gtk.Button(label="Comparar")
        self._compare_btn.add_css_class("suggested-action")
        self._compare_btn.add_css_class("pill")
        self._compare_btn.connect("clicked", lambda _b: self._start_compare())
        cmp_btn_box.append(self._compare_btn)
        self._compare_spinner = Gtk.Spinner()
        cmp_btn_box.append(self._compare_spinner)
        cmp_btn_row.set_child(cmp_btn_box)
        cmp_btn_row.set_activatable(False)
        compare_group.add(cmp_btn_row)

        # Compare results
        self._compare_status = Gtk.Label(label="")
        self._compare_status.add_css_class("dim-label")
        self._compare_status.set_halign(Gtk.Align.START)
        self._compare_status.set_wrap(True)
        self._compare_status.set_xalign(0)

        self._diff_group = Adw.PreferencesGroup()
        self._diff_group.set_title("Diferencas detectadas")
        self._diff_rows: list = []
        self._render_diff()

        # Available baselines
        list_group = Adw.PreferencesGroup()
        list_group.set_title("Baselines disponiveis")
        list_group.set_description(
            "Baselines criados pelo Vigia, em ~/.local/share/vigia-hash/."
        )
        self._list_group = list_group
        self._list_rows: list = []

        list_btn_row = Adw.ActionRow()
        list_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        list_btn_box.set_halign(Gtk.Align.END)
        refresh_btn = Gtk.Button(label="Recarregar lista")
        refresh_btn.add_css_class("pill")
        refresh_btn.connect("clicked", lambda _b: self._refresh_baselines())
        list_btn_box.append(refresh_btn)
        list_btn_row.set_child(list_btn_box)
        list_btn_row.set_activatable(False)
        list_group.add(list_btn_row)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(create_group)
        outer.append(self._create_status)
        outer.append(compare_group)
        outer.append(self._compare_status)
        outer.append(self._diff_group)
        outer.append(list_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self._refresh_baselines()

    # ============================================================
    # Create
    # ============================================================

    def _start_create(self) -> None:
        if self._running:
            return
        dirpath = self._cdir_entry.get_text().strip()
        if not dirpath:
            show_error(self, "Sem diretorio", "Informe o diretorio para baseline.")
            return

        algo = backend.list_algorithms()[self._create_algo.get_selected()]

        self._running = True
        self._create_btn.set_sensitive(False)
        self._compare_btn.set_sensitive(False)
        self._create_spinner.start()
        self._create_status.set_label("Hashing arquivos... pode levar minutos em diretorio grande.")

        threading.Thread(target=self._create_worker, args=(dirpath, algo), daemon=True).start()

    def _create_worker(self, dirpath: str, algo: str) -> None:
        result = backend.create_baseline_blocking(dirpath, None, algo)
        GLib.idle_add(self._on_create_done, result)

    def _on_create_done(self, result: backend.BaselineResult) -> bool:
        self._running = False
        self._create_btn.set_sensitive(True)
        self._compare_btn.set_sensitive(True)
        self._create_spinner.stop()

        if result.error:
            self._create_status.set_label(f"Erro: {result.error}")
            return False

        self._create_status.set_label(
            f"Baseline criado com {result.file_count} arquivos. "
            f"Salvo em {result.output_file}"
        )
        # Auto-popula o campo de comparacao com este baseline
        self._baseline_entry.set_text(result.output_file)
        self._refresh_baselines()
        show_info(
            self,
            "Baseline criado",
            f"{result.file_count} arquivo(s) hasheados.\nSalvo em {result.output_file}.",
        )
        return False

    # ============================================================
    # Compare
    # ============================================================

    def _start_compare(self) -> None:
        if self._running:
            return
        bf = self._baseline_entry.get_text().strip()
        if not bf:
            show_error(self, "Sem baseline", "Informe o arquivo baseline JSON.")
            return

        self._running = True
        self._create_btn.set_sensitive(False)
        self._compare_btn.set_sensitive(False)
        self._compare_spinner.start()
        self._compare_status.set_label("Comparando... pode levar minutos em diretorio grande.")

        threading.Thread(target=self._compare_worker, args=(bf,), daemon=True).start()

    def _compare_worker(self, baseline_file: str) -> None:
        result = backend.compare_baseline_blocking(baseline_file, None, None)
        GLib.idle_add(self._on_compare_done, result)

    def _on_compare_done(self, result: backend.CompareResult) -> bool:
        self._running = False
        self._create_btn.set_sensitive(True)
        self._compare_btn.set_sensitive(True)
        self._compare_spinner.stop()

        if result.error:
            self._compare_status.set_label(f"Erro: {result.error}")
            return False

        n_added = len(result.added)
        n_removed = len(result.removed)
        n_modified = len(result.modified)
        n_total_diff = n_added + n_removed + n_modified

        if n_total_diff == 0:
            self._compare_status.set_label(
                f"✓ Nenhuma diferenca. {result.unchanged} arquivo(s) inalterado(s)."
            )
        else:
            self._compare_status.set_label(
                f"⚠ {n_total_diff} diferenca(s): "
                f"{n_added} adicionado(s), {n_modified} modificado(s), "
                f"{n_removed} removido(s). "
                f"{result.unchanged} inalterado(s)."
            )

        self._last_compare = result
        self._render_diff()
        return False

    def _render_diff(self) -> None:
        for r in self._diff_rows:
            self._diff_group.remove(r)
        self._diff_rows = []

        if self._last_compare is None:
            row = Adw.ActionRow(title="Nenhuma comparacao ainda")
            row.set_subtitle("Crie um baseline e clique 'Comparar' para popular.")
            row.add_css_class("dim-label")
            self._diff_group.add(row)
            self._diff_rows.append(row)
            return

        if (not self._last_compare.added and
            not self._last_compare.removed and
            not self._last_compare.modified):
            row = Adw.ActionRow(title="Nenhuma diferenca")
            row.set_subtitle("Diretorio inalterado desde o baseline.")
            row.add_css_class("success")
            self._diff_group.add(row)
            self._diff_rows.append(row)
            return

        def _add(category: str, css: str, paths: list[str], limit: int = 30) -> None:
            shown = paths[:limit]
            for path in shown:
                row = Adw.ActionRow(title=path)
                row.add_css_class("property")
                badge = Gtk.Label(label=category)
                badge.add_css_class("monospace")
                badge.add_css_class("caption-heading")
                badge.add_css_class(css)
                badge.set_valign(Gtk.Align.CENTER)
                row.add_prefix(badge)
                self._diff_group.add(row)
                self._diff_rows.append(row)
            if len(paths) > limit:
                more = Adw.ActionRow(
                    title=f"... +{len(paths) - limit} {category.lower()}s (mostrando primeiros {limit})"
                )
                more.add_css_class("dim-label")
                self._diff_group.add(more)
                self._diff_rows.append(more)

        _add("MOD", "warning", self._last_compare.modified)
        _add("ADD", "success", self._last_compare.added)
        _add("REM", "error", self._last_compare.removed)

    # ============================================================
    # Baselines list
    # ============================================================

    def _refresh_baselines(self) -> None:
        threading.Thread(target=self._refresh_baselines_worker, daemon=True).start()

    def _refresh_baselines_worker(self) -> None:
        baselines = backend.list_baselines()
        GLib.idle_add(self._apply_baselines, baselines)

    def _apply_baselines(self, baselines: list[dict]) -> bool:
        for r in self._list_rows:
            self._list_group.remove(r)
        self._list_rows = []

        if not baselines:
            row = Adw.ActionRow(title="Nenhum baseline criado ainda")
            row.add_css_class("dim-label")
            self._list_group.add(row)
            self._list_rows.append(row)
            return False

        for b in baselines:
            ts = b.get("created_at", "?")
            try:
                dt = datetime.fromisoformat(ts)
                ts_h = dt.strftime("%d/%m %H:%M")
            except (TypeError, ValueError):
                ts_h = ts

            row = Adw.ActionRow(title=b.get("directory", "?"))
            row.set_subtitle(
                f"{ts_h} · {b.get('file_count', 0)} arquivos · "
                f"algo: {b.get('algorithm', '?')}"
            )

            use_btn = Gtk.Button(label="Usar")
            use_btn.add_css_class("pill")
            use_btn.add_css_class("flat")
            use_btn.set_valign(Gtk.Align.CENTER)
            file_path = b.get("_file", "")
            use_btn.connect(
                "clicked",
                lambda _b, p=file_path: self._baseline_entry.set_text(p),
            )
            row.add_suffix(use_btn)

            self._list_group.add(row)
            self._list_rows.append(row)

        return False
