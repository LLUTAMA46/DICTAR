# -*- mode: python ; coding: utf-8 -*-
"""Receptari de PyInstaller per fabricar DICTAR per a Windows.

S'executa des de l'arrel del projecte:  pyinstaller build/dictar.spec
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ARREL = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [
    (os.path.join(ARREL, "logo_small.png"), "."),
    (os.path.join(ARREL, "logo.png"), "."),
]
datas += collect_data_files("_sounddevice_data")   # portaudio (micròfon)
datas += collect_data_files("certifi")              # certificats https

hiddenimports = (
    collect_submodules("pynput")
    + [
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        "win32clipboard", "win32gui", "win32api", "win32con",
        "_sounddevice", "sounddevice", "_cffi_backend",
        "groq", "httpx", "httpcore", "h11", "anyio", "sniffio", "certifi", "idna",
        "flask", "jinja2", "markupsafe", "werkzeug",
        "dotenv", "numpy",
    ]
)

a = Analysis(
    [os.path.join(ARREL, "main.py")],
    pathex=[ARREL],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "AppKit", "objc", "pyautogui"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DICTAR",
    debug=False,
    strip=False,
    upx=False,          # sense compressió: els antivirus en desconfien menys
    console=False,      # sense finestra negra
    icon=os.path.join(ARREL, "build", "dictar.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DICTAR",
)
