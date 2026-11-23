"""Génère les icônes de release (Windows .ico, macOS .icns, Linux .png) à partir du logo.

Usage (Pillow requis) : python3 packaging/make_icons.py
Les fichiers produits dans packaging/icons/ sont versionnés : ne relancer qu'après un changement de logo.
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'src' / 'klmelec' / 'assets' / 'klmelec-rond.png'
OUT = ROOT / 'icons'
MARGIN = 0.04  # marge transparente autour du logo


def square(image):
    image = image.convert('RGBA').crop(image.getbbox())
    side = round(max(image.size) * (1 + 2 * MARGIN))
    canvas = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    canvas.paste(image, ((side - image.width) // 2, (side - image.height) // 2), image)
    return canvas.resize((1024, 1024), Image.LANCZOS)


def main():
    OUT.mkdir(exist_ok=True)
    icon = square(Image.open(SOURCE))
    icon.resize((512, 512), Image.LANCZOS).save(OUT / 'klmelec.png', optimize=True)
    icon.save(OUT / 'klmelec.ico', sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    icon.save(OUT / 'klmelec.icns')
    print('Icônes générées dans', OUT)


if __name__ == '__main__':
    main()
