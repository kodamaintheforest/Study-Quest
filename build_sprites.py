"""
One-time-ish build step: slices the source spritesheet into individual poses,
mattes out the white/gutter background, and generates neutral/red/green tier
variants. Run this again if you swap in new source art.

Usage: python build_sprites.py path/to/source_spritesheet.png
"""
import sys
import os
from collections import deque

import numpy as np
from PIL import Image

POSE_MAP = {
    0: "standing",
    1: "typing_1",
    2: "typing_2",
    3: "idle_1",
    4: "idle_2",
    5: "phone",
    6: "reading",
    7: "headphones_off",
    8: "video",
    9: "celebrate",
}

TINTS = {
    "neutral": None,
    "red": (255, 90, 90),
    "green": (90, 255, 130),
}

GUTTER = np.array([33, 33, 41])
INSET = 5

ROW_BANDS = [(11, 278), (292, 558), (573, 840)]
COL_SETS = [
    [(11, 170), (181, 338), (348, 559), (574, 841)],
    [(11, 278), (292, 559), (573, 841)],
    [(11, 278), (292, 559), (573, 841)],
]


def _is_removable_bg(px, tol=28):
    white_dist = np.abs(px.astype(int) - 255).sum()
    gutter_dist = np.abs(px.astype(int) - GUTTER).sum()
    return white_dist < tol or gutter_dist < tol


def _flood_remove_bg(panel_rgb, tol=28):
    h, w, _ = panel_rgb.shape
    rgba = np.dstack([panel_rgb, np.full((h, w), 255, dtype=np.uint8)])
    visited = np.zeros((h, w), dtype=bool)
    q = deque()

    def seed(x, y):
        if _is_removable_bg(panel_rgb[y, x], tol) and not visited[y, x]:
            visited[y, x] = True
            q.append((x, y))

    for x in range(w):
        seed(x, 0)
        seed(x, h - 1)
    for y in range(h):
        seed(0, y)
        seed(w - 1, y)

    while q:
        x, y = q.popleft()
        rgba[y, x, 3] = 0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx] and _is_removable_bg(panel_rgb[ny, nx], tol):
                visited[ny, nx] = True
                q.append((nx, ny))

    # Third pass: erase small floating islands. Baked-in pixel glyphs
    # (katakana/numbers around the head in some panels) end up as tiny
    # opaque islands after matting - character stays as one big connected
    # component, glyphs are dozens of ~20-40px orphans. Color-key won't
    # work here because glyphs use the same shade as the panel gutter.
    try:
        from scipy import ndimage
        opaque = rgba[..., 3] > 0
        labels, n_labels = ndimage.label(opaque)
        if n_labels > 0:
            sizes = ndimage.sum(opaque, labels, range(1, n_labels + 1))
            small_labels = [i + 1 for i, s in enumerate(sizes) if s < 200]
            for lbl in small_labels:
                rgba[labels == lbl, 3] = 0
    except ImportError:
        pass  # scipy not available - glyphs will remain

    return rgba


def _skin_mask(rgb):
    # Cheap heuristic skin-tone classifier (works fine on flat-shaded pixel
    # art). True = skin, should be excluded from tinting.
    r, g, b = rgb[..., 0].astype(int), rgb[..., 1].astype(int), rgb[..., 2].astype(int)
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    return (
        (r > 95) & (g > 40) & (b > 20)
        & ((max_c - min_c) > 15)
        & (np.abs(r - g) > 15)
        & (r > g) & (r > b)
    )


def add_outer_aura(img, tint_rgb, thickness=14, blur_radius=16, strength=0.55):
    """Big soft outer glow - reads as energy/aura emanating from the character,
    not just a rim outline. Layers *behind* the character (character on top).
    Set thickness=0 or strength=0 to skip."""
    from PIL import ImageFilter

    if thickness <= 0 or strength <= 0:
        return img

    alpha = img.split()[3]
    dilated = alpha.filter(ImageFilter.MaxFilter(thickness * 2 + 1))
    aura_arr = np.array(dilated).astype(np.uint8)

    aura_rgba = np.zeros((*aura_arr.shape, 4), dtype=np.uint8)
    aura_rgba[..., 0] = tint_rgb[0]
    aura_rgba[..., 1] = tint_rgb[1]
    aura_rgba[..., 2] = tint_rgb[2]
    aura_rgba[..., 3] = (aura_arr * strength).astype(np.uint8)
    aura_layer = Image.fromarray(aura_rgba, "RGBA").filter(ImageFilter.GaussianBlur(blur_radius))

    return Image.alpha_composite(aura_layer, img)


def add_rim_glow(img, tint_rgb, thickness=3, blur_radius=4, strength=0.9):
    """Colored glow hugging the silhouette edge - the 'his fit changed' cue
    that a flat multiply tint alone doesn't sell."""
    from PIL import ImageFilter

    alpha = img.split()[3]
    dilated = alpha.filter(ImageFilter.MaxFilter(thickness * 2 + 1))
    edge_ring = Image.eval(dilated, lambda a: a) 
    ring_arr = np.array(edge_ring).astype(int) - np.array(alpha).astype(int)
    ring_arr = np.clip(ring_arr, 0, 255).astype(np.uint8)

    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow_rgb = np.zeros((*ring_arr.shape, 4), dtype=np.uint8)
    glow_rgb[..., 0] = tint_rgb[0]
    glow_rgb[..., 1] = tint_rgb[1]
    glow_rgb[..., 2] = tint_rgb[2]
    glow_rgb[..., 3] = (ring_arr * strength).astype(np.uint8)
    glow_layer = Image.fromarray(glow_rgb, "RGBA").filter(ImageFilter.GaussianBlur(blur_radius))

    return Image.alpha_composite(glow_layer, img)


def tint_image(im, tint_rgb):
    arr = np.array(im).astype(float)
    rgb, alpha = arr[..., :3], arr[..., 3]
    skin = _skin_mask(arr[..., :3].astype(np.uint8))

    tint = np.array(tint_rgb, dtype=float) / 255.0
    tinted = rgb * tint
    out_rgb = np.where(skin[..., None], rgb, tinted)  # leave skin pixels untouched

    out = np.dstack([out_rgb, alpha]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def build(source_path, out_dir):
    im = Image.open(source_path).convert("RGB")
    arr = np.array(im)
    os.makedirs(out_dir, exist_ok=True)

    panel_idx = 0
    for (y0, y1), cols in zip(ROW_BANDS, COL_SETS):
        for (x0, x1) in cols:
            panel = arr[y0 + INSET:y1 - INSET, x0 + INSET:x1 - INSET]
            rgba_arr = _flood_remove_bg(panel)
            panel_img = Image.fromarray(rgba_arr, "RGBA")

            pose = POSE_MAP[panel_idx]
            for tier_name, tint_rgb in TINTS.items():
                if tint_rgb is None:
                    out_img = panel_img
                else:
                    out_img = tint_image(panel_img, tint_rgb)
                    # Rim glow only on Red Teamer. Ghost in the Wire drops it
                    # entirely - the airstrike brackets + matrix halo do the
                    # framing job cleanly without the outline muddying edges.
                    if tier_name == "red":
                        out_img = add_rim_glow(out_img, tint_rgb)
                out_img.save(f"{out_dir}/{pose}_{tier_name}.png")
            panel_idx += 1

    print(f"built {panel_idx} poses x {len(TINTS)} tiers -> {out_dir}")


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "sprite_source/original_spritesheet.png"
    build(source, "static/sprites/character")
