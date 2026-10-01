# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ("transformers", "torch", "av", "ctranslate2", "faster_whisper",
            "edge_tts", "tkinterdnd2"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test", "pydoc_data"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe_gui = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="VideoVoiceOver", console=False, icon="icon.ico",
    upx=False, disable_windowed_traceback=False,
)
exe_cli = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="VideoVoiceOver_CLI", console=True, icon="icon.ico", upx=False,
)
coll = COLLECT(
    exe_gui, exe_cli, a.binaries, a.datas,
    strip=False, upx=False, upx_exclude=[],
    name="VideoVoiceOver",
)
