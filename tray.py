"""Optional GTK3/X11 tray UI; the recorder owns the capture process."""
import sys
import time


def show(child, stop):
    """Wait for capture, invoking stop when the user clicks the tray icon."""
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
        if child.poll() is None:
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
