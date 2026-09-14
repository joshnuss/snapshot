# Snapshot

A screen recorder and webcam capture CLI base on `ffmpeg`.

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
