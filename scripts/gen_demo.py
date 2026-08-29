#!/usr/bin/env python3
"""Premium demo GIFs for CAUSALA — terminal + web browser twin.
Generates docs/demo.gif (CLI, 80x24 terminal) and docs/demo-web.gif (browser, 3-col dashboard).
Specs: 960px, 12fps, 64 colors, under 2MB, 12s loop, hold final 6-7s, clean restart.
No screen recorder — reconstructed via PIL for deterministic output.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io, math

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
W = 960
# Try to load premium mono fonts, fallback to default
def load_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/Consola.ttf", "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/CascadiaMono.ttf", "C:/Windows/Fonts/CascadiaCode.ttf",
        "C:/Windows/Fonts/JetBrainsMono-Regular.ttf", "C:/Windows/Fonts/GeistMono-Regular.ttf",
        "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf",
    ]
    for p in candidates:
        try:
            if Path(p).exists():
                return ImageFont.truetype(p, size)
        except: pass
    try:
        return ImageFont.truetype("DejaVuSansMono.ttf", size)
    except:
        return ImageFont.load_default()

FONT_14 = load_font(14)
FONT_13 = load_font(13)
FONT_12 = load_font(12)
FONT_11 = load_font(11)
FONT_10 = load_font(10)
FONT_9 = load_font(9)
FONT_B14 = load_font(14, bold=True)
FONT_B13 = load_font(13, bold=True)

BG_TERM = (11, 11, 15)  # #0B0B0F near
BG_WEB = (2, 6, 23)     # #020617
PANEL = (15, 23, 42)
BORDER = (30, 41, 59)
MUTED = (148, 163, 184)
TEXT = (241, 245, 249)
AMBER = (245, 158, 11)
AMBER2 = (251, 191, 36)
EMERALD = (52, 211, 153)

def draw_terminal_frame(cmd_typed, show_output=False, hold_callout=False, cursor_on=True):
    H = 520
    im = Image.new("RGB", (W, H), BG_TERM)
    d = ImageDraw.Draw(im)
    # window chrome
    d.rounded_rectangle([0,0,W,28], radius=8, fill=(26,26,30))
    d.ellipse([12,9,22,19], fill=(255,95,86))
    d.ellipse([30,9,40,19], fill=(255,189,46))
    d.ellipse([48,9,58,19], fill=(39,201,63))
    d.text((72,7), "Harsh — zsh — 80×24", font=FONT_9, fill=(120,120,130))
    # terminal content
    y = 48
    # $ prompt line
    d.text((18, y), "$", font=FONT_13, fill=(120,180,120))
    # typed command
    tx = cmd_typed
    d.text((32, y), tx, font=FONT_13, fill=TEXT)
    if cursor_on and not show_output:
        # cursor block
        tw = d.textlength(tx, font=FONT_13)
        d.rectangle([32+tw+2, y+1, 32+tw+9, y+16], fill=(180,180,180))
    y += 22
    if show_output:
        # output block
        lines = [
            ("Tenant: acme  DB: /tmp/causala-acme.db", MUTED),
            ("  ingest price -> demand 0.82 cite finance-q3-review -> c85ba0a2", TEXT),
            ("  ingest demand -> margin 0.75 cite finance-q3-review -> a1b2c3d4", TEXT),
            ("", TEXT),
            ("Simulate: price +3% ->", (180,180,220)),
            ("  demand: 2.46%  [1.985, 2.935]  conf 0.82  audit cd98f5cc", TEXT),
            ("    thin data (n=4) -> wide CI width 0.95 — verify with upstream warehouse export", AMBER2),
            ("    cites: finance-q3-review  path: price -> demand", MUTED),
            ("  margin: 1.84%  [1.12, 2.56]  audit 7a3e91b2", TEXT),
            ("", TEXT),
            ("Next:", MUTED),
            ("  causala tui                                         # open the dashboard", MUTED),
            ("  causala serve                                       # open in browser → http://127.0.0.1:8000", EMERALD),
            ("  causala audit --id cd98f5cc                         # hand regulators the receipt", MUTED),
        ]
        for txt, col in lines:
            d.text((18, y), txt, font=FONT_12, fill=col)
            y += 16
        # callout
        if hold_callout:
            # amber callout pointing at CI
            bx, by = 520, 138
            d.rounded_rectangle([bx, by, bx+300, by+28], radius=8, fill=AMBER)
            d.text((bx+10, by+7), "← point + 90% CI + receipt", font=FONT_11, fill=(10,10,10))
            # also small footer hint
            d.text((18, H-22), "Every simulate is cited. Thin data widens the band.  •  LOOP", font=FONT_9, fill=(90,100,110))
    else:
        # when not yet output, show hint
        d.text((18, H-22), "CAUSALA 0.3.0 · one process · networkx + SQLite · MIT", font=FONT_9, fill=(70,80,95))
    return im

def draw_web_frame(stage=0, progress=0.0):
    """stage 0: blank ingest, 1: typing claim, 2: graph updated, 3: simulate, 4: receipt"""
    H = 540
    im = Image.new("RGB", (W, H), BG_WEB)
    d = ImageDraw.Draw(im)
    # top bar
    d.rectangle([0,0,W,44], fill=(2,6,23))
    d.rectangle([0,43,W,44], fill=BORDER)
    # mark
    d.rounded_rectangle([14,9,46,35], radius=7, fill=(248,250,252), outline=(226,232,240))
    # tiny twin mark inside
    d.ellipse([20,15,26,27], outline=(10,10,10), width=1)
    d.ellipse([28,15,34,27], outline=(10,10,10), width=1)
    d.ellipse([26,20,28,22], fill=AMBER)
    d.text((54,10), "CAUSALA", font=FONT_B13, fill=TEXT)
    d.text((54,24), "browser twin · point + 90% band + receipt", font=FONT_9, fill=MUTED)
    # tenant pill
    d.rounded_rectangle([W-220,10, W-120,32], radius=12, fill=PANEL, outline=BORDER)
    d.text((W-210,16), "tenant  acme", font=FONT_9, fill=MUTED)
    d.ellipse([W-96,17, W-89,24], fill=EMERALD)
    d.text((W-84,16), "api online" if stage<4 else "receipt", font=FONT_9, fill=MUTED)
    # 3 cols
    pad = 12
    colw = (W - pad*4)//3
    cols = [pad, pad+colw+pad, pad+(colw+pad)*2]
    # left: ingest + simulate
    for idx, x in enumerate(cols):
        y0 = 54
        h = H - 64
        d.rounded_rectangle([x, y0, x+colw, y0+h], radius=12, fill=PANEL, outline=BORDER)
        # header
        hdr = ["INGEST · idempotent", "GRAPH + HONESTY · live twin", "RECEIPTS · hash chain"][idx]
        d.text((x+12, y0+10), hdr, font=FONT_9, fill=MUTED)
        # content per col
        if idx==0:
            # ingest form
            d.text((x+12, y0+28), "cause", font=FONT_9, fill=MUTED)
            d.rounded_rectangle([x+12, y0+40, x+colw-12, y0+62], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+18, y0+46), "price" if stage>=0 else "", font=FONT_11, fill=TEXT)
            if stage==1 and progress<0.5:
                # cursor
                d.rectangle([x+18 + d.textlength("price", font=FONT_11)+2, y0+46, x+18 + d.textlength("price", font=FONT_11)+7, y0+58], fill=AMBER)
            d.text((x+12, y0+66), "effect", font=FONT_9, fill=MUTED)
            d.rounded_rectangle([x+12, y0+78, x+colw-12, y0+100], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+18, y0+84), "demand", font=FONT_11, fill=TEXT)
            d.text((x+12, y0+104), "confidence   source", font=FONT_9, fill=MUTED)
            d.rounded_rectangle([x+12, y0+116, x+colw-70, y0+138], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+18, y0+122), "0.82", font=FONT_11, fill=TEXT)
            d.rounded_rectangle([x+62, y0+116, x+colw-12, y0+138], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+68, y0+122), "finance-q3…", font=FONT_11, fill=TEXT)
            # button
            btn_fill = AMBER if stage==1 else (248,250,252) if stage>=1 else PANEL
            btn_text = (10,10,10) if stage==1 else TEXT
            d.rounded_rectangle([x+12, y0+148, x+colw-12, y0+172], radius=8, fill=btn_fill, outline=BORDER if stage!=1 else AMBER)
            lab = "Ingest claim" if stage<1 else "✓ ingested c85ba0a2" if stage==1 else "Ingest claim"
            d.text((x+colw//2 - d.textlength(lab, font=FONT_11)//2, y0+154), lab, font=FONT_11, fill=btn_text)
            # simulate form lower
            d.rectangle([x+12, y0+184, x+colw-12, y0+185], fill=BORDER)
            d.text((x+12, y0+192), "SIMULATE · do-calculus", font=FONT_9, fill=MUTED)
            d.text((x+12, y0+206), "lever", font=FONT_9, fill=MUTED)
            d.rounded_rectangle([x+12, y0+218, x+colw-12, y0+240], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+18, y0+224), "price", font=FONT_11, fill=TEXT)
            d.text((x+12, y0+244), "delta %", font=FONT_9, fill=MUTED)
            d.rounded_rectangle([x+12, y0+256, x+colw-12, y0+278], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+18, y0+262), "3", font=FONT_11, fill=TEXT)
            # sim button highlight stage 3
            sfill = TEXT if stage==3 else PANEL
            sfc = TEXT if stage==3 else MUTED
            scol = BG_WEB if stage==3 else TEXT
            d.rounded_rectangle([x+12, y0+288, x+colw-12, y0+312], radius=8, fill=sfill, outline=BORDER)
            d.text((x+colw//2 - d.textlength("Simulate lever", font=FONT_11)//2, y0+294), "Simulate lever", font=FONT_11, fill=scol)
            if stage==3:
                # pulse ring
                r = int(6 + 6*abs(math.sin(progress*10)))
                d.ellipse([x+colw//2 + 52 - r, y0+300 - r, x+colw//2 +52 + r, y0+300 + r], outline=AMBER, width=1)
        elif idx==1:
            # graph
            d.rounded_rectangle([x+12, y0+28, x+colw-12, y0+120], radius=8, fill=BG_WEB, outline=BORDER)
            # nodes
            # price -> demand -> margin
            px, py = x+60, y0+70
            dx, dy = x+colw//2, y0+70
            mx, my = x+colw-60, y0+70
            # edges
            d.line([px+28, py, dx-28, dy], fill=(58,70,90), width=1)
            d.line([dx+28, dy, mx-28, my], fill=(58,70,90), width=1)
            # arrowheads
            d.polygon([dx-28, dy-4, dx-22, dy, dx-28, dy+4], fill=(58,70,90))
            d.polygon([mx-28, my-4, mx-22, my, mx-28, my+4], fill=(58,70,90))
            for (nx,ny,nm) in [(px,py,"price"),(dx,dy,"demand"),(mx,my,"margin")]:
                d.rounded_rectangle([nx-28, ny-14, nx+28, ny+14], radius=8, fill=(15,23,42), outline=BORDER)
                d.text((nx - d.textlength(nm, font=FONT_11)//2, ny-5), nm, font=FONT_11, fill=TEXT)
                if nm=="demand" and stage>=2:
                    # highlight
                    d.ellipse([nx-32, ny-18, nx+32, ny+18], outline=AMBER, width=1)
            d.text((x+12, y0+102), "0.82 finance-q3   0.75 finance-q3", font=FONT_9, fill=MUTED)
            d.text((x+colw//2 - d.textlength("Thin data widens 1.8×  ·  No claim, no edge.", font=FONT_9)//2, y0+112), "Thin data widens 1.8×  ·  No claim, no edge.", font=FONT_9, fill=(100,116,139))
            # results
            if stage>=3:
                # demand result
                ry = y0+132
                d.rounded_rectangle([x+12, ry, x+colw-12, ry+72], radius=8, fill=BG_WEB, outline=BORDER)
                d.text((x+18, ry+8), "demand", font=FONT_B14, fill=TEXT)
                d.text((x+colw-12 - d.textlength("2.46%  [1.985, 2.935]", font=FONT_11), ry+10), "2.46%  [1.985, 2.935]", font=FONT_11, fill=TEXT)
                d.text((x+18, ry+26), "cite finance-q3-review · path price → demand · conf 0.82 · cd98f5cc", font=FONT_9, fill=MUTED)
                d.rounded_rectangle([x+18, ry+40, x+colw-18, ry+60], radius=6, fill=(245,158,11,40) if stage==3 else (15,23,42), outline=(245,158,11,60) if stage==3 else BORDER)
                # draw amber bg manually since PIL no alpha
                d.rounded_rectangle([x+18, ry+40, x+colw-18, ry+60], radius=6, fill=(45,35,10) if stage==3 else PANEL, outline=(120,80,10) if stage==3 else BORDER)
                d.text((x+22, ry+46), "thin data (n=4) → wide CI width 0.95", font=FONT_9, fill=AMBER2)
                if stage==3 and progress>0.6:
                    d.text((x+colw-74, ry+46), "← honest", font=FONT_9, fill=AMBER)
                if stage>=4:
                    d.text((x+18, ry+62), "margin  1.84%  [1.12, 2.56]  audit 7a3e91b2", font=FONT_9, fill=MUTED)
            else:
                d.text((x+colw//2 - d.textlength("Simulate a lever to see point, band, and receipt.", font=FONT_11)//2, y0+152), "Simulate a lever to see point, band, and receipt.", font=FONT_11, fill=(100,116,139))
        else:
            # receipts
            d.rounded_rectangle([x+12, y0+28, x+colw-44, y0+50], radius=8, fill=BG_WEB, outline=BORDER)
            d.text((x+18, y0+34), "cd98f5cc", font=FONT_9, fill=MUTED)
            d.rounded_rectangle([x+colw-36, y0+28, x+colw-12, y0+50], radius=8, fill=PANEL, outline=BORDER)
            d.text((x+colw-32, y0+34), "Open", font=FONT_9, fill=TEXT)
            d.rounded_rectangle([x+12, y0+56, x+colw-12, y0+78], radius=8, fill=PANEL, outline=BORDER)
            d.text((x+colw//2 - d.textlength("Verify chain   Recent", font=FONT_9)//2, y0+62), "Verify chain   Recent", font=FONT_9, fill=MUTED)
            if stage>=4:
                ry = y0+88
                d.rounded_rectangle([x+12, ry, x+colw-12, ry+92], radius=8, fill=BG_WEB, outline=BORDER)
                d.text((x+18, ry+8), "cd98f5cc", font=FONT_B14, fill=TEXT)
                d.ellipse([x+colw-34, ry+10, x+colw-22, ry+22], fill=EMERALD)
                d.text((x+18, ry+24), "tenant acme · lever price 3% → demand 2.46", font=FONT_9, fill=MUTED)
                d.text((x+18, ry+36), "[1.985, 2.935]", font=FONT_9, fill=TEXT)
                d.text((x+18, ry+48), "prev 8843a1b2… · sig 9f3a…", font=FONT_9, fill=MUTED)
                d.text((x+18, ry+60), 'path [{"cause":"price","effect":"demand"}]', font=FONT_9, fill=MUTED)
                d.text((x+18, ry+72), "honest thin data (n=4) → wide CI", font=FONT_9, fill=AMBER2)
                # pulse
                if progress>0.3:
                    d.ellipse([x+12-2, ry-2, x+colw-12+2, ry+92+2], outline=AMBER, width=1)
            else:
                d.text((x+colw//2 - d.textlength("No receipt selected.", font=FONT_11)//2, y0+112), "No receipt selected.", font=FONT_11, fill=(100,116,139))
                d.text((x+colw//2 - d.textlength("Simulate, then open the audit_id.", font=FONT_9)//2, y0+128), "Simulate, then open the audit_id.", font=FONT_9, fill=(100,116,139))
            # kvs footer
            d.text((x+12, y0+h-48), "engine  Causala 0.3.0 · networkx + SQLite", font=FONT_9, fill=MUTED)
            d.text((x+12, y0+h-36), "audit   JSONL · prev_hash · HMAC-SHA256", font=FONT_9, fill=MUTED)
            d.text((x+12, y0+h-24), "api     FastAPI · Bearer JWT · 20/min", font=FONT_9, fill=MUTED)
            d.text((x+12, y0+h-12), "swap    Postgres / Neo4j / S3 later", font=FONT_9, fill=MUTED)
    # footer
    d.text((12, H-14), "CAUSALA · MIT · one process · causala quickstart · causala tui · causala serve", font=FONT_9, fill=(100,116,139))
    d.text((W-12 - d.textlength("GitHub · README · Architecture", font=FONT_9), H-14), "GitHub · README · Architecture", font=FONT_9, fill=MUTED)
    return im

def save_gif(frames, path, fps=12, loop=0, palette=64):
    # quantize to palette
    # pillow's quantize per frame then combine
    # use first frame to get palette
    quantized = []
    for im in frames:
        q = im.quantize(colors=palette, method=2, dither=0)
        quantized.append(q)
    # duration ms per frame
    duration = int(1000/fps)
    quantized[0].save(path, save_all=True, append_images=quantized[1:], duration=duration, loop=loop, optimize=True)
    print(f"{path}: {len(frames)} frames, {fps}fps, {palette} colors, {path.stat().st_size/1024:.1f}KB, {W}x{frames[0].height}")

# Build terminal gif
frames_term = []
# phase: blank 0.8s
for i in range(10):
    frames_term.append(draw_terminal_frame("", show_output=False, cursor_on=(i%6<3)))
# type causala quickstart
cmd = "causala quickstart"
for i in range(1, len(cmd)+1):
    for _ in range(2):  # 2 frames per char ~ 12fps *0.16s per char
        frames_term.append(draw_terminal_frame(cmd[:i], show_output=False, cursor_on=True))
# hold cmd 0.4s
for _ in range(5):
    frames_term.append(draw_terminal_frame(cmd, show_output=False, cursor_on=True))
# show output instantly + hold 7s with callout last 4s
# first 1s without callout
for _ in range(12):
    frames_term.append(draw_terminal_frame(cmd, show_output=True, hold_callout=False, cursor_on=False))
# next 6s with callout
for _ in range(72):
    frames_term.append(draw_terminal_frame(cmd, show_output=True, hold_callout=True, cursor_on=False))
# loop back: 0.5s blank to make clean restart
for i in range(6):
    # fade to blank
    frames_term.append(draw_terminal_frame("", show_output=False, cursor_on=False))
save_gif(frames_term, DOCS / "demo.gif", fps=12, palette=64)

# Build web gif
frames_web = []
# stage progression: 0 blank, 1 ingest, 2 graph, 3 simulate, 4 receipt
# timeline 12s at 12fps = 144 frames
# 0-1s stage0, 1-2.5s stage1 typing, 2.5-4s stage1 done, 4-5.5s stage2 graph highlight, 5.5-7s stage3 simulate press, 7-12s stage4 receipt hold
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
# add 6 blank to loop cleanly
for _ in range(6):
    frames_web.append(draw_web_frame(stage=0, progress=0))
save_gif(frames_web, DOCS / "demo-web.gif", fps=12, palette=128)
# also save a PNG preview for README static fallback
DOCS.joinpath("demo-web.png").parent.mkdir(parents=True, exist_ok=True)
draw_web_frame(stage=4, progress=0.9).save(DOCS / "demo-web.png")
draw_terminal_frame(cmd, show_output=True, hold_callout=True).save(DOCS / "demo.png")
print("done")
