"""Named presets: save/load full Settings snapshots as JSON on disk."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .command_builder import Settings

CONFIG_DIR = Path.home() / ".rpicam_tui"
USER_PRESETS_DIR = CONFIG_DIR / "presets"
SEED_PRESETS_DIR = Path(__file__).parent / "presets"


def ensure_user_presets_seeded() -> None:
    """Copy the built-in seed presets into ~/.rpicam_tui/presets on first run."""
    USER_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    if not SEED_PRESETS_DIR.is_dir():
        return
    for seed in SEED_PRESETS_DIR.glob("*.json"):
        target = USER_PRESETS_DIR / seed.name
        if not target.exists():
            shutil.copy(seed, target)


def list_presets() -> list[str]:
    ensure_user_presets_seeded()
    return sorted(p.stem for p in USER_PRESETS_DIR.glob("*.json"))


def save_preset(name: str, settings: Settings) -> Path:
    ensure_user_presets_seeded()
    safe_name = "".join(c for c in name if c.isalnum() or c in "-_") or "preset"
    path = USER_PRESETS_DIR / f"{safe_name}.json"
    path.write_text(json.dumps(settings.to_dict(), indent=2, sort_keys=True))
    return path


def load_preset(name: str) -> Settings:
    ensure_user_presets_seeded()
    path = USER_PRESETS_DIR / f"{name}.json"
    data = json.loads(path.read_text())
    return Settings.from_dict(data)
