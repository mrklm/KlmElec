# Spécification PyInstaller : pyinstaller --noconfirm packaging/klmelec.spec
# Prérequis : paquet installé (pip install .) pour embarquer ses métadonnées de version.
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

ROOT = Path(SPECPATH).parent
ICONS = Path(SPECPATH) / 'icons'
VERSION = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
icon = (str(ICONS / 'klmelec.ico') if sys.platform == 'win32' else str(ICONS / 'klmelec.icns') if sys.platform == 'darwin' else None)

a = Analysis(
    [str(Path(SPECPATH) / 'launcher.py')],
    pathex=[str(ROOT / 'src')],
    datas=collect_data_files('klmelec') + copy_metadata('klmelec'),
    excludes=['tkinter', 'pytest', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.Qt3DCore', 'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtMultimedia'],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='KlmElec', icon=icon,
          console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='KlmElec', upx=False)

if sys.platform == 'darwin':
    app = BUNDLE(coll, name='KlmElec.app', icon=icon, bundle_identifier='fr.klmelec.KlmElec',
                 version=VERSION,
                 info_plist={'CFBundleShortVersionString': VERSION, 'CFBundleVersion': VERSION,
                             'NSHighResolutionCapable': True, 'LSMinimumSystemVersion': '12.0'})
