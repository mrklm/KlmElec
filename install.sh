#!/bin/sh
# Installe KlmElec pour l'utilisateur courant (Linux) : pipx + raccourci dans le menu.
# Usage : ./install.sh            installe ou met à jour depuis ce dossier
#         ./install.sh --desinstaller
set -eu

SOURCE=$(cd "$(dirname "$0")" && pwd)
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
DESKTOP="$DATA/applications/klmelec.desktop"
ICON="$DATA/icons/klmelec.png"

if ! command -v pipx >/dev/null 2>&1; then
    echo "pipx est introuvable. Installez-le d'abord, par exemple :"
    echo "  sudo apt install pipx && pipx ensurepath"
    exit 1
fi

if [ "${1:-}" = "--desinstaller" ]; then
    pipx uninstall klmelec || true
    rm -f "$DESKTOP" "$ICON"
    echo "KlmElec est désinstallé. Vos données restent dans $DATA/KlmElec."
    exit 0
fi

pipx install --force "$SOURCE"
BIN="$(pipx environment --value PIPX_BIN_DIR)/klmelec"

mkdir -p "$(dirname "$DESKTOP")" "$(dirname "$ICON")"
cp "$SOURCE/src/klmelec/assets/klmelec-rond.png" "$ICON"
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=KlmElec
Comment=Préparation de listes de matériel électrique
Exec="$BIN"
Icon=$ICON
Terminal=false
Categories=Utility;
StartupWMClass=klmelec
EOF
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$(dirname "$DESKTOP")" || true

echo "KlmElec $(cat "$SOURCE/VERSION") est installé : menu des applications ou commande « $BIN »."
