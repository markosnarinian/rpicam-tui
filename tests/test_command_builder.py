from rpicam_tui.command_builder import (
    MODE_STILL,
    MODE_VIDEO,
    Settings,
    build_command,
    command_to_string,
    default_output_path,
    switch_mode,
)


def test_still_defaults_produce_expected_flags():
    settings = Settings(mode=MODE_STILL, output="out.jpg")
    argv = build_command(settings)
    assert argv[0] == "rpicam-still"
    assert "--width" in argv and argv[argv.index("--width") + 1] == "1920"
    assert "--height" in argv and argv[argv.index("--height") + 1] == "1080"
    assert "--output" in argv and argv[argv.index("--output") + 1] == "out.jpg"
    assert "--nopreview" in argv
    assert "--autofocus-mode" in argv and argv[argv.index("--autofocus-mode") + 1] == "continuous"
    assert "--quality" in argv and argv[argv.index("--quality") + 1] == "93"
    # video-only flags must not leak into still mode
    assert "--bitrate" not in argv
    assert "--codec" not in argv


def test_video_defaults_produce_expected_flags():
    settings = Settings(mode=MODE_VIDEO, output="out.h264", bitrate=5_000_000, framerate=30)
    argv = build_command(settings)
    assert argv[0] == "rpicam-vid"
    assert "--bitrate" in argv and argv[argv.index("--bitrate") + 1] == "5000000"
    assert "--framerate" in argv and argv[argv.index("--framerate") + 1] == "30"
    assert "--codec" in argv and argv[argv.index("--codec") + 1] == "h264"
    # still-only flags must not leak into video mode
    assert "--quality" not in argv
    assert "--encoding" not in argv


def test_camera_index_zero_is_omitted_but_nonzero_included():
    argv0 = build_command(Settings(camera=0))
    assert "--camera" not in argv0

    argv1 = build_command(Settings(camera=1))
    assert "--camera" in argv1
    assert argv1[argv1.index("--camera") + 1] == "1"


def test_lens_position_only_added_in_manual_af_mode():
    manual = Settings(af_mode="manual", lens_position=0.1)
    argv = build_command(manual)
    assert "--lens-position" in argv
    assert argv[argv.index("--lens-position") + 1] == "0.1"

    auto = Settings(af_mode="auto", lens_position=0.1)
    argv_auto = build_command(auto)
    assert "--lens-position" not in argv_auto


def test_awb_gains_only_added_when_awb_is_custom():
    custom = Settings(awb="custom", awb_gains="1.5,1.2")
    argv = build_command(custom)
    assert "--awbgains" in argv
    assert argv[argv.index("--awbgains") + 1] == "1.5,1.2"

    auto = Settings(awb="auto", awb_gains="1.5,1.2")
    argv_auto = build_command(auto)
    assert "--awbgains" not in argv_auto


def test_default_values_omit_optional_flags():
    settings = Settings()
    argv = build_command(settings)
    for flag in ("--shutter", "--gain", "--ev", "--saturation", "--contrast", "--sharpness", "--brightness"):
        assert flag not in argv


def test_vehicle_mount_style_settings_build_expected_command():
    settings = Settings(
        mode=MODE_VIDEO,
        af_mode="manual",
        lens_position=0.1,
        shutter=8000,
        bitrate=10_000_000,
        output="vehicle.h264",
    )
    argv = build_command(settings)
    assert "--lens-position" in argv and argv[argv.index("--lens-position") + 1] == "0.1"
    assert "--shutter" in argv and argv[argv.index("--shutter") + 1] == "8000"
    assert "--bitrate" in argv and argv[argv.index("--bitrate") + 1] == "10000000"


def test_switch_mode_preserves_shared_settings():
    still = Settings(mode=MODE_STILL, shutter=8000, awb="cloudy", output="capture_still.jpg")
    video = switch_mode(still, MODE_VIDEO)
    assert video.mode == MODE_VIDEO
    assert video.shutter == 8000
    assert video.awb == "cloudy"
    # auto-generated default output path gets a new extension for the new mode
    assert video.output.endswith(".h264")


def test_switch_mode_preserves_custom_output_path():
    still = Settings(mode=MODE_STILL, output="my_custom_name.jpg")
    video = switch_mode(still, MODE_VIDEO)
    assert video.output == "my_custom_name.jpg"


def test_command_to_string_is_shell_safe_and_quotes_spaces():
    settings = Settings(output="my photo.jpg")
    argv = build_command(settings)
    cmd = command_to_string(argv)
    assert "'my photo.jpg'" in cmd or '"my photo.jpg"' in cmd


def test_default_output_path_extension_matches_mode():
    assert default_output_path(MODE_STILL).endswith(".jpg")
    assert default_output_path(MODE_VIDEO).endswith(".h264")
