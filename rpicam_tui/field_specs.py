"""Declarative schema describing every form field: which Settings attribute it
maps to, its CLI flag, help text, and its control kind. Drives both form
construction and form <-> Settings syncing in app.py, so the two never drift.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .command_builder import (
    AF_MODES,
    AF_RANGES,
    AF_SPEEDS,
    AWB_MODES,
    CODECS,
    DENOISE_MODES,
    ENCODINGS,
    EXPOSURE_MODES,
    HDR_MODES,
    METERING_MODES,
    MODE_STILL,
    MODE_VIDEO,
)

KIND_INT = "int"
KIND_FLOAT = "float"
KIND_STR = "str"
KIND_BOOL = "bool"
KIND_SELECT = "select"


@dataclass
class FieldSpec:
    name: str
    flag: str
    help: str
    kind: str
    options: Optional[list[str]] = None
    modes: tuple[str, ...] = (MODE_STILL, MODE_VIDEO)
    optional: bool = False


@dataclass
class Group:
    title: str
    fields: list[FieldSpec] = field(default_factory=list)
    collapsed: bool = False
    modes: tuple[str, ...] = (MODE_STILL, MODE_VIDEO)


GROUPS: list[Group] = [
    Group(
        title="Common / capture",
        fields=[
            FieldSpec("camera", "--camera", "Camera index, for multi-camera boards", KIND_INT),
            FieldSpec("width", "--width", "Output image/video width in pixels", KIND_INT),
            FieldSpec("height", "--height", "Output image/video height in pixels", KIND_INT),
            FieldSpec("timeout", "--timeout / -t", "How long to run before exiting, in ms (0 = run until stopped)", KIND_INT),
            FieldSpec("output", "--output / -o", "Output file path (timestamped default)", KIND_STR),
            FieldSpec("nopreview", "--nopreview / -n", "Disable the preview window (recommended headless)", KIND_BOOL),
            FieldSpec("verbose", "--verbose / -v", "Print extra diagnostic information", KIND_BOOL),
        ],
    ),
    Group(
        title="Resolution presets",
        fields=[
            FieldSpec(
                "resolution_preset",
                "(preset)",
                "Quick-fill width/height; pick 'custom' to type your own above",
                KIND_SELECT,
                options=["custom", "4608x2592 (full)", "1920x1080", "1280x720"],
            ),
        ],
    ),
    Group(
        title="Autofocus (Camera Module 3)",
        fields=[
            FieldSpec("af_mode", "--autofocus-mode", "auto = focus once, continuous = keep hunting, manual = fixed lens position", KIND_SELECT, options=AF_MODES),
            FieldSpec("af_range", "--autofocus-range", "Distance range the AF algorithm searches over", KIND_SELECT, options=AF_RANGES),
            FieldSpec("af_speed", "--autofocus-speed", "How quickly the lens is allowed to rack focus", KIND_SELECT, options=AF_SPEEDS),
            FieldSpec("lens_position", "--lens-position", "Manual focus distance as 1/distance_m (0.1 = 10m, 10 = 10cm); only used when mode=manual", KIND_FLOAT),
            FieldSpec("af_window", "--autofocus-window", "Restrict AF to a region: x,y,w,h as fractions of the frame (optional)", KIND_STR),
        ],
    ),
    Group(
        title="Exposure",
        fields=[
            FieldSpec("shutter", "--shutter", "Fixed shutter speed in microseconds (blank = auto)", KIND_INT, optional=True),
            FieldSpec("gain", "--gain", "Analogue gain / ISO-like multiplier (blank = auto)", KIND_FLOAT),
            FieldSpec("ev", "--ev", "Exposure compensation in stops, e.g. -1.0 or 0.5", KIND_FLOAT),
            FieldSpec("metering", "--metering", "Which part of the frame is used to judge exposure", KIND_SELECT, options=METERING_MODES),
            FieldSpec("exposure", "--exposure", "Exposure profile: sport favours shutter speed, long favours low light", KIND_SELECT, options=EXPOSURE_MODES),
        ],
    ),
    Group(
        title="White balance / color",
        fields=[
            FieldSpec("awb", "--awb", "Auto white balance mode, or 'custom' to set explicit r/b gains", KIND_SELECT, options=AWB_MODES),
            FieldSpec("awb_gains", "--awbgains", "Manual red,blue gain pair e.g. 1.5,1.2; only used when awb=custom", KIND_STR),
            FieldSpec("saturation", "--saturation", "Colour saturation, 0.0-... (1.0 = normal)", KIND_FLOAT),
            FieldSpec("contrast", "--contrast", "Image contrast, 0.0-... (1.0 = normal)", KIND_FLOAT),
            FieldSpec("sharpness", "--sharpness", "Image sharpness, 0.0-... (1.0 = normal)", KIND_FLOAT),
            FieldSpec("brightness", "--brightness", "Image brightness, -1.0 to 1.0 (0.0 = normal)", KIND_FLOAT),
            FieldSpec("denoise", "--denoise", "Noise reduction mode", KIND_SELECT, options=DENOISE_MODES),
            FieldSpec("hdr", "--hdr", "HDR mode; Module 3 supports in-sensor HDR", KIND_SELECT, options=HDR_MODES),
        ],
    ),
    Group(
        title="Still-specific",
        modes=(MODE_STILL,),
        fields=[
            FieldSpec("quality", "--quality / -q", "JPEG quality, 0-100", KIND_INT, modes=(MODE_STILL,)),
            FieldSpec("encoding", "--encoding / -e", "Output file encoding", KIND_SELECT, options=ENCODINGS, modes=(MODE_STILL,)),
            FieldSpec("raw", "--raw / -r", "Also save a raw Bayer file alongside the image", KIND_BOOL, modes=(MODE_STILL,)),
            FieldSpec("timelapse", "--timelapse", "Repeat capture every N ms instead of a single shot (blank = single shot)", KIND_INT, modes=(MODE_STILL,), optional=True),
            FieldSpec("immediate", "--immediate", "Capture immediately, skipping the AF/AE/AWB settling period", KIND_BOOL, modes=(MODE_STILL,)),
        ],
    ),
    Group(
        title="Video-specific",
        modes=(MODE_VIDEO,),
        fields=[
            FieldSpec("framerate", "--framerate", "Capture frame rate in fps (blank = sensor default)", KIND_FLOAT, modes=(MODE_VIDEO,)),
            FieldSpec("bitrate", "--bitrate / -b", "Target encoder bitrate in bits/sec, e.g. 5000000 for 5 Mbps", KIND_INT, modes=(MODE_VIDEO,), optional=True),
            FieldSpec("codec", "--codec", "Video codec/container", KIND_SELECT, options=CODECS, modes=(MODE_VIDEO,)),
            FieldSpec("profile", "--profile", "H.264 profile, e.g. baseline, main, high (blank = default)", KIND_STR, modes=(MODE_VIDEO,)),
            FieldSpec("level", "--level", "H.264 level, e.g. 4.2 (blank = default)", KIND_STR, modes=(MODE_VIDEO,)),
            FieldSpec("intra", "--intra / -g", "Keyframe interval in frames (blank = codec default)", KIND_INT, modes=(MODE_VIDEO,), optional=True),
            FieldSpec("segment", "--segment", "Split output into chunks of N ms each (blank = single file)", KIND_INT, modes=(MODE_VIDEO,), optional=True),
        ],
    ),
]


def all_field_specs() -> list[FieldSpec]:
    return [f for group in GROUPS for f in group.fields]
