# Snapshot

Record your screen, webcam and mic with a CLI.

## Features

- Based on `ffmpeg`.
- CLI-based, no GUI.
- Easy to script.
- Easy to add to launchers or bind to hot keys.
- Click the recording tray icon or press Ctrl+C to save recordings.

## Usage

```bash
# get help
snapshot --help

# record to a specific file
snapshot my-recording.mp4

# optional: choose the monitor, camera, mic, etc..
snapshot --monitor HDMI-1 \
  --camera /dev/video0 \
  --position right \
  --fps 15

# list available devices
snapshot --list
```

Press <kbd>Ctrl</kbd> + <kbd>C</kbd> to stop recording and export the MP4.

## Options

The cli accepts this parameters:

| Option | Default | Explanation |
|---|---|---|
| `--monitor NAME` | Primary monitor | Select the screen to record, such as `HDMI-1`. |
| `--camera DEVICE` | `/dev/video0` | Select the webcam device. |
| `--mic SOURCE` | `default` | Select the PulseAudio/PipeWire audio source. |
| `--camera-size WxH` | `640x480` | Webcam capture resolution; must be supported by the camera. |
| `--camera-fps N` | `30` | Webcam frame rate; must be supported by the camera. |
| `--camera-format FMT` | Device default | Webcam input format, such as `mjpeg` or `yuyv422`. |
| `--fps N` | `30` | Screen capture and output frame rate. |
| `--size N` | `600` | Webcam circle diameter in pixels. |
| `--margin N` | `24` | Gap from the bottom and applicable side edge, in pixels. |
| `--position POSITION` | `right` | Place the circle at bottom `left`, `center`, or `right`. |
| `--no-tray` | Tray enabled | Disable the recording tray icon. |
| `--no-mirror` | Mirroring enabled | Disable horizontal webcam mirroring. |
| `--list` | — | List monitors, cameras, and audio sources, then exit. |
| `--demo` | — | Generate a three-second synthetic recording without accessing devices. |
| `--dry-run` | — | Print FFmpeg commands without recording; live device checks still run. |
| `-h`, `--help` | — | Show usage and exit. |
| `output.mp4` | `recording-YYYYmmdd-HHMMSS.mp4` | Optional output filename; must end in `.mp4`. Existing recordings aren’t overwritten. |

## License

MIT
