# rpicam-tui

An interactive terminal UI for building and running `rpicam-still` / `rpicam-vid`
commands on the Raspberry Pi Camera Module 3, without hand-typing long CLI
invocations every time.

This is a **guided wrapper around the real CLI**, not an abstraction that hides
it. Every control in the settings form is labeled with the actual flag it maps
to (`--awb`, `--autofocus-mode`, ...), and the command preview pane always
shows the exact command that will run. Runs are executed with
`asyncio.create_subprocess_exec` against the real `rpicam-still`/`rpicam-vid`
binaries — argv in, argv out, no `picamera2` abstraction layer in between.

## Layout

- **Left pane** — the settings form, grouped into collapsible sections
  (common/capture, autofocus, exposure, white balance/color, still-specific,
  video-specific).
- **Top-right pane** — a live, syntax-highlighted preview of the exact command
  that will run.
- **Bottom-right pane** — tabs for streamed process output and run history.
  Select a history row to reload its settings back into the form.

## Running on the Pi

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m rpicam_tui
# or: python3 run.py
```

`rpicam-still`/`rpicam-vid` must be on `PATH` (they ship with `rpicam-apps` on
Raspberry Pi OS with a Camera Module 3 attached).

## Developing off-Pi (dry-run mode)

The app runs fine on a laptop with no camera attached:

- If `rpicam-still`/`rpicam-vid` isn't found on `PATH`, the runner
  automatically falls back to logging the command instead of executing it —
  you'll see a warning notification on startup and a note in the command
  preview.
- You can also force this at any time with **Ctrl+D** (toggle dry-run), or by
  launching with `python3 -m rpicam_tui --dry-run`.
- In dry-run, "running" a capture just prints `[dry-run] would run: ...` to
  the output log and records a (fake, zero-duration) entry in run history, so
  the whole picking-settings → preview → run → history loop is exercisable
  without hardware.

## Keybindings

| Key      | Action                              |
|----------|--------------------------------------|
| `Ctrl+R` | Run capture                          |
| `Ctrl+X` | Cancel running capture (SIGINT)      |
| `Ctrl+T` | Toggle still/video mode              |
| `Ctrl+S` | Save current settings as a preset    |
| `Ctrl+L` | Load a preset                        |
| `Ctrl+Y` | Copy the current command to clipboard|
| `Ctrl+D` | Toggle dry-run mode                  |
| `Ctrl+Q` | Quit (cancels any running capture)   |

## Presets

Presets are JSON snapshots of the full settings form, stored at
`~/.rpicam_tui/presets/*.json`. A few are seeded on first run (copied from
`rpicam_tui/presets/` in the package):

- `default-still` — general-purpose full-resolution still capture.
- `default-video` — general-purpose 1080p30 video capture.
- `vehicle-mount` — manual focus at ~10m (`--lens-position 0.1`), a fast
  `--shutter 8000` to fight rolling-shutter blur from vibration, and a higher
  `--bitrate 10000000`.

## Run history

Every run (including dry runs) is appended to `~/.rpicam_tui/history.json`
with its timestamp, full command, exit code, duration, and output path.
Selecting a row in the History tab reloads that run's settings back into the
form so you can tweak and rerun.

## Project layout

```
rpicam_tui/
  command_builder.py   # pure Settings -> argv logic, unit-testable, no I/O
  runner.py            # async subprocess execution + cancellation
  field_specs.py        # declarative form schema (flags, help text, groups)
  presets.py            # preset save/load
  history.py            # run history persistence
  widgets.py             # reusable Textual form/preview widgets
  app.py                 # the Textual App tying it all together
  presets/                # seed preset JSON files
tests/
  test_command_builder.py
run.py                    # `python3 run.py` convenience entry point
```

## Tests

```bash
pip install pytest
pytest
```

`command_builder.py` has no Textual or subprocess dependency, so its tests
run instantly and cover the argv-building logic directly.
