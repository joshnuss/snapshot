"""Keep system programs from loading PyInstaller's bundled Linux libraries."""
import os
import sys


def system_program_env():
    env = os.environ.copy()
    if getattr(sys, 'frozen', False) and sys.platform.startswith('linux'):
        original = env.pop('LD_LIBRARY_PATH_ORIG', None)
        if original is None:
            env.pop('LD_LIBRARY_PATH', None)
        else:
            env['LD_LIBRARY_PATH'] = original
    return env
