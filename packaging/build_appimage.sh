#!/bin/sh
# Assemble dist/KlmElec-<version>-x86_64.AppImage à partir de dist/KlmElec (PyInstaller).
# Usage : packaging/build_appimage.sh [chemin/vers/appimagetool]
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
VERSION=$(cat "$ROOT/VERSION")
TOOL=${1:-appimagetool}
APPDIR="$ROOT/build/KlmElec.AppDir"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/share/icons/hicolor/512x512/apps"
cp -r "$ROOT/dist/KlmElec" "$APPDIR/usr/lib-klmelec"
cp "$ROOT/packaging/icons/klmelec.png" "$APPDIR/klmelec.png"
cp "$ROOT/packaging/icons/klmelec.png" "$APPDIR/usr/share/icons/hicolor/512x512/apps/klmelec.png"
ln -s klmelec.png "$APPDIR/.DirIcon"
cat > "$APPDIR/klmelec.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=KlmElec
Comment=Préparation de listes de matériel électrique
Exec=KlmElec
Icon=klmelec
Terminal=false
Categories=Utility;
StartupWMClass=klmelec
DESKTOP
cat > "$APPDIR/AppRun" <<'APPRUN'
#!/bin/sh
HERE=$(dirname "$(readlink -f "$0")")
exec "$HERE/usr/lib-klmelec/KlmElec" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" --no-appstream "$APPDIR" "$ROOT/dist/KlmElec-$VERSION-x86_64.AppImage"
