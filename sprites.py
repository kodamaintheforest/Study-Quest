import random
from PIL import Image

WIDTH = 22
TORSO_ROWS = range(7, 13)   # rows that "puff" on the inhale animation frame
GLOW_PULSE = [0, 40]        # brightness offset per frame for glow chars

# Each tier is its own content list (unpadded, centered at build time) -
# accessories get added/replaced structurally per tier rather than patched
# in dynamically, since shades *replace* the eye row entirely rather than
# just recoloring it.

TIER0_ROWS = [  # Script Kiddie - plain hoodie, no gear
    "HHHH",
    "HhhhhH",
    "HhhhhhhH",
    "HhhDDDDhhH",
    "HKKKKKKKKH",
    "HKKGGGGKKH",
    "HKKKKKKKKH",
    "HhhhhhhhhH",
    "HhhhhhhhhhhH",
    "HhhhhhhhhhhhhH",
    "HhhhhhhhhhhhhhhH",
    "HhhhhhWhhhhhhhhhhH",
    "HhhhhhWhhhhhhhhhhH",
    "HhhhhhWhhhhhhhhhhH",
    "HDDhhhWhhhhhDDDhH",
    "HDDhhhWhhhhhDDDhH",
    "HhhTTTWTTTThhhhH",
    "HhTTT.LLLLLL.TThH",
    "HhTT..LVllllVL..ThH",
    "HhT...LllllllL...ThH",
    ".HT...LLLLLLLL...TH.",
    "..H..............H..",
]

TIER1_ROWS = [  # Red Teamer - patterned scarf added across the neckline
    "HHHH",
    "HhhhhH",
    "HhhhhhhH",
    "HhhDDDDhhH",
    "HKKKKKKKKH",
    "HKKGGGGKKH",
    "HKKKKKKKKH",
    "HxXxXxXxXH",
    "HhxXxXxXxhH",
    "HhhxXxXxhhhH",
    "HhhhhhhhhhhhhhhH",
    "HhhhhhWhhhhhhhhhhH",
    "HhhhhhWhhhhhhhhhhH",
    "HhhhhhWhhhhhhhhhhH",
    "HDDhhhWhhhhhDDDhH",
    "HDDhhhWhhhhhDDDhH",
    "HhhTTTWTTTThhhhH",
    "HhTTT.LLLLLL.TThH",
    "HhTT..LVllllVL..ThH",
    "HhT...LllllllL...ThH",
    ".HT...LLLLLLLL...TH.",
    "..H..............H..",
]

TIER2_ROWS = [  # Ghost in the Wire - shades replace eyes, scarf, bracelet glint
    "HHHH",
    "HhhhhH",
    "HhhhhhhH",
    "HhhDDDDhhH",
    "HSSSSSSSSH",
    "HSSSSSSSSH",
    "HKKKKKKKKH",
    "HxXxXxXxXH",
    "HhxXxXxXxhH",
    "HhhxXxXxhhhH",
    "HhhhhhhhhhhhhhhH",
    "HhhhhhWhhhhhhhhhhH",
    "HhhhhhWhhhhhhhhhhH",
    "HhhhhhWhhhhhhhhhhH",
    "HDDhhhWhhhhhDDDhH",
    "HDDhhhWhhhhhDDDhH",
    "HhZTTTWTTTThZhhH",
    "HhTTT.LLLLLL.TThH",
    "HhTT..LVllllVL..ThH",
    "HhT...LllllllL...ThH",
    ".HT...LLLLLLLL...TH.",
    "..H..............H..",
]

TIER_GRIDS = {0: TIER0_ROWS, 1: TIER1_ROWS, 2: TIER2_ROWS}

PALETTES = {
    0: {"name": "Script Kiddie", "H": "#20242b", "h": "#2c3038", "D": "#101216",
        "K": "#0a0a0d", "G": "#4d5a66", "L": "#3a3d42", "l": "#5fa8c9",
        "T": "#181b20", "W": "#14161a", "V": "#101216"},
    1: {"name": "Red Teamer", "H": "#2b1010", "h": "#3a1717", "D": "#140505",
        "K": "#0a0a0d", "G": "#ff3b3b", "L": "#3a1414", "l": "#ff5c5c",
        "T": "#1c0a0a", "W": "#200909", "V": "#140505",
        "x": "#0d0d0d", "X": "#c9c9c9"},
    2: {"name": "Ghost in the Wire", "H": "#041019", "h": "#0a1e29", "D": "#00080d",
        "K": "#000000", "L": "#0a2a33", "l": "#00e5ff",
        "T": "#031117", "W": "#00232b", "V": "#00080d",
        "x": "#041019", "X": "#e8f6fa", "S": "#dff7ff", "Z": "#ffd76b"},
}


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _brighten(rgb, amount):
    return tuple(min(255, c + amount) for c in rgb)


def _build_grid(tier, frame_idx):
    rows = list(TIER_GRIDS[tier])
    if frame_idx == 1:
        for i in TORSO_ROWS:
            if i < len(rows):
                rows[i] = ("h" * 2) + rows[i] + ("h" * 2)
    return [row.center(WIDTH, ".") for row in rows]


def render_frame(tier, frame_idx, scale=16, grain=6):
    palette = PALETTES[tier]
    grid = _build_grid(tier, frame_idx)
    h, w = len(grid), len(grid[0])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    glow_boost = GLOW_PULSE[frame_idx % len(GLOW_PULSE)]
    rng = random.Random(tier * 100 + frame_idx)

    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            rgb = _hex_to_rgb(palette[ch])
            if ch in ("G", "l"):
                rgb = _brighten(rgb, glow_boost)
            img.putpixel((x, y), (*rgb, 255))

    for _ in range(grain):
        gx, gy = rng.randrange(w), rng.randrange(h)
        r, g, b, a = img.getpixel((gx, gy))
        if a == 0:
            continue
        shift = rng.choice([-30, 30])
        rgb = _brighten((r, g, b), shift)
        img.putpixel((gx, gy), (*rgb, a))

    return img.resize((w * scale, h * scale), Image.NEAREST)


def generate_all(output_dir=".", frames_per_tier=2):
    paths = {}
    for tier in PALETTES:
        paths[tier] = []
        for f in range(frames_per_tier):
            img = render_frame(tier, f)
            path = f"{output_dir}/sprite_tier{tier}_f{f}.png"
            img.save(path)
            paths[tier].append(path)
    return paths


if __name__ == "__main__":
    generate_all()
