"""
CyberGuy app icon.

Draws the icon from the app's own name - a terminal-green "CG" monogram with a
prompt cursor, over a dark tile with faint matrix rain - then packs it into the
.icns the Desktop launcher bundle uses.

Usage:
    python3 make_icon.py                     # writes static/img/ + /tmp/cyberguy.icns
    python3 make_icon.py /path/to/App.app     # also installs it into that bundle

The tile hues match the app's Ghost-in-the-Wire palette in sprites.py so the
launcher icon reads as the same product as the character sheet it opens.
"""
import os
import random
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

S = 1024                      # master size; every icns slot is downsampled from it
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "static", "img")

BG_TOP = (17, 27, 36)
BG_BOTTOM = (5, 9, 13)
EDGE = (0, 229, 255)
GREEN = (77, 255, 158)
RAIN = (0, 229, 255)

# 5x7 pixel glyphs - blocky on purpose, so the monogram reads as terminal type
# rather than as a font, and still holds its shape at 16px.
GLYPHS = {
    "C": ["01110",
          "11111",
          "11000",
          "11000",
          "11000",
          "11111",
          "01110"],
    "G": ["01110",
          "11111",
          "11000",
          "11011",
          "11011",
          "11111",
          "01111"],
}


def _rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius, fill=255)
    return m


def _gradient(size):
    g = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        g.putpixel((0, y), tuple(
            int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3)))
    return g.resize((size, size))


def _matrix_rain(size, seed=7):
    """Faint vertical code rain. Texture only - it must never compete with the
    monogram, so it tops out well under 20% alpha."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rng = random.Random(seed)
    col_w = size // 26
    for col in range(26):
        x = col * col_w + col_w // 4
        y = rng.randrange(-size // 2, size)
        length = rng.randrange(size // 6, size // 2)
        cell = col_w
        while y < min(y + length, size):
            if 0 <= y < size and rng.random() < 0.72:
                a = rng.randrange(14, 42)
                d.rectangle([x, y, x + cell // 2, y + cell // 2], fill=(*RAIN, a))
            y += cell
            if y > size:
                break
    return layer.filter(ImageFilter.GaussianBlur(size / 400))


def _monogram(size):
    """'CG' plus a prompt cursor, on its own layer so it can be glowed."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    px = int(size * 0.050)                    # one glyph pixel
    gap = px                                  # space between the two letters
    cursor_w = int(px * 2.6)          # a chunky block cursor - a thin caret
                                      # would read as the letter I at 16px
    text_w = (5 * px) * 2 + gap + int(px * 0.7) + cursor_w
    block_h = 7 * px + int(px * 1.9)          # glyphs + the command-line rule
    x0 = (size - text_w) // 2
    y0 = (size - block_h) // 2

    for i, ch in enumerate(("C", "G")):
        gx = x0 + i * (5 * px + gap)
        for ry, row in enumerate(GLYPHS[ch]):
            for rx, bit in enumerate(row):
                if bit == "1":
                    x, y = gx + rx * px, y0 + ry * px
                    d.rectangle([x, y, x + px - 1, y + px - 1], fill=(*GREEN, 255))

    # underscore-style prompt cursor on the baseline right of the G. A
    # full-height block sits there like a third letter and the monogram starts
    # reading as "CGI"; on the baseline it reads as a terminal caret.
    cx = x0 + 2 * (5 * px + gap) - gap + int(px * 0.7)
    d.rectangle([cx, y0 + 5 * px, cx + cursor_w - 1, y0 + 7 * px - 1],
                fill=(*EDGE, 235))

    # the command line the guy is typing on
    uy = y0 + 7 * px + int(px * 1.6)
    d.rectangle([x0, uy, x0 + text_w - 1, uy + max(2, int(px * 0.38))],
                fill=(*EDGE, 150))
    return layer


def build_master():
    size = S
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon.paste(_gradient(size).convert("RGBA"), (0, 0))
    icon.alpha_composite(_matrix_rain(size))

    # scanlines - subtle CRT read, 1px on / 3px off at master scale
    lines = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lines)
    for y in range(0, size, max(1, size // 256)):
        dl.line([(0, y), (size, y)], fill=(0, 0, 0, 26))
    icon.alpha_composite(lines)

    # monogram with its own bloom
    mono = _monogram(size)
    glow = mono.filter(ImageFilter.GaussianBlur(size / 34))
    icon.alpha_composite(Image.blend(Image.new("RGBA", (size, size), (0, 0, 0, 0)), glow, 0.85))
    icon.alpha_composite(mono)

    # inner edge stroke
    stroke = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ds = ImageDraw.Draw(stroke)
    inset = int(size * 0.035)
    ds.rounded_rectangle([inset, inset, size - 1 - inset, size - 1 - inset],
                         int(size * 0.19), outline=(*EDGE, 105), width=max(2, size // 190))
    icon.alpha_composite(stroke)

    # clip to the macOS tile shape
    icon.putalpha(_rounded_mask(size, int(size * 0.225)))
    return icon


ICNS_SLOTS = [(16, ["16x16"]), (32, ["16x16@2x", "32x32"]), (64, ["32x32@2x"]),
              (128, ["128x128"]), (256, ["128x128@2x", "256x256"]),
              (512, ["256x256@2x", "512x512"]), (1024, ["512x512@2x"])]


def build_icns(master, icns_path="/tmp/cyberguy.icns"):
    iconset = "/tmp/cyberguy.iconset"
    shutil.rmtree(iconset, ignore_errors=True)
    os.makedirs(iconset)
    for size, names in ICNS_SLOTS:
        im = master.resize((size, size), Image.LANCZOS)
        for n in names:
            im.save(f"{iconset}/icon_{n}.png")
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", icns_path], check=True)
    return icns_path


if __name__ == "__main__":
    master = build_master()
    os.makedirs(IMG_DIR, exist_ok=True)
    png = os.path.join(IMG_DIR, "cyberguy_icon.png")
    master.save(png)
    master.resize((256, 256), Image.LANCZOS).save(os.path.join(IMG_DIR, "cyberguy_icon_256.png"))
    icns = build_icns(master)
    print(f"icon  {png}")
    print(f"icns  {icns}")

    if len(sys.argv) > 1:
        dest = os.path.join(sys.argv[1], "Contents", "Resources", "app.icns")
        shutil.copy(icns, dest)
        print(f"installed -> {dest}")
