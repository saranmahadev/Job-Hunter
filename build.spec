# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path
import customtkinter

block_cipher = None

# Get customtkinter path for data files
customtkinter_path = Path(customtkinter.__path__[0])

a = Analysis(
    ['src/interview_tracker/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        (str(customtkinter_path), 'customtkinter'),
    ],
    hiddenimports=[
        'babel.numbers',
        'win32timezone',
        'pystray',
        'PIL._tkinter_finder',
        'google_auth_oauthlib',
        'googleapiclient.discovery',
        'googleapiclient.errors',
        'google.auth.transport.requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Interview Tracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None # Add icon path if available
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Interview Tracker',
)
