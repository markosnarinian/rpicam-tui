"""Reusable Textual widgets for the settings form and command preview.

Each form control shows the real rpicam-* flag name as its label (not just a
friendly name) so the operator learns the CLI mapping while using the TUI.
"""
from __future__ import annotations

from typing import Optional

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Checkbox, Input, Select, Static


class LabeledInput(Vertical):
    """A flag name + one-line help text + a text Input, stacked vertically."""

    DEFAULT_CSS = """
    LabeledInput {
        height: auto;
        margin-bottom: 1;
    }
    LabeledInput > .flag-label {
        color: $accent;
        text-style: bold;
    }
    LabeledInput > .help-text {
        color: $text-muted;
    }
    """

    def __init__(self, field_name: str, flag: str, help_text: str, value: str = "", placeholder: str = ""):
        super().__init__()
        self.field_name = field_name
        self.flag = flag
        self.help_text = help_text
        self._value = value
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield Static(self.flag, classes="flag-label")
        yield Static(self.help_text, classes="help-text")
        yield Input(value=self._value, placeholder=self._placeholder, id=f"field-{self.field_name}")


class LabeledSelect(Vertical):
    """A flag name + one-line help text + a dropdown Select, stacked vertically."""

    DEFAULT_CSS = """
    LabeledSelect {
        height: auto;
        margin-bottom: 1;
    }
    LabeledSelect > .flag-label {
        color: $accent;
        text-style: bold;
    }
    LabeledSelect > .help-text {
        color: $text-muted;
    }
    """

    def __init__(self, field_name: str, flag: str, help_text: str, options: list[str], value: str):
        super().__init__()
        self.field_name = field_name
        self.flag = flag
        self.help_text = help_text
        self._options = [(opt, opt) for opt in options]
        self._value = value

    def compose(self) -> ComposeResult:
        yield Static(self.flag, classes="flag-label")
        yield Static(self.help_text, classes="help-text")
        yield Select(self._options, value=self._value, id=f"field-{self.field_name}", allow_blank=False)


class LabeledCheckbox(Vertical):
    """A flag name + one-line help text + a Checkbox."""

    DEFAULT_CSS = """
    LabeledCheckbox {
        height: auto;
        margin-bottom: 1;
    }
    LabeledCheckbox > .help-text {
        color: $text-muted;
    }
    """

    def __init__(self, field_name: str, flag: str, help_text: str, value: bool = False):
        super().__init__()
        self.field_name = field_name
        self.flag = flag
        self.help_text = help_text
        self._value = value

    def compose(self) -> ComposeResult:
        yield Checkbox(self.flag, value=self._value, id=f"field-{self.field_name}")
        yield Static(self.help_text, classes="help-text")


class CommandPreview(Static):
    """Read-only, syntax-highlighted preview of the exact command that will run."""

    DEFAULT_CSS = """
    CommandPreview {
        height: auto;
        min-height: 5;
        border: round $accent;
        padding: 1;
        background: $surface;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_command(self, command_str: str, dry_run: bool, note: Optional[str] = None) -> None:
        prefix = "[DRY RUN] " if dry_run else ""
        lines = [prefix + command_str]
        if note:
            lines.append("")
            lines.append(note)
        syntax = Syntax("\n".join(lines), "bash", theme="ansi_dark", word_wrap=True)
        self.update(syntax)
