# -*- mode: python ; coding: utf-8 -*-
"""
ETF Monitor - PyInstaller Build Configuration
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all wx submodules and data files
hiddenimports = collect_submodules('wx')
hiddenimports += [
    'wx.adv',
    'wx.html', 
    'wx.xml',
    'wx.lib',
    'wx.lib.agw',
    'wx.lib.mixins',
]

# Data files to include
datas = [
    ('config.default.json', '.'),
    ('resources', 'resources'),
]

# Collect wx data files (locale, icons, etc)
try:
    datas += collect_data_files('wx')
except Exception:
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'scipy',
        'tkinter',
        'PyQt5',
        'PySide2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ETFMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/tray.ico' if os.path.exists('resources/icons/tray.ico') else None,
    version_file=None,
)

