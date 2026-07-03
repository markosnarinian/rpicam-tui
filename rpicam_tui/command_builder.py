"""Pure logic for turning a Settings object into an rpicam-still/rpicam-vid argv list.

No Textual, no subprocess, no I/O — this module is independently unit-testable.
"""
from __future__ import annotations

import shlex
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any, Optional

MODE_STILL = "still"
MODE_VIDEO = "video"

BINARY = {
    MODE_STILL: "rpicam-still",
    MODE_VIDEO: "rpicam-vid",
}

RESOLUTION_PRESETS = {
    "4608x2592 (full)": (4608, 2592),
    "1920x1080": (1920, 1080),
    "1280x720": (1280, 720),
}

AF_MODES = ["auto", "manual", "continuous"]
AF_RANGES = ["normal", "macro", "full"]
AF_SPEEDS = ["normal", "fast"]
METERING_MODES = ["centre", "spot", "average", "custom"]
EXPOSURE_MODES = ["normal", "sport", "long"]
AWB_MODES = [
    "auto", "incandescent", "tungsten", "fluorescent",
    "indoor", "daylight", "cloudy", "custom",
]
DENOISE_MODES = ["auto", "off", "cdn_off", "cdn_fast", "cdn_hq"]
HDR_MODES = ["off", "auto", "single-exp", "sensor"]
ENCODINGS = ["jpg", "png", "bmp", "rgb", "yuv420"]
CODECS = ["h264", "mjpeg", "yuv420"]


def default_output_path(mode: str) -> str:
    ext = "jpg" if mode == MODE_STILL else "h264"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"capture_{ts}.{ext}"


@dataclass
class Settings:
    mode: str = MODE_STILL

    # Common / capture
    camera: int = 0
    width: int = 1920
    height: int = 1080
    timeout: int = 5000
    output: str = field(default_factory=lambda: default_output_path(MODE_STILL))
    nopreview: bool = True
    verbose: bool = False

    # Autofocus (Module 3 specific)
    af_mode: str = "continuous"
    af_range: str = "normal"
    af_speed: str = "normal"
    lens_position: Optional[float] = None
    af_window: str = ""  # "x,y,w,h"

    # Exposure
    shutter: Optional[int] = None
    gain: Optional[float] = None
    ev: Optional[float] = None
    metering: str = "centre"
    exposure: str = "normal"

    # White balance / color
    awb: str = "auto"
    awb_gains: str = ""  # "r,b"
    saturation: Optional[float] = None
    contrast: Optional[float] = None
    sharpness: Optional[float] = None
    brightness: Optional[float] = None
    denoise: str = "auto"
    hdr: str = "off"

    # Still-specific
    quality: int = 93
    encoding: str = "jpg"
    raw: bool = False
    timelapse: Optional[int] = None
    immediate: bool = False

    # Video-specific
    framerate: Optional[float] = None
    bitrate: Optional[int] = None
    codec: str = "h264"
    profile: str = ""
    level: str = ""
    intra: Optional[int] = None
    segment: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def copy(self) -> "Settings":
        return Settings.from_dict(self.to_dict())


def switch_mode(settings: Settings, mode: str) -> Settings:
    """Return a copy of settings with mode switched, preserving shared fields.

    If the output path still looks like an auto-generated default for the old
    mode, regenerate one with the correct extension for the new mode.
    """
    new_settings = settings.copy()
    old_mode = new_settings.mode
    if old_mode == mode:
        return new_settings
    old_default_ext = "jpg" if old_mode == MODE_STILL else "h264"
    if new_settings.output.startswith("capture_") and new_settings.output.endswith(f".{old_default_ext}"):
        new_settings.output = default_output_path(mode)
    new_settings.mode = mode
    return new_settings


def build_command(settings: Settings) -> list[str]:
    """Build the argv list for the given settings. Pure function, no I/O."""
    binary = BINARY[settings.mode]
    argv: list[str] = [binary]

    def add(flag: str, value: Any = None) -> None:
        argv.append(flag)
        if value is not None:
            argv.append(str(value))

    # --- Common / capture ---
    if settings.camera:
        add("--camera", settings.camera)
    if settings.width:
        add("--width", settings.width)
    if settings.height:
        add("--height", settings.height)
    if settings.timeout is not None:
        add("--timeout", settings.timeout)
    if settings.output:
        add("--output", settings.output)
    if settings.nopreview:
        add("--nopreview")
    if settings.verbose:
        add("--verbose")

    # --- Autofocus ---
    if settings.af_mode:
        add("--autofocus-mode", settings.af_mode)
    if settings.af_range and settings.af_range != "normal":
        add("--autofocus-range", settings.af_range)
    if settings.af_speed and settings.af_speed != "normal":
        add("--autofocus-speed", settings.af_speed)
    if settings.af_mode == "manual" and settings.lens_position is not None:
        add("--lens-position", settings.lens_position)
    if settings.af_window:
        add("--autofocus-window", settings.af_window)

    # --- Exposure ---
    if settings.shutter is not None:
        add("--shutter", settings.shutter)
    if settings.gain is not None:
        add("--gain", settings.gain)
    if settings.ev is not None:
        add("--ev", settings.ev)
    if settings.metering and settings.metering != "centre":
        add("--metering", settings.metering)
    if settings.exposure and settings.exposure != "normal":
        add("--exposure", settings.exposure)

    # --- White balance / color ---
    if settings.awb:
        add("--awb", settings.awb)
    if settings.awb == "custom" and settings.awb_gains:
        add("--awbgains", settings.awb_gains)
    if settings.saturation is not None:
        add("--saturation", settings.saturation)
    if settings.contrast is not None:
        add("--contrast", settings.contrast)
    if settings.sharpness is not None:
        add("--sharpness", settings.sharpness)
    if settings.brightness is not None:
        add("--brightness", settings.brightness)
    if settings.denoise and settings.denoise != "auto":
        add("--denoise", settings.denoise)
    if settings.hdr and settings.hdr != "off":
        add("--hdr", settings.hdr)

    # --- Mode-specific ---
    if settings.mode == MODE_STILL:
        if settings.quality is not None:
            add("--quality", settings.quality)
        if settings.encoding:
            add("--encoding", settings.encoding)
        if settings.raw:
            add("--raw")
        if settings.timelapse:
            add("--timelapse", settings.timelapse)
        if settings.immediate:
            add("--immediate")
    else:
        if settings.framerate is not None:
            add("--framerate", settings.framerate)
        if settings.bitrate is not None:
            add("--bitrate", settings.bitrate)
        if settings.codec:
            add("--codec", settings.codec)
        if settings.profile:
            add("--profile", settings.profile)
        if settings.level:
            add("--level", settings.level)
        if settings.intra is not None:
            add("--intra", settings.intra)
        if settings.segment is not None:
            add("--segment", settings.segment)

    return argv


def command_to_string(argv: list[str]) -> str:
    """Render an argv list as a copy-pasteable shell command string."""
    return shlex.join(argv)
