# Handoff — Cyber Viking added to the Defenders roster

New character, art included, plus a desktop launcher. Everything is inside this
folder; no absolute paths, nothing to download.

## Run it

```
python3 -m pip install -r requirements.txt
python3 app.py                 # http://127.0.0.1:5000
```

Or build a double-clickable launcher (macOS):

```
tools/install_launcher.sh
```

That puts `CyberGuy.app` on your Desktop. It clears the port, starts the server,
waits until it actually answers an HTTP request, then opens Chrome on it; closing
the Terminal window it opens stops the server. All paths are derived from where
this folder sits and which python3 you have, so it needs no editing — re-run it
if you move the project. `--name`, `--port`, `--dest-dir`, `--python` override
the defaults; `.venv/bin/python3` is picked up automatically if present.

## What changed

| File | Change |
| --- | --- |
| `roster.py` | One new `_character(...)` entry: Cyber Viking, Defenders, unlocks at Lv 20, `has_real_sprites=True` |
| `static/js/roster.js` | One `PORTRAIT_PATHS` entry pointing at his bust image |
| `static/js/app.js` | One `CHARACTER_SPRITES` entry, plus a `tiered` flag in the sprite-path line (see below) |
| `static/css/style.css` | Three-selector rule at the end of the file, opting his images out of `image-rendering: pixelated` |
| `static/sprites/cyber_viking/` | New folder, the art (see below) |
| `tools/` | New: the desktop launcher installer + the generic launch script it calls |
| `make_icon.py`, `static/img/` | New: the launcher's "CG" icon. Nothing in the app reads these — delete if unwanted |
| `README.md`, `PROJECT_STATE__3_.md` | Notes describing the above |

## The art

His art is an illustration, not a pixel spritesheet, so it doesn't follow the
`{pose}_{tier}.png` convention the generated sprites use:

- `portrait.png` (512²) — bust crop, used by the roster grid and detail overlay,
  where the box is square and the full 1:1.8 image would render ~54px wide
- `full.png` (600x800) — waist-up crop, used by the character card
- `cutout.png` (1536x2752) — full-res background-removed master. **Re-crop from
  this** rather than re-running background removal
- `source.jpg` — the original render, untouched

`cutout.png` and `source.jpg` are masters, not used at runtime — safe to delete
if you'd rather keep the folder small.

Three things about them worth knowing:

1. **They are stored pre-mirrored.** The app flips every portrait with CSS
   `transform: scaleX(-1)` (the left-facing source convention). This art carries
   readable HUD text, so the files are mirrored on disk and the CSS flip lands
   them the right way round. If you re-crop from `cutout.png`, note it is
   already mirrored too.
2. **One image serves all three tiers.** The sprite path in `app.js` normally
   appends `_neutral` / `_red` / `_green`, which would 404 on tiers 2 and 3 for a
   single image. The new `tiered: false` flag skips the suffix:
   `const tierPart = poseConfig.tiered === false ? "" : `_${cosmeticSuffix}`;`
   Existing characters don't set the flag, so their behaviour is unchanged.
   Drop in per-tier art later and remove the flag.
3. **The background is removed** (macOS Vision subject lifting) so he floats like
   the pixel sprites instead of sitting in a rectangle. Both derived files fade
   to transparent over the bottom 10-12%, where the original frame cut through
   his torso, so the cut dissolves instead of ending in a hard line.

## Not included

`data/` was left out — that's save data, not code. It's recreated on first run.
