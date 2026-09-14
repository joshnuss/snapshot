# Snapshot

Record screen, webcam and mic with a CLI.

## Features

- Based on `ffmpeg`.
- CLI-based, no GUI.
- Easy to script.
- Easy to add to launchers or bind to hot keys.
- CTRL+C to save recordings.

## Usage

```bash
snapshot --help
snapshot my-recording.mp4
```

Just hit `CTRL+C` to end recording and save the video.

## Customizing

Many options are customizable.

For example, you can choose the monitor, camera, mic


```bash
snapshot --monitor DP-1 \
  --camera /dev/video0 \
  --position right \
  --fps 15
```

## License

MIT
