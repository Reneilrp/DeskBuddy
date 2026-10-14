# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None
base_dir = Path.cwd()

a = Analysis(
    ['main.py'],
    pathex=[str(base_dir)],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'sqlite3',
        'apscheduler',
        'apscheduler.schedulers.background',
        'src.agent.brain',
        'src.core.stash_manager',
        'src.core.clipboard_assistant',
        'src.core.download_watcher',
        'src.core.cleanup_hunter',
        'src.core.ergonomics_tracker',
        'src.core.fast_search',
        'src.core.file_organizer',
        'src.core.task_manager',
        'src.core.resonators',
        'src.core.desktop_watcher',
        'src.core.window_detector',
        'src.ui.pet_window',
        'src.ui.speech_bubble',
        'src.ui.workspace_dialog',
        'src.ui.task_dialog',
        'src.ui.resonator_dialog',
        'src.ui.stash_dialog',
        'src.ui.tray',
        'src.ui.chibi_rig',
        'src.ui.sprite_animator',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy'],
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
    name='DeskBuddy',
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
    icon='assets/tray_icon.ico' if Path('assets/tray_icon.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DeskBuddy',
)
