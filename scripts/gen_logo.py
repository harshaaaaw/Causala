"""Generate the final CAUSALA mark (concept A: Twin) as production assets.

Concept: "Two lenses, one decision." Two overlapping circles form a vesica (the twin);
a single amber node marks the decision point where cause becomes effect. Monochrome +
one amber accent, flat, geometric, Apple/Nvidia grade. Scales 16->256px.

Outputs (in docs/):
  logo.svg          light bg full lockup (icon + CAUSALA wordmark)
  logo-dark.svg     dark bg lockup (light ink)
  mark.svg          icon only, light bg, viewBox 0 0 32
  mark-dark.svg     icon only, dark bg, viewBox 0 0 32
  logo.png / logo-dark.png / mark.png / mark-dark.png   raster previews (8x supersample)
"""
from __future__ import annotations
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
SCALE = 8
INK_LIGHT = "#0b0c0e"
INK_DARK = "#f5f5f7"
AMBER = "#f59e0b"

# geometry in an 88-box (light/dark lockup). Tighter lens so it holds at 16px.
CX1, CX2, CY, R = 35.0, 53.0, 44.0, 15.0
DOT_R = 2.8
SW = 2.0
WORD_Y = 70.0


def vec_lockup(dark: bool) -> str:
    ink = INK_DARK if dark else INK_LIGHT
    return f'''<svg width="88" height="92" viewBox="0 0 88 92" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="CAUSALA mark">
  <g fill="none" stroke="{ink}" stroke-width="{SW}" stroke-linecap="round" stroke-linejoin="round" shape-rendering="geometricPrecision">
    <circle cx="{CX1}" cy="{CY}" r="{R}"/>
    <circle cx="{CX2}" cy="{CY}" r="{R}"/>
  </g>
  <circle cx="{CX2- (CX2-CX1)/2:.1f}" cy="{CY}" r="{DOT_R}" fill="{AMBER}"/>
  <text x="44" y="{WORD_Y}" text-anchor="middle" font-family="Inter, ui-sans-serif, system-ui, -apple-system, Helvetica, Arial" font-size="11" font-weight="700" letter-spacing="0.14em" fill="{ink}">CAUSALA</text>
</svg>'''


def vec_mark(dark: bool) -> str:
    ink = INK_DARK if dark else INK_LIGHT
    # normalized to 32 box: scale base 88 -> 32
    s = 32.0 / 88.0
    cx1, cx2, cy, r = CX1 * s, CX2 * s, CY * s, R * s
    dr = DOT_R * s
    sw = 2.0 * s
    dotx = (CX1 + CX2) / 2 * s
    return f'''<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="CAUSALA mark">
  <g fill="none" stroke="{ink}" stroke-width="{sw:.3f}" stroke-linecap="round" stroke-linejoin="round" shape-rendering="geometricPrecision">
    <circle cx="{cx1:.2f}" cy="{cy:.2f}" r="{r:.2f}"/>
    <circle cx="{cx2:.2f}" cy="{cy:.2f}" r="{r:.2f}"/>
  </g>
  <circle cx="{dotx:.2f}" cy="{cy:.2f}" r="{dr:.2f}" fill="{AMBER}"/>
</svg>'''


def raster_lockup(dark: bool, size=(176, 184)):
    """Rasterize lockup to PNG for preview (16x to read small-size legibility)."""
    ink = INK_DARK if dark else INK_LIGHT
    img = Image.new("RGBA", (size[0] * SCALE, size[1] * SCALE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    sw = int(round(SW * SCALE))
    # two circles
    for cx in (CX1 * SCALE, CX2 * SCALE):
        box = [int(round(cx - R * SCALE)), int(round(CY * SCALE - R * SCALE)),
               int(round(cx + R * SCALE)), int(round(CY * SCALE + R * SCALE))]
        d.ellipse(box, outline=ink, width=sw)
    dotx = (CX1 + CX2) / 2 * SCALE
    dbox = [int(round(dotx - DOT_R * SCALE)), int(round(CY * SCALE - DOT_R * SCALE)),
            int(round(dotx + DOT_R * SCALE)), int(round(CY * SCALE + DOT_R * SCALE))]
    d.ellipse(dbox, fill=AMBER)
    out = img.resize(size, Image.LANCZOS)
    return out


def main():
    os.makedirs(DOCS, exist_ok=True)
    # SVG sources of truth
    with open(os.path.join(DOCS, "logo.svg"), "w", encoding="utf-8") as f:
        f.write(vec_lockup(False))
    with open(os.path.join(DOCS, "logo-dark.svg"), "w", encoding="utf-8") as f:
        f.write(vec_lockup(True))
    with open(os.path.join(DOCS, "mark.svg"), "w", encoding="utf-8") as f:
        f.write(vec_mark(False))
    with open(os.path.join(DOCS, "mark-dark.svg"), "w", encoding="utf-8") as f:
        f.write(vec_mark(True))
    # PNG previews (lockup + mark, light/dark)
    raster_lockup(False).save(os.path.join(DOCS, "logo.png"))
    raster_lockup(True).save(os.path.join(DOCS, "logo-dark.png"))
    # remove the 3 exploration candidates + their pngs + explore boards to keep hygiene clean
    for n in ("a", "b", "c"):
        for ext in (".svg", ".png", "-dark.png"):
            p = os.path.join(DOCS, f"logo-{n}{ext}")
            if os.path.exists(p):
                os.remove(p)
    for board in ("logo-explore.html", "logo-exploration.html"):
        p = os.path.join(DOCS, board)
        if os.path.exists(p):
            os.remove(p)
    # small-size legibility preview (16, 24, 32)
    small = Image.new("RGBA", (3 * 24 * SCALE, 24 * SCALE), (0, 0, 0, 0))
    src = raster_lockup(False)
    for i, sz in enumerate((16, 24, 32)):
        small.paste(src.resize((sz * SCALE, sz * SCALE), Image.LANCZOS),
                    (i * 24 * SCALE, 0))
    small.resize((3 * 24, 24), Image.LANCZOS).save(os.path.join(DOCS, "logo-small.png"))
    print("final mark assets written: logo.svg logo-dark.svg mark.svg mark-dark.svg (+ png previews)")


if __name__ == "__main__":
    main()
