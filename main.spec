# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for TFG – Libretro Frontend
#
# Uso:  pyinstaller main.spec
#
# El .exe resultante espera estas carpetas JUNTO A ÉL (no se empaquetan):
#   cores/      → DLLs de los cores libretro
#   games/      → ROMs, games.json, nombres.json, listas.json, icons/
#   saves/      → Datos de guardado (se crean en tiempo de ejecución)
#   system/     → Archivos de sistema de los cores
#   config.json → Configuración de la app (se crea en tiempo de ejecución)
#
# Los archivos .qss y el código Python se empaquetan dentro del .exe.

import os
import glob

block_cipher = None

# ── Recopilar QSS ───────────────────────────────────────────────
# Se empaquetan dentro de _MEIPASS/ui/**/*.qss
qss_datas = []
for qss in glob.glob(os.path.join('ui', '**', '*.qss'), recursive=True):
    dest = os.path.dirname(qss)           # p.ej. ui/sidebar
    qss_datas.append((qss, dest))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=qss_datas,
    hiddenimports=[
        # PyOpenGL – PyInstaller no detecta todos sus módulos automáticamente
        'OpenGL',
        'OpenGL.GL',
        'OpenGL.GL.framebufferobjects',
        'OpenGL.platform.win32',
        'OpenGL.platform',
        'OpenGL.arrays',
        'OpenGL.arrays.ctypesarrays',
        'OpenGL.arrays.ctypesparameters',
        'OpenGL.arrays.ctypespointers',
        'OpenGL.arrays.numpymodule',
        'OpenGL.arrays.strings',
        'OpenGL.arrays.numbers',
        'OpenGL.converters',
        'OpenGL.error',
        'OpenGL.constant',
        'OpenGL.contextdata',
        'OpenGL.plugins',
        # PyAudio
        'pyaudio',
        # PIL / Pillow
        'PIL',
        'PIL.Image',
        # Módulos propios que se importan dinámicamente o por string
        'retro_core',
        'retro_definitions',
        'audio_manager',
        'input_manager',
        'juego',
        'lista',
        'ui.openGLWidget',
        'ui.mainWindow.mainWindow',
        'ui.mainWindow.mainWindowUI',
        'ui.gameWindow.gameWindow',
        'ui.gameWindow.gameWindowUI',
        'ui.header.header',
        'ui.header.headerUI',
        'ui.sidebar.sidebar',
        'ui.sidebar.sidebarUI',
        'ui.editableLabel.editableLabel',
        'ui.configWindow.configWindow',
        'ui.configWindow.configWindowUI',
        'ui.gameSideBar.gameSideBar',
        'ui.gameSideBar.gameSideBarUI',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
    ],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,             # todo empaquetado dentro del .exe (modo onefile)
    a.datas,
    [],
    name='TFG',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # UPX puede dañar DLLs de OpenGL
    console=True,           # Mantener consola para ver errores
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
