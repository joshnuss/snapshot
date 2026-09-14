# Snapshot

Record your screen, webcam and mic with a CLI.

## Features

- Based on `ffmpeg`.
- CLI-based, no GUI.
- Easy to script.
- Easy to add to launchers or bind to hot keys.
- CTRL+C to save recordings.

## Usage

```bash
# get help
snapshot --help

# record to a specific file
snapshot my-recording.mp4

# optional: choose the monitor, camera, mic, etc..
snapshot --monitor DP-1 \
  --camera /dev/video0 \
  --position right \
  --fps 15
```

Press <kbd>Ctrl</kbd> + <kbd>C</kbd> to stop recording and export the MP4.

## Options

| Option | Default | Explanation |
|---|---|---|
| <code>--monitor&nbsp;NAME</code> | Primary monitor | Select the screen to record, such as `HDMI-1`. |
| <code>--camera&nbsp;DEVICE</code> | `/dev/video0` | Select the webcam device. |
| <code>--mic&nbsp;SOURCE</code> | `default` | Select the PulseAudio/PipeWire audio source. |
| <code>--camera-size&nbsp;WxH</code> | `640x480` | Webcam capture resolution; must be supported by the camera. |
| <code>--camera-fps&nbsp;N</code> | `30` | Webcam frame rate; must be supported by the camera. |
| <code>--camera-format&nbsp;FMT</code> | Device default | Webcam input format, such as `mjpeg` or `yuyv422`. |
| <code>--fps&nbsp;N</code> | `30` | Screen capture and output frame rate. |
| <code>--size&nbsp;N</code> | `600` | Webcam circle diameter in pixels. |
| <code>--margin&nbsp;N</code> | `24` | Gap from the bottom and applicable side edge, in pixels. |
| <code>--position&nbsp;POSITION</code> | `right` | Place the circle at bottom `left`, `center`, or `right`. |
| <code>--no-mirror</code> | Mirroring enabled | Disable horizontal webcam mirroring. |
| <code>--list</code> | — | List monitors, cameras, and audio sources, then exit. |
| <code>--demo</code> | — | Generate a three-second synthetic recording without accessing devices. |
| <code>--dry-run</code> | — | Print FFmpeg commands without recording; live device checks still run. |
| <code>-h</code>,&nbsp;<code>--help</code> | — | Show usage and exit. |
| <code>output.mp4</code> | `recording-YYYYmmdd-HHMMSS.mp4` | Optional output filename; must end in `.mp4`. Existing recordings aren’t overwritten. |

## License

MIT
