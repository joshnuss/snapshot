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
| <span style="white-space: nowrap;"><code>--monitor&nbsp;NAME</code></span> | Primary monitor | Select the screen to record, such as `HDMI-1`. |
| <span style="white-space: nowrap;"><code>--camera&nbsp;DEVICE</code></span> | `/dev/video0` | Select the webcam device. |
| <span style="white-space: nowrap;"><code>--mic&nbsp;SOURCE</code></span> | `default` | Select the PulseAudio/PipeWire audio source. |
| <span style="white-space: nowrap;"><code>--camera-size&nbsp;WxH</code></span> | `640x480` | Webcam capture resolution; must be supported by the camera. |
| <span style="white-space: nowrap;"><code>--camera-fps&nbsp;N</code></span> | `30` | Webcam frame rate; must be supported by the camera. |
| <span style="white-space: nowrap;"><code>--camera-format&nbsp;FMT</code></span> | Device default | Webcam input format, such as `mjpeg` or `yuyv422`. |
| <span style="white-space: nowrap;"><code>--fps&nbsp;N</code></span> | `30` | Screen capture and output frame rate. |
| <span style="white-space: nowrap;"><code>--size&nbsp;N</code></span> | `600` | Webcam circle diameter in pixels. |
| <span style="white-space: nowrap;"><code>--margin&nbsp;N</code></span> | `24` | Gap from the bottom and applicable side edge, in pixels. |
| <span style="white-space: nowrap;"><code>--position&nbsp;POSITION</code></span> | `right` | Place the circle at bottom `left`, `center`, or `right`. |
| <span style="white-space: nowrap;"><code>--no-mirror</code></span> | Mirroring enabled | Disable horizontal webcam mirroring. |
| <span style="white-space: nowrap;"><code>--list</code></span> | — | List monitors, cameras, and audio sources, then exit. |
| <span style="white-space: nowrap;"><code>--demo</code></span> | — | Generate a three-second synthetic recording without accessing devices. |
| <span style="white-space: nowrap;"><code>--dry-run</code></span> | — | Print FFmpeg commands without recording; live device checks still run. |
| <span style="white-space: nowrap;"><code>-h</code>,&nbsp;<code>--help</code></span> | — | Show usage and exit. |
| <span style="white-space: nowrap;"><code>output.mp4</code></span> | `recording-YYYYmmdd-HHMMSS.mp4` | Optional output filename; must end in `.mp4`. Existing recordings aren’t overwritten. |

## License

MIT
