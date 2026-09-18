"""Linux/X11 device discovery and FFmpeg capture inputs."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import subprocess

from process_env import system_program_env


@dataclass(frozen=True)
class Monitor:
    name: str
    width: int
    height: int
    x: int
    y: int
    primary: bool


def query(*command):
    try:
        return subprocess.check_output(command, stderr=subprocess.DEVNULL,
                                       env=system_program_env(), text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def monitors(layout):
    result = []
    for line in layout.splitlines():
        fields = line.split()
        if len(fields) < 2 or fields[1] != 'connected':
            continue
        for field in fields[2:]:
            match = re.fullmatch(r'(\d+)x(\d+)([+-]\d+)([+-]\d+)', field)
            if match:
                result.append(Monitor(fields[0], *map(int, match.groups()),
                                      'primary' in fields[2:]))
                break
    return result


def camera_label(device):
    try:
        return (Path('/sys/class/video4linux') / Path(device).resolve().name / 'name').read_text().strip()
    except OSError:
        return ''


def show_devices():
    print('\nScreens  (--monitor NAME)')
    layout = query('xrandr', '--query')
    if layout is None:
        print('  Unavailable. Run in an X11 desktop with xrandr installed.')
    else:
        screens = monitors(layout)
        for screen in screens:
            print(f'  {screen.name:<16} {str(screen.width)+"x"+str(screen.height):<12} '
                  + ('(primary)' if screen.primary else ''))
        if not screens:
            print('  No active screens found.')
    print('\nCameras  (--camera DEVICE)')
    listing = query('v4l2-ctl', '--list-devices')
    found = False
    if listing:
        label = ''
        for line in listing.splitlines():
            if line and not line[0].isspace():
                label = line.rstrip(':')
            elif line.strip().startswith('/dev/video'):
                print(f'  {line.strip():<16} {label}')
                found = True
    else:
        for device in sorted(Path('/dev').glob('video*')):
            print(f'  {str(device):<16} {camera_label(device) or "Video device"}')
            found = True
    if not found:
        print('  No cameras found.')
    print('\nAudio sources  (--mic SOURCE / --system-audio SOURCE)')
    listing = query('pactl', 'list', 'short', 'sources')
    if listing is None:
        print('  Unavailable. Check PulseAudio/PipeWire and install pulseaudio-utils.')
    else:
        default = query('pactl', 'get-default-source')
        sources = [line.split()[1] for line in listing.splitlines() if len(line.split()) >= 2]
        for source in sources:
            print('  ' + source + (' (default)' if source == default else '')
                  + (' [system audio]' if source.endswith('.monitor') else ''))
        if not sources:
            print('  No audio sources found.')
    print('\nUse the names above with --monitor, --camera, --mic, and --system-audio.\n')


def resolve_devices(args):
    if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
        raise ValueError('This recorder requires an X11 session. Log into an Xorg session; x11grab cannot capture a Wayland desktop.')
    if not os.environ.get('DISPLAY'):
        raise ValueError('DISPLAY is unset; run this in your desktop terminal.')
    if not shutil.which('xrandr'):
        raise ValueError('Install x11-xserver-utils for xrandr.')
    layout = query('xrandr', '--query')
    if layout is None:
        raise ValueError('Cannot query displays; run this in your desktop terminal.')
    active = [s for s in monitors(layout) if s.x >= 0 and s.y >= 0]
    selected = next((s for s in active if s.name == args.monitor), None) if args.monitor else next((s for s in active if s.primary), None)
    if selected is None and not args.monitor:
        if len(active) != 1:
            raise ValueError('No primary monitor set. Use --devices and --monitor NAME.')
        selected = active[0]
    if selected is None:
        raise ValueError('Selected monitor is not active or its geometry is unsupported.')
    if not Path(args.camera).is_char_device() or not os.access(args.camera, os.R_OK):
        raise ValueError(f'Cannot read webcam {args.camera}. Use --devices to choose a camera.')
    mic = args.mic
    if mic == 'default':
        mic = query('pactl', 'get-default-source') or mic
    system_audio = args.system_audio
    if system_audio == 'default':
        if not shutil.which('pactl'):
            raise ValueError('Resolving default system audio requires pactl (pulseaudio-utils).')
        sink = query('pactl', 'get-default-sink')
        if not sink:
            raise ValueError('Cannot determine the default audio output. Use --devices and pass its monitor source.')
        system_audio = sink + '.monitor'
    return selected, mic, system_audio


def capture_inputs(args, screen, mic, system_audio):
    sync = ['-isync', '0'] if args.export == 'kdenlive' else []
    inputs = ['-thread_queue_size', '8', '-use_wallclock_as_timestamps', '1',
              '-f', 'x11grab', '-probesize', '32', '-analyzeduration', '0',
              '-framerate', str(args.fps), '-video_size', f'{screen.width}x{screen.height}',
              '-draw_mouse', '1', '-i', f'{os.environ["DISPLAY"]}+{screen.x},{screen.y}',
              '-thread_queue_size', '8', '-use_wallclock_as_timestamps', '1',
              '-f', 'v4l2', '-probesize', '32', '-analyzeduration', '0',
              '-framerate', str(args.camera_fps), '-video_size', args.camera_size]
    if args.camera_format:
        inputs += ['-input_format', args.camera_format]
    inputs += sync + ['-i', args.camera]
    for source in [mic] + ([system_audio] if system_audio else []):
        inputs += ['-thread_queue_size', '512', '-use_wallclock_as_timestamps', '1',
                   '-f', 'pulse'] + sync + ['-i', source]
    return inputs
