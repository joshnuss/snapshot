"""Record screen, webcam and audio with FFmpeg; retain media and export on stop."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading

import kdenlive
import linux_capture
from process_env import system_program_env

POSITIONS = ('top-left', 'top-center', 'top-right', 'center-left', 'center',
             'center-right', 'bottom-left', 'bottom-center', 'bottom-right')


def positive(value):
    if not re.fullmatch(r'[1-9][0-9]*', value):
        raise argparse.ArgumentTypeError('must be a positive integer')
    return int(value)


def nonnegative(value):
    if not re.fullmatch(r'0|[1-9][0-9]*', value):
        raise argparse.ArgumentTypeError('must be a nonnegative integer')
    return int(value)


def parser():
    p = argparse.ArgumentParser(prog='snapshot', description=__doc__, allow_abbrev=False)
    p.add_argument('output', nargs='?', help='output file or directory (default: recording-YYYYmmdd-HHMMSS.mp4)')
    p.add_argument('--export', choices=('mp4', 'kdenlive'), default='mp4')
    p.add_argument('--devices', action='store_true', help='list capture devices')
    p.add_argument('--monitor', default='', help='XRandR monitor name (default: primary)')
    p.add_argument('--camera', default='/dev/video0')
    p.add_argument('--mic', default='default')
    p.add_argument('--system-audio', default='default', help='PulseAudio monitor source (default: default output)')
    p.add_argument('--no-system-audio', dest='system_audio', action='store_const', const='')
    p.add_argument('--camera-size', default='640x480')
    p.add_argument('--camera-fps', type=positive, default=30)
    p.add_argument('--camera-format', default='')
    p.add_argument('--fps', type=positive, default=30)
    p.add_argument('--overlay-size', dest='size', type=positive, default=600)
    p.add_argument('--overlay-margin', dest='margin', type=nonnegative, default=24)
    p.add_argument('--overlay-position', dest='position', choices=POSITIONS, default='bottom-right')
    p.add_argument('--no-tray', action='store_true')
    p.add_argument('--no-mirror', action='store_true')
    p.add_argument('--dry-run', action='store_true', help='print commands; still checks live devices')
    return p


def output_paths(output, mode):
    path = Path(output or '.')
    if not output or path.is_dir():
        path /= datetime.now().strftime('recording-%Y%m%d-%H%M%S.') + mode
    path = path.resolve()
    if '.' not in path.name:
        print(f'Warning: output filename has no extension: {path} (writing {mode}).', file=sys.stderr)
    stem = str(path)
    if stem.endswith('.' + mode):
        stem = stem[:-len(mode)-1]
    media = Path(stem + '.mkv')
    if media == path:
        media = Path(str(path) + '.source.mkv')
    if path.exists() or media.exists():
        raise ValueError('Output or intermediate MKV already exists; choose another filename.')
    return path, media, Path(stem + '.capture.log')


def capture_command(args, inputs, media, system_audio):
    command = ['ffmpeg', '-hide_banner', '-nostdin', '-n', '-copyts', '-start_at_zero'] + inputs
    if args.export == 'kdenlive':
        command += ['-map', '0:v:0', '-map', '1:v:0', '-map', '2:a:0']
        if system_audio:
            command += ['-map', '3:a:0']
        command += ['-filter:v:0', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
                    '-filter:v:1', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency',
                    '-crf', '20', '-pix_fmt', 'yuv420p', '-fps_mode:v', 'passthrough',
                    '-c:a', 'aac', '-b:a', '160k', '-af', 'aresample=async=1',
                    '-metadata:s:v:0', 'title=Screen', '-metadata:s:v:1', 'title=Webcam',
                    '-metadata:s:a:0', 'title=Microphone']
        if system_audio:
            command += ['-metadata:s:a:1', 'title=System Audio']
    else:
        vertical, horizontal = ('center', 'center') if args.position == 'center' else args.position.split('-')
        x = {'left': str(args.margin), 'center': '(W-w)/2', 'right': f'W-w-{args.margin}'}[horizontal]
        y = {'top': str(args.margin), 'center': '(H-h)/2', 'bottom': f'H-h-{args.margin}'}[vertical]
        size = args.size
        flip = '' if args.no_mirror else 'hflip,'
        graph = (f"[1:v]crop='min(iw,ih)':'min(iw,ih)',scale={size}:{size},setsar=1,{flip}"
                 f"format=yuv420p,split[cam][masksrc];[masksrc]trim=end_frame=1,format=gray,"
                 f"geq=lum='255*clip({size}/2-hypot(X-(W-1)/2,Y-(H-1)/2),0,1)',"
                 f"loop=loop=-1:size=1:start=0,setpts=N/({args.camera_fps}*TB)[mask];"
                 f"[cam][mask]alphamerge=shortest=1[face];[0:v][face]overlay=x={x}:y={y}:"
                 'eof_action=pass,scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p[v];')
        graph += ('[2:a][3:a]amix=inputs=2:duration=longest:normalize=0,' if system_audio else '[2:a]')
        graph += 'aresample=async=1:first_pts=0[a]'
        command += ['-filter_complex_threads', '1', '-filter_complex', graph,
                    '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'ultrafast',
                    '-tune', 'zerolatency', '-crf', '20', '-r', str(args.fps),
                    '-c:a', 'aac', '-b:a', '160k']
    return command + [str(media)]


def run_capture(command, log_path, use_tray):
    child = None
    stopping = False

    def stop(*_):
        nonlocal stopping
        if stopping:
            return
        stopping = True
        if child is not None and child.poll() is None:
            try:
                child.send_signal(signal.SIGINT)
            except ProcessLookupError:
                pass  # Capture finished between poll() and the signal.

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        with log_path.open('ab') as log:
            # FFmpeg gets one explicit stop signal, independent of terminal signals.
            child = subprocess.Popen(command, stderr=subprocess.PIPE, start_new_session=True,
                                     env=system_program_env())
            if stopping:
                child.send_signal(signal.SIGINT)

            def diagnostics():
                for data in iter(lambda: child.stderr.read1(8192), b''):
                    log.write(data)
                    log.flush()
                    try:
                        sys.stderr.buffer.write(data)
                        sys.stderr.buffer.flush()
                    except (OSError, AttributeError):
                        pass

            reader = threading.Thread(target=diagnostics)
            reader.start()
            try:
                if use_tray:
                    import tray
                    tray.show(child, stop)
                status = child.wait()
            finally:
                if child.poll() is None:
                    stop()
                    child.wait()
                reader.join()
                child.stderr.close()
        return status, stopping
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def remux_command(media, output):
    return ['ffmpeg', '-hide_banner', '-nostdin', '-n', '-i', str(media), '-map', '0',
            '-c', 'copy', '-movflags', '+faststart', '-f', 'mp4', str(output)]


def record(args):
    if not re.fullmatch(r'[1-9][0-9]*x[1-9][0-9]*', args.camera_size):
        raise ValueError('camera-size must be WxH')
    if not shutil.which('ffmpeg'):
        raise ValueError('Install ffmpeg first.')
    if args.export == 'kdenlive' and not shutil.which('ffprobe'):
        raise ValueError('Kdenlive export requires ffprobe.')
    output, media, log = output_paths(args.output, args.export)
    screen, mic, system_audio = linux_capture.resolve_devices(args)
    if args.size + 2 * args.margin > min(screen.width, screen.height):
        raise ValueError('Circle and margin must fit inside the selected monitor.')
    label = linux_capture.camera_label(args.camera)
    print(f'Webcam: {args.camera}' + (f' ({label})' if label else ''))
    print(f'Microphone source: {mic}')
    if system_audio:
        print(f'System audio source: {system_audio}')
    inputs = linux_capture.capture_inputs(args, screen, mic, system_audio)
    capture = capture_command(args, inputs, media, system_audio)
    if args.dry_run:
        print(shlex.join(capture))
        if args.export == 'mp4':
            print(shlex.join(remux_command(media, output)))
        else:
            print(f'Kdenlive project: {media} -> {output} '
                  f'(fps={args.fps}, size={args.size}, margin={args.margin}, '
                  f'position={args.position}, mirror={not args.no_mirror})')
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f'Recording to {media}\nPress Ctrl+C to stop and export.\nCapture log: {log}', flush=True)
    status, stopped = run_capture(capture, log, not args.no_tray)
    if status not in (0, 255, 130, -signal.SIGINT):
        raise ValueError(f'Capture failed (exit {status}). Any partial recording remains at {media}; diagnostics: {log}')
    if not stopped:
        print(f'Warning: capture ended without Ctrl+C (exit {status}). Check {log}', file=sys.stderr)
    if not media.is_file() or not media.stat().st_size:
        raise ValueError(f'No recording was produced. Check {log}')
    try:
        if args.export == 'kdenlive':
            kdenlive.generate(media.resolve(), output, args.fps, args.size, args.margin,
                              args.position, not args.no_mirror)
        else:
            subprocess.run(remux_command(media, output), check=True, env=system_program_env())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        raise ValueError(f'Export failed; your recording remains at {media}: {exc}') from exc
    print(f'\nExported: {output}\nOriginal retained: {media}')


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if sys.platform != 'linux':
            raise ValueError('Recording currently supports Linux/X11 only.')
        if args.devices:
            linux_capture.show_devices()
        else:
            record(args)
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
