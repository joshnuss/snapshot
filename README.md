# Snapshot

Record your screen, webcam and mic with a CLI.

## Features

- Developer friendly workflow.
- CLI-based, no GUI.
- Fully scriptable.
- Add to launchers or bind to hot keys.
- <kbd>Ctrl</kbd> + <kbd>C</kbd> to save recordings.
- Displays a system tray icon when running.
- Exports to mp4 or kdenlive.
- Based on `ffmpeg`.

## Usage

```bash
# get help
snapshot --help

# record to a specific file
snapshot ~/Recordings/screencast.mp4

# record to a specific folder (generated name recording-YYYYMMDD-HHMMSS.mp4)
snapshot ~/Recordings

# record and create a kednlive project
snapshot --export kdenlive

# optional: choose the monitor, camera, mic, etc..
snapshot --monitor HDMI-1 \
  --camera /dev/video0 \
  --overlay-position bottom-right \
  --fps 15

# list available devices
snapshot --devices
```

Press <kbd>Ctrl</kbd> + <kbd>C</kbd> to stop recording and save the output.

## Options

The cli accepts this parameters:

| Option                         | Default                         | Explanation                                                                                                                                                                           |
|--------------------------------|---------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--export FORMAT` | `mp4` | Export a combined `mp4` or an editable `kdenlive` project with multistream MKV media. |
| `--monitor NAME`               | Primary monitor                 | Select the screen to record, such as `HDMI-1`.                                                                                                                                        |
| `--camera DEVICE`              | `/dev/video0`                   | Select the webcam device.                                                                                                                                                             |
| `--mic SOURCE`                 | `default`                       | Select the PulseAudio/PipeWire audio source.                                                                                                                                          |
| `--system-audio SOURCE`        | `default`                       | Capture a system-output monitor source. `default` selects the default output.                                                                                                         |
| `--camera-size WxH`            | `640x480`                       | Webcam capture resolution; must be supported by the camera.                                                                                                                           |
| `--camera-fps N`               | `30`                            | Webcam frame rate; must be supported by the camera.                                                                                                                                   |
| `--camera-format FMT`          | Device default                  | Webcam input format, such as `mjpeg` or `yuyv422`.                                                                                                                                    |
| `--fps N`                      | `30`                            | Screen capture and output frame rate.                                                                                                                                                 |
| `--overlay-size N`             | `600`                           | Webcam circle diameter in pixels.                                                                                                                                                     |
| `--overlay-margin N`           | `24`                            | Gap from the selected edges, in pixels; centered axes ignore it.                                                                                                                      |
| `--overlay-position POSITION`  | `bottom-right`                  | `top-left`, `top-center`, `top-right`, `center-left`, `center`, `center-right`, `bottom-left`, `bottom-center`, or `bottom-right`.                                                    |
| `--no-tray`                    | Tray enabled                    | Disable the recording tray icon.                                                                                                                                                      |
| `--no-mirror`                  | Mirroring enabled               | Disable horizontal webcam mirroring.                                                                                                                                                  |
| `--no-system-audio`            | System audio enabled            | Disable system-audio recording.                                                                                                                                                       |
| `--devices`                    | —                               | List available monitors, cameras, and audio sources.                                                                                                                                  |
| `--dry-run`                    | —                               | Print FFmpeg commands without recording; live device checks still run.                                                                                                                |
| `-h`, `--help`                 | —                               | Show help                                                                                                                                                                             |
| `output.mp4` or `path/to/dir`  | `recording-YYYYmmdd-HHMMSS.mp4` | a filename or directory path                                                                                                                                                          |
## Install

First, install dependencies

```bash
sudo apt install ffmpeg x11-xserver-utils pulseaudio-utils
```

Then, download `snapshot-linux-x86_64.tar.gz` from the [GitHub Releases](https://github.com/joshnuss/snapshot/releases).

```bash
sha256sum -c SHA256SUMS
tar -xzf snapshot-linux-x86_64.tar.gz
./snapshot-linux-x86_64/snapshot --help
```

## License

MIT
