#!/usr/bin/env python3
"""Premium demo GIFs — terminal + browser twin.
Apple/Linear grade: high contrast, generous whitespace, one accent, sharp type, no sticker overlays.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
W = 960

def load_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/Consola.ttf",
        "C:/Windows/Fonts/CascadiaMono.ttf",
        "C:/Windows/Fonts/CascadiaCode.ttf",
        "C:/Windows/Fonts/JetBrainsMono-Regular.ttf",
        "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf",
    ]
    for p in candidates:
        try:
            if Path(p).exists():
                return ImageFont.truetype(p, size)
        except: pass
    try: return ImageFont.truetype("DejaVuSansMono.ttf", size)
    except: return ImageFont.load_default()

F13 = load_font(13)
F12 = load_font(12)
F11 = load_font(11)
F10 = load_font(10)
F9 = load_font(9)
FB12 = load_font(12, bold=True)
FB13 = load_font(13, bold=True)

# Premium palette — not hacker green
BG = (18, 18, 20)        # #121214 deep grey, not pure black
BG_CHROME = (28, 28, 30) # chrome
TEXT = (241, 245, 249)
MUTED = (148, 163, 184)
DIM = (100, 116, 139)
AMBER = (245, 158, 11)
AMBER_SOFT = (251, 191, 36)
EMERALD = (52, 211, 153)
EMERALD_SOFT = (110, 231, 183)
RULE = (38, 38, 42)

def draw_terminal_frame(cmd_typed, show_output=False, cursor_on=True, show_legend=False):
    H = 520
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    # Chrome — minimal, rounded 10, subtle
    d.rounded_rectangle([0,0,W,26], radius=10, fill=BG_CHROME)
    d.ellipse([12,8,21,17], fill=(255,95,86))
    d.ellipse([28,8,37,17], fill=(255,189,46))
    d.ellipse([44,8,53,17], fill=(39,201,63))
    d.text((68,6), "Harsh — zsh — 80x24", font=F9, fill=(130,130,135))
    # Content with generous whitespace
    y = 46
    # Prompt — desaturated sage, not neon green
    d.text((20, y), "$", font=F13, fill=(140, 160, 140))
    d.text((34, y), cmd_typed, font=F13, fill=TEXT)
    if cursor_on and not show_output and cmd_typed:
        tw = d.textlength(cmd_typed, font=F13)
        d.rectangle([34+tw+2, y+1, 34+tw+8, y+16], fill=(200,200,200))
    y += 26
    if show_output:
        # Ingest section — muted label with rule
        d.text((20, y), "acme  ·  /tmp/causala-acme.db", font=F10, fill=DIM)
        y += 18
        # hairline
        d.rectangle([20, y, W-20, y+1], fill=RULE)
        y += 10
        # ingest lines — key muted, value white
        d.text((20, y), "ingest", font=F11, fill=DIM)
        d.text((70, y), "price → demand", font=F11, fill=TEXT)
        d.text((200, y), "0.82", font=F11, fill=MUTED)
        d.text((240, y), "finance-q3-review", font=F10, fill=DIM)
        d.text((W-80, y), "c85ba0a2", font=F10, fill=DIM)
        y += 18
        d.text((20, y), "ingest", font=F11, fill=DIM)
        d.text((70, y), "demand → margin", font=F11, fill=TEXT)
        d.text((200, y), "0.75", font=F11, fill=MUTED)
        d.text((240, y), "finance-q3-review", font=F10, fill=DIM)
        d.text((W-80, y), "a1b2c3d4", font=F10, fill=DIM)
        y += 24
        # Simulate header — bold, amber left rule accent, generous space above
        d.rectangle([20, y+2, 22, y+14], fill=AMBER)  # subtle rail
        d.text((30, y), "Simulate: price +3%", font=FB12, fill=TEXT)
        y += 22
        # Result 1 — demand
        # outcome name bold, value white, CI amber-muted
        d.text((30, y), "demand", font=FB12, fill=TEXT)
        d.text((110, y), "2.46%", font=F12, fill=TEXT)
        # CI as secondary, not primary
        ci_txt = "[1.985, 2.935]"
        d.text((170, y), ci_txt, font=F11, fill=MUTED)
        d.text((280, y), "conf 0.82", font=F10, fill=DIM)
        d.text((360, y), "audit", font=F10, fill=DIM)
        d.text((400, y), "cd98f5cc", font=F10, fill=AMBER_SOFT)
        y += 18
        # honest note — amber, but as inline with icon, not covering
        d.ellipse([30, y+5, 36, y+11], fill=AMBER)
        d.text((42, y), "thin data (n=4)  ·  CI width 0.95  ·  verify with upstream warehouse export", font=F10, fill=AMBER_SOFT)
        y += 16
        d.text((42, y), "cite finance-q3-review  ·  path price → demand", font=F10, fill=MUTED)
        y += 20
        # Result 2 — margin, lighter
        d.text((30, y), "margin", font=F11, fill=MUTED)
        d.text((110, y), "1.84%", font=F11, fill=MUTED)
        d.text((170, y), "[1.12, 2.56]", font=F11, fill=DIM)
        d.text((280, y), "audit 7a3e91b2", font=F10, fill=DIM)
        y += 24
        d.rectangle([20, y, W-20, y+1], fill=RULE)
        y += 10
        # Next — muted, with one green actionable
        d.text((20, y), "next", font=F10, fill=DIM)
        y += 14
        d.text((30, y), "causala tui", font=F10, fill=MUTED)
        d.text((180, y), "open the dashboard", font=F10, fill=DIM)
        y += 14
        d.text((30, y), "causala serve", font=F10, fill=EMERALD_SOFT)
        d.text((180, y), "open in browser  →  http://127.0.0.1:8000", font=F10, fill=EMERALD_SOFT)
        y += 14
        d.text((30, y), "causala audit --id cd98f5cc", font=F10, fill=MUTED)
        d.text((260, y), "hand regulators the receipt", font=F10, fill=DIM)
        # Bottom legend — premium pill bar, NOT overlay sticker
        if show_legend:
            # subtle border top
            d.rectangle([0, H-30, W, H-30+1], fill=RULE)
            legend = "Every simulate is cited  ·  Thin data widens the band  ·  LOOP"
            # pill
            pill_w = int(d.textlength(legend, font=F9) + 28)
            pill_x = (W - pill_w)//2
            d.rounded_rectangle([pill_x, H-24, pill_x+pill_w, H-8], radius=8, fill=(32,32,36), outline=RULE)
            d.ellipse([pill_x+8, H-20, pill_x+14, H-14], fill=AMBER)
            d.text((pill_x+18, H-20), legend, font=F9, fill=MUTED)
        else:
            d.text((20, H-18), "CAUSALA 0.3.0  ·  one process  ·  networkx + SQLite  ·  MIT", font=F9, fill=(70,75,85))
    else:
        if not cmd_typed:
            d.text((20, y+10), "Type causala quickstart to see a lever become a cited number.", font=F11, fill=DIM)
        d.text((20, H-18), "CAUSALA 0.3.0  ·  one process  ·  networkx + SQLite  ·  MIT", font=F9, fill=(70,75,85))
    return im

# Web frame — premium Monitor surface, dense but airy
BG_WEB = (2, 6, 23)
PANEL = (15, 23, 42)
BORDER = (30, 41, 59)
TEXT_L = (241,245,249)

def draw_web_frame(stage=0, progress=0.0):
    H = 540
    im = Image.new("RGB", (W, H), BG_WEB)
    d = ImageDraw.Draw(im)
    d.rectangle([0,0,W,42], fill=BG_WEB)
    d.rectangle([0,41,W,42], fill=BORDER)
    # Mark — dark bg, light ink, no white square (premium)
    # twin at 14,11 size 24
    # use light ink directly
    d.ellipse([16,14,27,28], outline=TEXT_L, width=1)
    d.ellipse([24,14,35,28], outline=TEXT_L, width=1)
    d.ellipse([24,20,26,22], fill=AMBER)
    d.text((44,10), "CAUSALA", font=FB13, fill=TEXT_L)
    d.text((44,24), "browser twin · point + 90% band + receipt", font=F9, fill=MUTED)
    d.rounded_rectangle([W-220,9, W-118,31], radius=10, fill=PANEL, outline=BORDER)
    d.text((W-210,15), "tenant  acme", font=F9, fill=MUTED)
    d.ellipse([W-96,16, W-89,23], fill=EMERALD)
    d.text((W-84,15), "api online" if stage<4 else "receipt", font=F9, fill=MUTED)
    pad = 12
    colw = (W - pad*4)//3
    cols = [pad, pad+colw+pad, pad+(colw+pad)*2]
    for idx, x in enumerate(cols):
        y0 = 52
        h = H - 62
        d.rounded_rectangle([x, y0, x+colw, y0+h], radius=12, fill=PANEL, outline=BORDER)
        hdr = ["INGEST · idempotent", "GRAPH + HONESTY · live twin", "RECEIPTS · hash chain"][idx]
        d.text((x+12, y0+10), hdr, font=F9, fill=MUTED)
        if idx==0:
            d.text((x+12, y0+28), "cause", font=F9, fill=MUTED)
            d.rounded_rectangle([x+12, y0+40, x+colw-12, y0+60], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+18, y0+46), "price", font=F11, fill=TEXT_L)
            d.text((x+12, y0+66), "effect", font=F9, fill=MUTED)
            d.rounded_rectangle([x+12, y0+78, x+colw-12, y0+98], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+18, y0+84), "demand", font=F11, fill=TEXT_L)
            d.text((x+12, y0+104), "confidence   source", font=F9, fill=MUTED)
            d.rounded_rectangle([x+12, y0+116, x+colw-70, y0+136], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+18, y0+122), "0.82", font=F11, fill=TEXT_L)
            d.rounded_rectangle([x+62, y0+116, x+colw-12, y0+136], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+68, y0+122), "finance-q3…", font=F11, fill=TEXT_L)
            btn_fill = AMBER if stage==1 else (248,250,252) if stage>=1 else PANEL
            btn_text = (10,10,10) if stage==1 else TEXT_L
            d.rounded_rectangle([x+12, y0+148, x+colw-12, y0+170], radius=8, fill=btn_fill, outline=BORDER if stage!=1 else AMBER)
            lab = "Ingest claim" if stage<1 else "✓ ingested c85ba0a2" if stage==1 else "Ingest claim"
            d.text((x+colw//2 - d.textlength(lab, font=F11)//2, y0+154), lab, font=F11, fill=btn_text)
            d.rectangle([x+12, y0+182, x+colw-12, y0+183], fill=BORDER)
            d.text((x+12, y0+190), "SIMULATE · do-calculus", font=F9, fill=MUTED)
            d.text((x+12, y0+204), "lever", font=F9, fill=MUTED)
            d.rounded_rectangle([x+12, y0+216, x+colw-12, y0+236], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+18, y0+222), "price", font=F11, fill=TEXT_L)
            d.text((x+12, y0+242), "delta %", font=F9, fill=MUTED)
            d.rounded_rectangle([x+12, y0+254, x+colw-12, y0+274], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+18, y0+260), "3", font=F11, fill=TEXT_L)
            sfill = TEXT_L if stage==3 else PANEL
            scol = BG_WEB if stage==3 else TEXT_L
            d.rounded_rectangle([x+12, y0+284, x+colw-12, y0+306], radius=8, fill=sfill, outline=BORDER)
            d.text((x+colw//2 - d.textlength("Simulate lever", font=F11)//2, y0+290), "Simulate lever", font=F11, fill=scol)
            if stage==3:
                r = int(6 + 6*abs(math.sin(progress*10)))
                d.ellipse([x+colw//2 + 52 - r, y0+296 - r, x+colw//2 +52 + r, y0+296 + r], outline=AMBER, width=1)
        elif idx==1:
            d.rounded_rectangle([x+12, y0+28, x+colw-12, y0+118], radius=8, fill=BG_WEB, outline=BORDER)
            px, py = x+60, y0+68
            dx, dy = x+colw//2, y0+68
            mx, my = x+colw-60, y0+68
            d.line([px+28, py, dx-28, dy], fill=(58,70,90), width=1)
            d.line([dx+28, dy, mx-28, my], fill=(58,70,90), width=1)
            d.polygon([dx-28, dy-4, dx-22, dy, dx-28, dy+4], fill=(58,70,90))
            d.polygon([mx-28, my-4, mx-22, my, mx-28, my+4], fill=(58,70,90))
            for (nx,ny,nm) in [(px,py,"price"),(dx,dy,"demand"),(mx,my,"margin")]:
                d.rounded_rectangle([nx-28, ny-14, nx+28, ny+14], radius=8, fill=(15,23,42), outline=BORDER)
                d.text((nx - d.textlength(nm, font=F11)//2, ny-5), nm, font=F11, fill=TEXT_L)
                if nm=="demand" and stage>=2:
                    d.ellipse([nx-32, ny-18, nx+32, ny+18], outline=AMBER, width=1)
            d.text((x+12, y0+100), "0.82 finance-q3   0.75 finance-q3", font=F9, fill=MUTED)
            d.text((x+colw//2 - d.textlength("Thin data widens 1.8×  ·  No claim, no edge.", font=F9)//2, y0+110), "Thin data widens 1.8×  ·  No claim, no edge.", font=F9, fill=(100,116,139))
            if stage>=3:
                ry = y0+130
                d.rounded_rectangle([x+12, ry, x+colw-12, ry+70], radius=8, fill=BG_WEB, outline=BORDER)
                d.text((x+18, ry+8), "demand", font=FB12, fill=TEXT_L)
                d.text((x+colw-12 - d.textlength("2.46%  [1.985, 2.935]", font=F11), ry+9), "2.46%  [1.985, 2.935]", font=F11, fill=TEXT_L)
                d.text((x+18, ry+24), "cite finance-q3-review · path price → demand · conf 0.82 · cd98f5cc", font=F9, fill=MUTED)
                d.rounded_rectangle([x+18, ry+38, x+colw-18, ry+58], radius=6, fill=(45,35,10), outline=(120,80,10))
                d.text((x+22, ry+44), "thin data (n=4) → wide CI width 0.95", font=F9, fill=AMBER_SOFT)
                if stage>=4:
                    d.text((x+18, ry+60), "margin  1.84%  [1.12, 2.56]  audit 7a3e91b2", font=F9, fill=MUTED)
            else:
                d.text((x+colw//2 - d.textlength("Simulate a lever to see point, band, and receipt.", font=F11)//2, y0+150), "Simulate a lever to see point, band, and receipt.", font=F11, fill=(100,116,139))
        else:
            d.rounded_rectangle([x+12, y0+28, x+colw-44, y0+48], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+18, y0+34), "cd98f5cc", font=F9, fill=MUTED)
            d.rounded_rectangle([x+colw-36, y0+28, x+colw-12, y0+48], radius=8, fill=PANEL, outline=BORDER)
            d.text((x+colw-32, y0+34), "Open", font=F9, fill=TEXT_L)
            d.rounded_rectangle([x+12, y0+54, x+colw-12, y0+76], radius=8, fill=PANEL, outline=BORDER)
            d.text((x+colw//2 - d.textlength("Verify chain   Recent", font=F9)//2, y0+60), "Verify chain   Recent", font=F9, fill=MUTED)
            if stage>=4:
                ry = y0+86
                d.rounded_rectangle([x+12, ry, x+colw-12, ry+90], radius=8, fill=BG_WEB, outline=BORDER)
                d.text((x+18, ry+8), "cd98f5cc", font=FB12, fill=TEXT_L)
                d.ellipse([x+colw-34, ry+10, x+colw-22, ry+22], fill=EMERALD)
                d.text((x+18, ry+24), "tenant acme · lever price 3% → demand 2.46", font=F9, fill=MUTED)
                d.text((x+18, ry+36), "[1.985, 2.935]", font=F9, fill=TEXT_L)
                d.text((x+18, ry+48), "prev 8843a1b2… · sig 9f3a…", font=F9, fill=MUTED)
                d.text((x+18, ry+60), 'path [{"cause":"price","effect":"demand"}]', font=F9, fill=MUTED)
                d.text((x+18, ry+72), "honest thin data (n=4) → wide CI", font=F9, fill=AMBER_SOFT)
                if progress>0.3:
                    d.ellipse([x+12-2, ry-2, x+colw-12+2, ry+90+2], outline=AMBER, width=1)
            else:
                d.text((x+colw//2 - d.textlength("No receipt selected.", font=F11)//2, y0+110), "No receipt selected.", font=F11, fill=(100,116,139))
                d.text((x+colw//2 - d.textlength("Simulate, then open the audit_id.", font=F9)//2, y0+126), "Simulate, then open the audit_id.", font=F9, fill=(100,116,139))
            d.text((x+12, y0+h-48), "engine  Causala 0.3.0 · networkx + SQLite", font=F9, fill=MUTED)
            d.text((x+12, y0+h-36), "audit   JSONL · prev_hash · HMAC-SHA256", font=F9, fill=MUTED)
            d.text((x+12, y0+h-24), "api     FastAPI · Bearer JWT · 20/min", font=F9, fill=MUTED)
            d.text((x+12, y0+h-12), "swap    Postgres / Neo4j / S3 later", font=F9, fill=MUTED)
    d.text((12, H-14), "CAUSALA · MIT · one process · causala quickstart · causala tui · causala serve", font=F9, fill=(100,116,139))
    d.text((W-12 - d.textlength("GitHub · README · Architecture", font=F9), H-14), "GitHub · README · Architecture", font=F9, fill=MUTED)
    return im

def save_gif(frames, path, fps=12, loop=0, palette=64):
    quantized = []
    for im in frames:
        q = im.quantize(colors=palette, method=2, dither=0)
        quantized.append(q)
    duration = int(1000/fps)
    quantized[0].save(path, save_all=True, append_images=quantized[1:], duration=duration, loop=loop, optimize=True)
    print(f"{path.name}: {len(frames)} frames, {fps}fps, {palette}c, {path.stat().st_size/1024:.1f}KB, {W}x{frames[0].height}")

frames_term = []
for i in range(10):
    frames_term.append(draw_terminal_frame("", show_output=False, cursor_on=(i%6<3)))
cmd = "causala quickstart"
for i in range(1, len(cmd)+1):
    for _ in range(2):
        frames_term.append(draw_terminal_frame(cmd[:i], show_output=False, cursor_on=True))
for _ in range(5):
    frames_term.append(draw_terminal_frame(cmd, show_output=False, cursor_on=True))
for _ in range(12):
    frames_term.append(draw_terminal_frame(cmd, show_output=True, cursor_on=False, show_legend=False))
for _ in range(72):
    frames_term.append(draw_terminal_frame(cmd, show_output=True, cursor_on=False, show_legend=True))
for _ in range(6):
    frames_term.append(draw_terminal_frame("", show_output=False, cursor_on=False))
save_gif(frames_term, DOCS / "demo.gif", fps=12, palette=64)

frames_web = []
def stage_for_frame(i, total=144):
    t = i/total*12
    if t < 1.0: return (0, t)
    if t < 2.5: return (1, (t-1)/1.5)
    if t < 4.0: return (1, 1.0)
    if t < 5.5: return (2, (t-4)/1.5)
    if t < 7.0: return (3, (t-5.5)/1.5)
    return (4, min(1.0, (t-7)/2))
for i in range(144):
    s, p = stage_for_frame(i)
    frames_web.append(draw_web_frame(stage=s, progress=p))
for _ in range(6):
    frames_web.append(draw_web_frame(stage=0, progress=0))
save_gif(frames_web, DOCS / "demo-web.gif", fps=12, palette=128)
DOCS.joinpath("demo-web.png").parent.mkdir(parents=True, exist_ok=True)
draw_web_frame(stage=4, progress=0.9).save(DOCS / "demo-web.png")
draw_terminal_frame(cmd, show_output=True, show_legend=True).save(DOCS / "demo.png")
print("done premium")
