"""CLI and process-lifecycle checks without physical recording devices."""
import os
from pathlib import Path
import shlex
import signal
import subprocess
import tempfile
import time
import unittest

from linux_capture import monitors
from cli import parser, output_paths

ROOT = Path(os.environ.get('SNAPSHOT_TEST_ROOT', Path(__file__).resolve().parents[1]))


class RecorderTest(unittest.TestCase):
    def test_monitor_geometry(self):
        screens = monitors('''DP-1 connected primary 1920x1080+0+0 normal
HDMI-1 connected 1280x720-1280+100 normal
DP-2 disconnected
''')
        self.assertEqual([(s.name, s.x, s.y, s.primary) for s in screens],
                         [('DP-1', 0, 0, True), ('HDMI-1', -1280, 100, False)])

    def test_audio_option_order(self):
        self.assertEqual(parser().parse_args(['--no-system-audio']).system_audio, '')
        self.assertEqual(parser().parse_args(['--no-system-audio', '--system-audio', 'custom']).system_audio, 'custom')

    def test_output_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            output, media, log = output_paths(str(base / 'clip.mkv'), 'mp4')
            self.assertEqual(media, base / 'clip.mkv.mkv')
            generated, _, _ = output_paths(directory, 'kdenlive')
            self.assertEqual(generated.parent, base)
            self.assertEqual(generated.suffix, '.kdenlive')
            media.touch()
            with self.assertRaisesRegex(ValueError, 'already exists'):
                output_paths(str(output), 'mp4')

    def make_environment(self, base, ffmpeg):
        bins = base / 'bin'
        bins.mkdir()
        (bins / 'xrandr').write_text('#!/bin/sh\necho "HDMI-1 connected primary 1280x720+0+0"\n')
        (bins / 'ffmpeg').write_text(ffmpeg)
        for file in bins.iterdir():
            file.chmod(0o755)
        return {**os.environ, 'PATH': str(bins) + ':' + os.environ['PATH'],
                'DISPLAY': ':9876', 'XDG_SESSION_TYPE': 'x11', 'WAYLAND_DISPLAY': ''}

    def command(self, output):
        return [str(ROOT / 'snapshot'), '--no-tray', '--no-system-audio',
                '--camera', '/dev/zero', '--mic', 'test', str(output)]

    def test_dry_run_preserves_input_options_and_does_not_record(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            env = self.make_environment(base, '#!/bin/sh\nexit 99\n')
            output = base / 'folder with spaces' / 'clip.mp4'
            run = subprocess.run(self.command(output) + ['--dry-run', '--no-mirror',
                                 '--overlay-position', 'top-center', '--camera-format', 'mjpeg'],
                                 env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            capture, export = [shlex.split(line) for line in run.stdout.splitlines() if line.startswith('ffmpeg ')]
            self.assertEqual(capture[capture.index('-input_format') + 1], 'mjpeg')
            graph = capture[capture.index('-filter_complex') + 1]
            self.assertIn('overlay=x=(W-w)/2:y=24', graph)
            self.assertNotIn('hflip', graph)
            self.assertNotIn('amix', graph)
            self.assertEqual(export[-1], str(output))
            self.assertFalse(output.parent.exists())

    def test_failed_capture_retains_media_and_log_without_export(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            env = self.make_environment(base, '''#!/usr/bin/env python3
import pathlib, sys
pathlib.Path(sys.argv[-1]).write_bytes(b'partial media')
print('capture diagnostic', file=sys.stderr)
sys.exit(7)
''')
            output = base / 'clip.mp4'
            run = subprocess.run(self.command(output), env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 1)
            self.assertIn('Capture failed (exit 7)', run.stderr)
            self.assertFalse(output.exists())
            self.assertEqual(output.with_suffix('.mkv').read_bytes(), b'partial media')
            self.assertIn('capture diagnostic', output.with_suffix('.capture.log').read_text())

    def test_export_failure_retains_media(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            env = self.make_environment(base, '''#!/usr/bin/env python3
import pathlib, sys
if 'x11grab' in sys.argv:
    pathlib.Path(sys.argv[-1]).write_bytes(b'original media')
else:
    sys.exit(9)
''')
            output = base / 'clip.mp4'
            run = subprocess.run(self.command(output), env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 1)
            self.assertIn('Export failed; your recording remains', run.stderr)
            self.assertEqual(output.with_suffix('.mkv').read_bytes(), b'original media')

    def test_stop_finalizes_and_exports_with_and_without_tray(self):
        # Fake FFmpeg waits for an explicit stop and writes a trailer before exiting.
        # Sending a terminal-group signal checks that the recorder forwards it once.
        for use_tray in (False, True):
            for stop_signal in (signal.SIGINT, signal.SIGTERM):
                with self.subTest(tray=use_tray, signal=stop_signal), tempfile.TemporaryDirectory() as directory:
                    base = Path(directory)
                    env = self.make_environment(base, '''#!/usr/bin/env python3
import pathlib, signal, sys, time
out = pathlib.Path(sys.argv[-1])
if 'x11grab' not in sys.argv:
    out.write_bytes(b'exported')
    sys.exit(0)
def finish(*_):
    out.write_bytes(b'finalized')
    print('finished cleanly', file=sys.stderr)
    sys.exit(255)
signal.signal(signal.SIGINT, finish)
out.with_suffix('.ready').touch()
while True:
    time.sleep(0.02)
''')
                    output = base / 'clip.mp4'
                    command = self.command(output)
                    if use_tray:
                        command.remove('--no-tray')
                    child = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE, text=True, start_new_session=True)
                    try:
                        deadline = time.monotonic() + 15
                        while not output.with_suffix('.ready').exists():
                            if child.poll() is not None or time.monotonic() > deadline:
                                self.fail('capture did not become ready')
                            time.sleep(0.02)
                        os.killpg(child.pid, stop_signal)
                        stdout, stderr = child.communicate(timeout=15)
                        self.assertEqual(child.returncode, 0, stderr)
                        self.assertNotIn('without Ctrl+C', stderr)
                        self.assertIn('Exported:', stdout)
                        self.assertEqual(output.read_bytes(), b'exported')
                        self.assertEqual(output.with_suffix('.mkv').read_bytes(), b'finalized')
                        self.assertIn('finished cleanly', output.with_suffix('.capture.log').read_text())
                    finally:
                        if child.poll() is None:
                            child.kill()
                        child.communicate()
