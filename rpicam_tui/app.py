"""Textual TUI: guided wrapper around rpicam-still / rpicam-vid.

The settings form always mirrors real rpicam-* flags, and the command
preview pane is the source of truth for what will actually run -- this app
never hides the underlying CLI behind an abstraction.
"""
from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import datetime
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    DataTable,
    Footer,
    Header,
    Input,
    OptionList,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from . import history, presets
from .command_builder import (
    MODE_STILL,
    MODE_VIDEO,
    RESOLUTION_PRESETS,
    Settings,
    build_command,
    command_to_string,
    switch_mode,
)
from .field_specs import GROUPS, KIND_BOOL, KIND_FLOAT, KIND_INT, KIND_SELECT, FieldSpec, all_field_specs
from .runner import CaptureRunner
from .widgets import CommandPreview, LabeledCheckbox, LabeledInput, LabeledSelect

SETTINGS_FIELD_NAMES = {f.name for f in dataclass_fields(Settings)}


class SavePresetScreen(ModalScreen[Optional[str]]):
    DEFAULT_CSS = """
    SavePresetScreen { align: center middle; }
    SavePresetScreen > Vertical {
        width: 50; height: auto; border: thick $accent; padding: 1 2; background: $surface;
    }
    SavePresetScreen Horizontal { height: auto; margin-top: 1; }
    SavePresetScreen Button { margin-right: 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Save current settings as preset:")
            yield Input(placeholder="preset-name", id="preset-name-input")
            with Horizontal():
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#preset-name-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            name = self.query_one("#preset-name-input", Input).value.strip()
            self.dismiss(name or None)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class LoadPresetScreen(ModalScreen[Optional[str]]):
    DEFAULT_CSS = """
    LoadPresetScreen { align: center middle; }
    LoadPresetScreen > Vertical {
        width: 50; height: auto; max-height: 20; border: thick $accent; padding: 1 2; background: $surface;
    }
    """

    def __init__(self, names: list[str]) -> None:
        super().__init__()
        self.names = names

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Select a preset to load (Esc to cancel):")
            yield OptionList(*self.names, id="preset-list")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option.prompt))

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class RpicamTuiApp(App[None]):
    """Guided settings explorer for rpicam-still / rpicam-vid."""

    TITLE = "rpicam-tui"

    CSS = """
    #settings-pane {
        width: 44%;
        border-right: solid $accent;
        padding: 0 1;
    }
    #right-pane {
        width: 1fr;
        padding: 0 1;
    }
    #output-log {
        height: 1fr;
    }
    #history-table {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("ctrl+r", "run_capture", "Run"),
        Binding("ctrl+x", "cancel_capture", "Cancel"),
        Binding("ctrl+t", "switch_mode", "Still/Video"),
        Binding("ctrl+s", "save_preset", "Save preset"),
        Binding("ctrl+l", "load_preset", "Load preset"),
        Binding("ctrl+y", "copy_command", "Copy cmd"),
        Binding("ctrl+d", "toggle_dry_run", "Dry-run"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, dry_run: bool = False) -> None:
        super().__init__()
        self.settings = Settings()
        self.dry_run = dry_run
        self.runner = CaptureRunner()
        self.history_entries: list[history.HistoryEntry] = []
        self._syncing = False

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with VerticalScroll(id="settings-pane"):
                for i, group in enumerate(GROUPS):
                    with Collapsible(title=group.title, id=f"group-{i}", collapsed=group.collapsed):
                        for spec in group.fields:
                            yield self._build_field_widget(spec)
            with Vertical(id="right-pane"):
                yield CommandPreview(id="preview")
                with TabbedContent(id="output-tabs"):
                    with TabPane("Output", id="tab-output"):
                        yield RichLog(id="output-log", highlight=False, markup=False, wrap=True)
                    with TabPane("History", id="tab-history"):
                        yield DataTable(id="history-table")
        yield Footer()

    def _build_field_widget(self, spec: FieldSpec):
        if spec.name == "resolution_preset":
            return LabeledSelect(spec.name, spec.flag, spec.help, spec.options, "custom")
        value = getattr(self.settings, spec.name) if spec.name in SETTINGS_FIELD_NAMES else None
        if spec.kind == KIND_BOOL:
            return LabeledCheckbox(spec.name, spec.flag, spec.help, bool(value))
        if spec.kind == KIND_SELECT:
            return LabeledSelect(spec.name, spec.flag, spec.help, spec.options, value)
        text = "" if value is None else str(value)
        return LabeledInput(spec.name, spec.flag, spec.help, value=text)

    def on_mount(self) -> None:
        presets.ensure_user_presets_seeded()
        self.history_entries = history.load_history()
        table = self.query_one("#history-table", DataTable)
        table.add_columns("Time", "Mode", "Exit", "Duration", "Output")
        table.cursor_type = "row"
        self.refresh_history_table()
        self.update_group_visibility()
        self._toggle_dependent_fields()
        self.update_preview()
        if not self.dry_run and not self.runner.binary_available("rpicam-still"):
            self.notify(
                "rpicam-still/rpicam-vid not found on this machine — running in dry-run fallback.",
                severity="warning",
                timeout=6,
            )

    # ------------------------------------------------------------------ #
    # Form <-> Settings sync
    # ------------------------------------------------------------------ #
    def read_settings_from_form(self) -> Settings:
        data = self.settings.to_dict()
        for spec in all_field_specs():
            if spec.name not in SETTINGS_FIELD_NAMES:
                continue
            widget = self.query_one(f"#field-{spec.name}")
            data[spec.name] = self._widget_value(widget, spec)
        return Settings.from_dict(data)

    @staticmethod
    def _widget_value(widget, spec: FieldSpec):
        if spec.kind == KIND_BOOL:
            return bool(widget.value)
        if spec.kind == KIND_SELECT:
            return widget.value
        text = (widget.value or "").strip()
        if spec.kind == KIND_INT:
            if not text:
                return None if spec.optional else 0
            try:
                return int(text)
            except ValueError:
                return None if spec.optional else 0
        if spec.kind == KIND_FLOAT:
            if not text:
                return None
            try:
                return float(text)
            except ValueError:
                return None
        return text

    def apply_settings_to_form(self, settings: Settings) -> None:
        self._syncing = True
        try:
            for spec in all_field_specs():
                if spec.name not in SETTINGS_FIELD_NAMES:
                    continue
                widget = self.query_one(f"#field-{spec.name}")
                value = getattr(settings, spec.name)
                if spec.kind == KIND_BOOL:
                    widget.value = bool(value)
                elif spec.kind == KIND_SELECT:
                    widget.value = value
                else:
                    widget.value = "" if value is None else str(value)
        finally:
            self._syncing = False
        self._toggle_dependent_fields()

    def update_group_visibility(self) -> None:
        for i, group in enumerate(GROUPS):
            self.query_one(f"#group-{i}", Collapsible).display = self.settings.mode in group.modes

    def _toggle_dependent_fields(self) -> None:
        self.query_one("#field-lens_position", Input).disabled = self.settings.af_mode != "manual"
        self.query_one("#field-awb_gains", Input).disabled = self.settings.awb != "custom"

    def update_preview(self) -> None:
        argv = build_command(self.settings)
        preview = self.query_one(CommandPreview)
        note = None
        if not self.dry_run and not self.runner.binary_available(argv[0]):
            note = f"Note: '{argv[0]}' not found on PATH -- will run as dry-run when executed."
        preview.update_command(command_to_string(argv), self.dry_run, note)
        self.sub_title = f"{self.settings.mode.upper()}" + ("  [DRY RUN]" if self.dry_run else "")

    def _on_form_changed(self) -> None:
        self.settings = self.read_settings_from_form()
        self._toggle_dependent_fields()
        self.update_preview()

    def _apply_resolution_preset(self, value) -> None:
        if value in ("custom", None, Select.BLANK):
            return
        preset = RESOLUTION_PRESETS.get(value)
        if not preset:
            return
        width, height = preset
        self._syncing = True
        try:
            self.query_one("#field-width", Input).value = str(width)
            self.query_one("#field-height", Input).value = str(height)
        finally:
            self._syncing = False
        self._on_form_changed()

    # ------------------------------------------------------------------ #
    # Widget events
    # ------------------------------------------------------------------ #
    def on_input_changed(self, event: Input.Changed) -> None:
        if self._syncing:
            return
        self._on_form_changed()

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._syncing:
            return
        if event.select.id == "field-resolution_preset":
            self._apply_resolution_preset(event.value)
            return
        self._on_form_changed()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if self._syncing:
            return
        self._on_form_changed()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key.value is None:
            return
        idx = int(event.row_key.value)
        entry = self.history_entries[idx]
        self.settings = entry.restore_settings()
        self.apply_settings_to_form(self.settings)
        self.update_group_visibility()
        self.update_preview()
        self.notify(f"Loaded settings from {entry.timestamp} — tweak and Ctrl+R to rerun")

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def action_switch_mode(self) -> None:
        new_mode = MODE_VIDEO if self.settings.mode == MODE_STILL else MODE_STILL
        self.settings = switch_mode(self.read_settings_from_form(), new_mode)
        self.apply_settings_to_form(self.settings)
        self.update_group_visibility()
        self.update_preview()

    def action_toggle_dry_run(self) -> None:
        self.dry_run = not self.dry_run
        self.update_preview()
        self.notify(f"Dry-run mode: {'ON' if self.dry_run else 'OFF'}")

    def action_copy_command(self) -> None:
        argv = build_command(self.read_settings_from_form())
        cmd = command_to_string(argv)
        try:
            self.copy_to_clipboard(cmd)
            self.notify("Command copied to clipboard")
        except Exception:
            self.notify(f"Copy failed, command was:\n{cmd}", severity="warning", timeout=8)

    def action_run_capture(self) -> None:
        if self.runner.running:
            self.notify("A capture is already running", severity="warning")
            return
        self.settings = self.read_settings_from_form()
        argv = build_command(self.settings)
        self.run_worker(self._do_run(argv, self.settings), exclusive=True, group="capture")

    def action_cancel_capture(self) -> None:
        if self.runner.cancel():
            self.query_one("#output-log", RichLog).write("^C sent to running process...")
        else:
            self.notify("Nothing running to cancel", severity="warning")

    def action_quit(self) -> None:
        if self.runner.running:
            self.runner.cancel()
        self.exit()

    async def action_save_preset(self) -> None:
        name = await self.push_screen_wait(SavePresetScreen())
        if name:
            path = presets.save_preset(name, self.read_settings_from_form())
            self.notify(f"Saved preset '{name}' to {path}")

    async def action_load_preset(self) -> None:
        names = presets.list_presets()
        if not names:
            self.notify("No presets found", severity="warning")
            return
        name = await self.push_screen_wait(LoadPresetScreen(names))
        if name:
            self.settings = presets.load_preset(name)
            self.apply_settings_to_form(self.settings)
            self.update_group_visibility()
            self.update_preview()
            self.notify(f"Loaded preset '{name}'")

    # ------------------------------------------------------------------ #
    # Capture execution
    # ------------------------------------------------------------------ #
    async def _do_run(self, argv: list[str], settings: Settings) -> None:
        log = self.query_one("#output-log", RichLog)
        log.write(f"$ {command_to_string(argv)}")

        def on_line(line: str) -> None:
            log.write(line)

        result = await self.runner.run(argv, on_line=on_line, dry_run=self.dry_run)
        status = "cancelled" if result.cancelled else f"exit code {result.returncode}"
        log.write(f"-- {status}, duration {result.duration:.1f}s --")

        entry = history.make_entry(
            argv,
            settings,
            result.returncode,
            result.duration,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.history_entries = history.append_history(entry)
        self.refresh_history_table()

    def refresh_history_table(self) -> None:
        table = self.query_one("#history-table", DataTable)
        table.clear()
        for i, entry in enumerate(self.history_entries):
            table.add_row(
                entry.timestamp,
                entry.mode,
                str(entry.returncode),
                f"{entry.duration:.1f}s",
                entry.output_path,
                key=str(i),
            )


def main() -> None:
    import sys

    dry_run = "--dry-run" in sys.argv
    RpicamTuiApp(dry_run=dry_run).run()


if __name__ == "__main__":
    main()
