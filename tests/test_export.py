"""Integration checks with synthetic capture inputs; never opens capture devices."""
import os
import json
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class ExportTest(unittest.TestCase):
    def test_common_start_trim(self):
        with tempfile.TemporaryDirectory(prefix='snapshot-trim-test-') as directory:
            media = Path(directory) / 'delayed.mkv'
            project = Path(directory) / 'delayed.kdenlive'
            subprocess.run(['ffmpeg', '-v', 'error',
                '-f', 'lavfi', '-i', 'color=blue:s=1280x720:r=15',
                '-itsoffset', '0.5', '-f', 'lavfi', '-i', 'color=red:s=640x480:r=15',
                '-itsoffset', '0.2', '-f', 'lavfi', '-i', 'sine=frequency=440',
                '-map', '0:v', '-map', '1:v', '-map', '2:a', '-t', '1',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-fps_mode:v', 'passthrough',
                '-c:a', 'aac', str(media)], check=True)
            probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error',
                '-show_streams', '-of', 'json', str(media)]))
            expected = math.ceil(max(float(s['start_time']) for s in probe['streams']) * 15 - 1e-9)
            subprocess.run(['python3', str(ROOT/'kdenlive.py'), str(media), str(project),
                '--fps', '15', '--size', '300', '--margin', '24', '--position', 'center'], check=True)
            tree = ET.parse(project)
            for name, stream in zip(('screen', 'webcam', 'mic'), probe['streams']):
                playlist = tree.find(f"./playlist[@id='{name}_clips']")
                offset = 0 if name == 'mic' else math.floor(float(stream['start_time']) * 15 + 0.5)
                self.assertEqual(int(playlist.find('entry').get('in')), expected - offset)
                self.assertIsNone(playlist.find('blank'))
            entries = [tree.find(f"./playlist[@id='{name}_clips']/entry")
                       for name in ('screen', 'webcam', 'mic')]
            self.assertEqual(len({int(e.get('out')) - int(e.get('in')) for e in entries}), 1)
            groups = json.loads(tree.find(
                "./tractor[@id='sequence']/property[@name='kdenlive:sequenceproperties.groups']").text)
            self.assertEqual([child['data'] for child in groups[0]['children']],
                             ['0:0:-1', '1:0:-1', '2:0:-1'])
            self.assertGreater(expected, 0)

    def test_recording_modes(self):
        with tempfile.TemporaryDirectory(prefix='snapshot-export-test-') as directory:
            base = Path(directory)
            bins = base / 'bin'
            bins.mkdir()
            (bins / 'xrandr').write_text('#!/bin/sh\necho "HDMI-1 connected primary 1280x720+0+0"\n')
            (bins / 'pactl').write_text('''#!/bin/sh
if [ "$1" = get-default-sink ]; then
    echo test-output
fi
''')
            # Preserve the output mapping/encoding from the actual CLI, replacing
            # only hardware capture with a short, deterministic source.
            (bins / 'ffmpeg').write_text('''#!/usr/bin/env python3
import os, sys
args=sys.argv[1:]
if 'x11grab' in args:
    tail=args[args.index('-filter_complex_threads'):] if '-filter_complex_threads' in args else args[args.index('-map'):]
    args=['-hide_banner','-nostdin','-n','-f','lavfi','-i','color=blue:s=1280x720:r=15',
          '-f','lavfi','-i','testsrc2=s=640x480:r=15','-f','lavfi','-i','sine=frequency=440']
    if any('3:a' in value for value in args + tail):
        args += ['-f','lavfi','-i','sine=frequency=880']
    args += tail[:-1]+['-t','1',tail[-1]]
os.execv('/usr/bin/ffmpeg',['ffmpeg']+args)
''')
            for path in bins.iterdir():
                path.chmod(0o755)
            env = {**os.environ, 'PATH': str(bins)+':'+os.environ['PATH'],
                   'DISPLAY': ':0', 'XDG_SESSION_TYPE': 'x11'}
            for mode in ('mp4', 'kdenlive'):
                output = base / f'recording.{mode}'
                if mode == 'kdenlive':
                    # MP4 mode retains the same stem's MKV; use another name.
                    output = base / 'editable.kdenlive'
                command = [str(ROOT/'snapshot'), '--no-tray', '--export', mode,
                    '--camera', '/dev/zero', '--mic', 'test', '--fps', '15']
                run = subprocess.run(command + [str(output)],
                    env=env, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIn('System audio source: test-output.monitor', run.stdout)
                self.assertTrue(output.is_file())
                if mode == 'kdenlive':
                    tree = ET.parse(output)
                    self.assertEqual(tree.find('profile').get('description'), 'Snapshot 1280x720 15 fps')
                    self.assertEqual(len(tree.findall('./chain')), 4)
                    self.assertEqual(tree.find("./chain[@id='webcam']/property[@name='vstream']").text, '1')
                    self.assertEqual(tree.find("./chain[@id='mic']/property[@name='astream']").text, '0')
                    self.assertEqual(tree.find("./chain[@id='system_audio']/property[@name='astream']").text, '1')
                    self.assertEqual(tree.find("./tractor[@id='system_audio_track']/property[@name='kdenlive:track_name']").text,
                                     'System Audio')
                    groups = json.loads(tree.find(
                        "./tractor[@id='sequence']/property[@name='kdenlive:sequenceproperties.groups']").text)
                    self.assertEqual(groups, [{
                        'type': 'Normal',
                        'children': [
                            {'type': 'Leaf', 'leaf': 'clip', 'data': f'{track}:0:-1'}
                            for track in range(4)
                        ],
                    }])
                    self.assertEqual(len(tree.findall('./tractor[@id="webcam_track"]')), 1)
                    effects = tree.findall('.//filter/property[@name="mlt_service"]')
                    self.assertEqual([e.text for e in effects], ['avfilter.hflip', 'frei0r.alphaspot', 'qtblend'])
                    self.assertTrue(all(p.text=='editable.mkv' for p in tree.findall('./chain/property[@name="resource"]')))
                    retry = subprocess.run([str(ROOT/'snapshot'), '--export', mode, str(output)],
                                           env=env, capture_output=True, text=True)
                    self.assertNotEqual(retry.returncode, 0)
                    self.assertIn('already exists', retry.stderr)


if __name__ == '__main__':
    unittest.main()
