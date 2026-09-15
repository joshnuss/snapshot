# Snapshot

Record your screen, webcam and mic with a CLI.

## Features

- Developer friendly workflow.
- CLI-based, no GUI.
- Fully scriptable.
- Add to launchers or bind to hot keys.
- <kbd>Ctrl</kbd> + <kbd>C</kbd> to save recordings.
- Displays a system tray icon when running.
- Based on `ffmpeg`.

## Usage

```bash
# get help
snapshot --help

# record to a specific file
snapshot my-recording.mp4

# optional: choose the monitor, camera, mic, etc..
snapshot --monitor HDMI-1 \
  --camera /dev/video0 \
  --overlay-position bottom-right \
  --fps 15

# list available devices
snapshot --devices
```

Press <kbd>Ctrl</kbd> + <kbd>C</kbd> to stop recording and export the MP4.

## Options

The cli accepts this parameters:

| Option                | Default                         | Explanation                                                                           |
|-----------------------|---------------------------------|---------------------------------------------------------------------------------------|
| `--monitor NAME`      | Primary monitor                 | Select the screen to record, such as `HDMI-1`.                                        |
| `--camera DEVICE`     | `/dev/video0`                   | Select the webcam device.                                                             |
| `--mic SOURCE`        | `default`                       | Select the PulseAudio/PipeWire audio source.                                          |
| `--camera-size WxH`   | `640x480`                       | Webcam capture resolution; must be supported by the camera.                           |
| `--camera-fps N`      | `30`                            | Webcam frame rate; must be supported by the camera.                                   |
| `--camera-format FMT` | Device default                  | Webcam input format, such as `mjpeg` or `yuyv422`.                                    |
| `--fps N`             | `30`                            | Screen capture and output frame rate.                                                 |
| `--overlay-size N`            | `600`                           | Webcam circle diameter in pixels.                                                     |
| `--overlay-margin N`          | `24`                            | Gap from the selected edges, in pixels; centered axes ignore it.                              |
| `--overlay-position POSITION` | `bottom-right` | `top-left`, `top-center`, `top-right`, `center-left`, `center`, `center-right`, `bottom-left`, `bottom-center`, or `bottom-right`. |
| `--no-tray`           | Tray enabled                    | Disable the recording tray icon.                                                      |
| `--no-mirror`         | Mirroring enabled               | Disable horizontal webcam mirroring.                                                  |
| `--devices`           | —                               | List available monitors, cameras, and audio sources.                                  |
| `--demo`              | —                               | Generate a three-second synthetic recording without accessing devices.                |
| `--dry-run`           | —                               | Print FFmpeg commands without recording; live device checks still run.                |
| `-h`, `--help`        | —                               | Show help                                                                             |
| `output.mp4`          | `recording-YYYYmmdd-HHMMSS.mp4` | Optional output filename; must end in `.mp4`. Existing recordings aren’t overwritten. |

## License

MIT
