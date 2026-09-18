#!/usr/bin/env python3
"""Run capture with an optional GTK3/X11 tray icon and graceful stop signals."""
import os
import signal
import subprocess
import sys
import time

from process_env import system_program_env


def main():
    command = sys.argv[1:]
    if not command:
        return 2
    child = None
    stopping = False

    def stop(*_):
        nonlocal stopping
        if stopping:
            return
        stopping = True
        if child is not None and child.poll() is None:
            child.send_signal(signal.SIGINT)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    # Separate group prevents terminal Ctrl+C reaching FFmpeg twice.
    child = subprocess.Popen(command, start_new_session=True, env=system_program_env())
    if stopping:
        child.send_signal(signal.SIGINT)
    try:
        try:
            import gi
            gi.require_version('Gtk', '3.0')
            from gi.repository import Gtk, GLib, GdkPixbuf
            if not Gtk.init_check()[0]:
                raise RuntimeError('cannot connect to the desktop display')
        except (ImportError, ValueError, RuntimeError) as exc:
            print(f'Tray unavailable ({exc}); use Ctrl+C to stop.', file=sys.stderr)
            return child.wait()

        # Embedded SVG keeps the icon independent of installed icon themes.
        svg = b'''<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">
        <circle cx="16" cy="16" r="13" fill="#ef4444" stroke="white" stroke-width="2"/>
        <rect x="11" y="11" width="10" height="10" rx="1" fill="white"/></svg>'''
        loader = GdkPixbuf.PixbufLoader.new_with_type('svg')
        loader.write(svg)
        loader.close()
        icon = Gtk.StatusIcon.new_from_pixbuf(loader.get_pixbuf())
        icon.set_title('Snapshot recording')
        icon.set_tooltip_text('Snapshot: recording — click to stop and save')

        def clicked(*_):
            if not stopping and child.poll() is None:
                # Tell the Bash wrapper this was an intentional stop.
                os.kill(int(os.environ.get('SNAPSHOT_RECORDER_PID', os.getppid())), signal.SIGUSR1)
                stop()
                icon.set_tooltip_text('Snapshot: finishing recording…')

        icon.connect('activate', clicked)
        menu = Gtk.Menu()
        item = Gtk.MenuItem(label='Stop recording and save')
        item.connect('activate', clicked)
        menu.append(item)
        menu.show_all()
        icon.connect('popup-menu', lambda _, button, timestamp:
                     menu.popup(None, None, Gtk.StatusIcon.position_menu,
                                icon, button, timestamp))
        icon.set_visible(True)
        started = time.monotonic()
        warned = False

        def poll():
            nonlocal warned
            if child.poll() is not None:
                icon.set_visible(False)
                Gtk.main_quit()
                return False
            if not warned and time.monotonic() - started > 3 and not icon.is_embedded():
                print('No system tray detected; use Ctrl+C to stop.', file=sys.stderr)
                warned = True
            return True

        GLib.timeout_add(100, poll)
        Gtk.main()
        return child.wait()
    finally:
        # Never leave a recording running if the UI helper fails.
        if child.poll() is None:
            stop()
            child.wait()


if __name__ == '__main__':
    result = main()
    sys.exit(128 - result if result < 0 else result)
