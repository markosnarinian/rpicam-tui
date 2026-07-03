"""Run history: an on-disk log of past captures, replayable back into the form."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .command_builder import Settings, command_to_string

HISTORY_PATH = Path.home() / ".rpicam_tui" / "history.json"
MAX_ENTRIES = 200


@dataclass
class HistoryEntry:
    timestamp: str
    mode: str
    command: str
    returncode: Optional[int]
    duration: float
    output_path: str
    settings: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "mode": self.mode,
            "command": self.command,
            "returncode": self.returncode,
            "duration": self.duration,
            "output_path": self.output_path,
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoryEntry":
        return cls(
            timestamp=data["timestamp"],
            mode=data["mode"],
            command=data["command"],
            returncode=data.get("returncode"),
            duration=data.get("duration", 0.0),
            output_path=data.get("output_path", ""),
            settings=data.get("settings", {}),
        )

    def restore_settings(self) -> Settings:
        return Settings.from_dict(self.settings)


def make_entry(argv: list[str], settings: Settings, returncode: Optional[int], duration: float, timestamp: str) -> HistoryEntry:
    return HistoryEntry(
        timestamp=timestamp,
        mode=settings.mode,
        command=command_to_string(argv),
        returncode=returncode,
        duration=duration,
        output_path=settings.output,
        settings=settings.to_dict(),
    )


def load_history() -> list[HistoryEntry]:
    if not HISTORY_PATH.exists():
        return []
    try:
        raw = json.loads(HISTORY_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [HistoryEntry.from_dict(item) for item in raw]


def save_history(entries: list[HistoryEntry]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    trimmed = entries[-MAX_ENTRIES:]
    HISTORY_PATH.write_text(json.dumps([e.to_dict() for e in trimmed], indent=2))


def append_history(entry: HistoryEntry) -> list[HistoryEntry]:
    entries = load_history()
    entries.append(entry)
    save_history(entries)
    return entries
