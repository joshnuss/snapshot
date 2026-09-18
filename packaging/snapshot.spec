from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / 'snapshot')],
    pathex=[str(root)],
    # The tray draws its own SVG. Do not bundle every desktop icon/theme.
    hooksconfig={'gi': {'icons': [], 'themes': [], 'languages': [],
                        'module-versions': {'Gtk': '3.0', 'Gdk': '3.0'}}},
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name='snapshot', console=True, upx=False)
