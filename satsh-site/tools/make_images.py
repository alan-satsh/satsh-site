"""Genera las imágenes del sitio (vista previa social y favicon). Requiere Pillow y numpy.
   python tools/make_images.py"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "img")
FONT = next((p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
                         "/System/Library/Fonts/Helvetica.ttc") if os.path.exists(p)), None)
W, H = 1200, 630


def stars(img, n=420, seed=3):
    rng = np.random.default_rng(seed)
    d = ImageDraw.Draw(img)
    for _ in range(n):
        x, y, a = rng.integers(0, W), rng.integers(0, H), rng.uniform(.25, 1)
        r = rng.choice([0, 0, 0, 1])
        c = int(255 * a)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(c, c, c))


def spaced(d, xy, text, font, fill, tracking):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + tracking


def limb(img):
    """Horizonte de planeta (halo azul) en la parte baja."""
    cx, cy, R = W / 2, H + 1500, 1640
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot(xx - cx, yy - cy) - R
    glow = np.exp(-np.clip(d, 0, None) / 38.0) * (d > 0) * 0.55 + np.exp(-np.abs(d) / 3.0) * 0.8
    glow = np.where(d < 0, np.exp(-np.abs(d) / 70.0) * 0.12 + np.exp(-np.abs(d) / 3.0) * 0.8, glow)
    arr = np.asarray(img).astype(float)
    col = np.array([120, 170, 255.0])
    arr += glow[..., None] * col
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def moon(img, cx, cy, r, seed=5):
    rng = np.random.default_rng(seed)
    n = np.zeros((2 * r, 2 * r))
    for octave, amp in ((6, 1.0), (14, .55), (30, .3), (60, .15)):
        g = rng.random((octave, octave))
        n += amp * np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((2 * r, 2 * r), Image.BICUBIC)).astype(float) / 255
    n = (n - n.min()) / (n.max() - n.min())
    yy, xx = np.mgrid[-r:r, -r:r]
    rr = np.hypot(xx, yy) / r
    shade = np.clip(1.15 - 0.95 * ((xx + 0.45 * r) ** 2 + (yy + 0.4 * r) ** 2) ** .5 / (1.3 * r), 0, 1)
    tex = (0.55 + 0.45 * n) * shade
    rgb = np.stack([tex * 232, tex * 235, tex * 240], -1)
    alpha = np.clip((1 - rr) * r / 1.5, 0, 1)
    m = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8), "RGBA")
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6], fill=(200, 215, 255, 70))
    img.paste(Image.alpha_composite(img.convert("RGBA"), halo.filter(ImageFilter.GaussianBlur(26))).convert("RGB"))
    img.paste(m, (cx - r, cy - r), m)


def og(name, title, subtitle, with_moon):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    stars(img)
    if with_moon:
        moon(img, 900, 250, 190)
    else:
        img = limb(img)
    d = ImageDraw.Draw(img)
    big = ImageFont.truetype(FONT, 104)
    small = ImageFont.truetype(FONT, 26)
    spaced(d, (80, 330), title, big, (255, 255, 255), 14)
    spaced(d, (84, 470), subtitle, small, (200, 205, 215), 6)
    spaced(d, (84, 70), "SATSH", ImageFont.truetype(FONT, 22), (255, 255, 255), 9)
    img.save(os.path.join(OUT, name), optimize=True)


os.makedirs(OUT, exist_ok=True)
og("og-satsh.png", "SATSH", "SOFTWARE & SCIENCE PROJECTS", False)
og("og-lunagen.png", "LUNAGEN", "AGENT-BASED CULTURE SIMULATION", True)

with open(os.path.join(OUT, "..", "..", "favicon.svg"), "w", encoding="utf-8") as f:
    f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#000"/>'
            '<circle cx="32" cy="32" r="17" fill="none" stroke="#fff" stroke-width="3"/>'
            '<circle cx="39" cy="26" r="5" fill="#fff"/></svg>\n')
print("imágenes generadas en", OUT)
