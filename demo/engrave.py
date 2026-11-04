"""Self-drawn copperplate-engraving style scenes (no stock images)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
W, H = 2400, 1350
rng = np.random.default_rng(7)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

def blank(top, bottom):  # sky tone gradient, darkness 0..1
    return np.tile(np.linspace(top, bottom, H, dtype=np.float32)[:, None], (1, W))

def mask(draw_fn):
    m = Image.new("L", (W, H), 0); draw_fn(ImageDraw.Draw(m)); return np.asarray(m, np.float32) / 255

def paint(t, m, tone, shade=0.0):
    # shade: vertical darkening inside the shape for volume
    val = tone + shade * (yy / H - 0.5)
    return t * (1 - m) + np.clip(val, 0, 1) * m

def ridge(base, amp, freq, seed):
    r = np.random.default_rng(seed); x = np.arange(W)
    y = base + sum(amp / (k + 1) * np.sin(x * freq * (k + 1) / W * 6.28 + r.uniform(0, 6)) for k in range(4))
    return mask(lambda d: d.polygon([(0, H)] + list(zip(x[::8], y[::8])) + [(W, H)], fill=255))

def glow(t, cx, cy, r, strength):
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return np.clip(t - strength * np.exp(-(d / r) ** 2), 0, 1)

def render(t, warm=False):
    """Turn a tone map into engraving lines on aged paper."""
    t = np.asarray(Image.fromarray((t * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)), np.float32) / 255
    t = t * 0.88
    s = 7.5
    def lines(coord, thick):
        f = np.abs((coord / s) % 1 - 0.5) * 2  # 0 at line centre, 1 between lines
        return np.clip((thick - f) * s * 0.5 + 0.5, 0, 1) * (thick > 0.02)
    ink = lines(yy, np.clip(t * 1.15, 0, 1))
    ink = np.maximum(ink, lines((xx + yy) * 0.707, np.clip((t - 0.5) * 1.4, 0, 1)))
    ink = np.maximum(ink, lines((xx - yy) * 0.707, np.clip((t - 0.75) * 1.8, 0, 1)))
    paper = np.array([236, 222, 192], np.float32) if not warm else np.array([240, 220, 180], np.float32)
    inkc = np.array([52, 36, 24], np.float32)
    noise = rng.normal(0, 1, (H // 4, W // 4)).astype(np.float32)
    noise = np.asarray(Image.fromarray(((noise + 3) * 40).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255 - 0.47
    vig = np.clip(1 - 0.55 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2.2, 0, 1)
    img = paper * (1 - ink[..., None]) + inkc * ink[..., None]
    img = img * (0.93 + 0.12 * noise[..., None]) * vig[..., None]
    im = Image.fromarray(img.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for i, w in ((40, 5), (56, 2)):
        d.rectangle([i, i, W - i, H - i], outline=(52, 36, 24), width=w)
    return im.resize((1920, 1080), Image.LANCZOS)

def stars(t, n=160, ymax=0.5):
    for _ in range(n):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H * ymax), rng.uniform(2, 5)
        t = glow(t, x, y, r, 0.9)
    return t

def buildings(t, base, seed, tone, roofs=True, cols=False):
    r = np.random.default_rng(seed); x = -50
    while x < W:
        w = r.uniform(140, 320); h = r.uniform(120, 330)
        top = base - h
        m = mask(lambda d: d.rectangle([x, top, x + w, H], fill=255))
        t = paint(t, m, tone)
        if roofs:
            m = mask(lambda d: d.polygon([(x - 15, top), (x + w / 2, top - h * 0.22), (x + w + 15, top)], fill=255))
            t = paint(t, m, tone + 0.08)
        for wx in np.arange(x + 30, x + w - 30, 60):  # windows
            for wy in np.arange(top + 30, base - 40, 80):
                if r.random() < 0.35:
                    m = mask(lambda d: d.rectangle([wx, wy, wx + 22, wy + 34], fill=255))
                    t = paint(t, m, 0.15 if r.random() < 0.4 else tone + 0.15)
        x += w + r.uniform(-20, 30)
    return t

def scene_moon():
    t = blank(0.78, 0.55); t = stars(t); t = glow(t, 1650, 330, 260, 0.45)
    t = paint(t, mask(lambda d: d.ellipse([1560, 240, 1740, 420], fill=255)), 0.05)
    t = paint(t, ridge(900, 90, 1.2, 1), 0.68); t = paint(t, ridge(1000, 60, 2, 2), 0.78)
    t = buildings(t, 1180, 3, 0.86)
    return render(t)

def scene_oven():
    t = blank(0.85, 0.75)
    t = paint(t, mask(lambda d: d.rectangle([0, 1050, W, H], fill=255)), 0.62)  # floor
    t = paint(t, mask(lambda d: d.rounded_rectangle([600, 300, 1800, 1100], 40, fill=255)), 0.7, 0.2)  # oven body
    for row in range(330, 1080, 60):  # bricks
        off = 0 if (row // 60) % 2 else 50
        for bx in range(600 + off, 1800, 100):
            t = paint(t, mask(lambda d: d.line([bx, row, bx, row + 60], fill=255, width=6)), 0.9)
        t = paint(t, mask(lambda d: d.line([600, row, 1800, row], fill=255, width=6)), 0.9)
    t = paint(t, mask(lambda d: d.pieslice([900, 560, 1500, 1160], 180, 360, fill=255)), 0.9)  # arch
    t = paint(t, mask(lambda d: d.rectangle([900, 860, 1500, 1050], fill=255)), 0.9)
    t = glow(t, 1200, 980, 230, 0.95); t = glow(t, 1200, 900, 520, 0.35)
    for i in range(7):  # flames
        cx = 980 + i * 70
        t = paint(t, mask(lambda d: d.polygon([(cx - 35, 1040), (cx, 860 - (i % 3) * 40), (cx + 35, 1040)], fill=255)), 0.02)
    for lx in range(950, 1460, 90):  # logs
        t = paint(t, mask(lambda d: d.ellipse([lx, 1020, lx + 110, 1055], fill=255)), 0.8)
    return render(t, warm=True)

def scene_river():
    t = blank(0.6, 0.35); t = glow(t, 600, 300, 400, 0.3)
    t = paint(t, ridge(700, 50, 1.5, 4), 0.62)
    t = buildings(t, 780, 9, 0.7, roofs=True)
    water = mask(lambda d: d.rectangle([0, 780, W, H], fill=255))
    t = paint(t, water, 0.45)
    t = np.where(water > 0, np.clip(t + 0.12 * np.sin(yy / 6 + np.sin(xx / 60) * 2), 0, 1), t)
    br = mask(lambda d: d.rectangle([0, 600, W, 700], fill=255))
    t = paint(t, br, 0.75)
    for ax in range(150, W, 420):  # bridge arches
        t = paint(t, mask(lambda d: d.ellipse([ax, 650, ax + 300, 950], fill=255)), 0.45)
        t = paint(t, mask(lambda d: d.rectangle([ax, 800, ax + 300, 950], fill=255)), 0.45)
    t = np.where(water > 0, np.clip(t + 0.12 * np.sin(yy / 6 + np.sin(xx / 60) * 2), 0, 1), t)
    t = paint(t, mask(lambda d: d.polygon([(1300, 1080), (1750, 1080), (1680, 1150), (1370, 1150)], fill=255)), 0.85)
    t = paint(t, mask(lambda d: d.line([1520, 1080, 1520, 860], fill=255, width=10)), 0.85)
    t = paint(t, mask(lambda d: d.polygon([(1530, 870), (1530, 1060), (1690, 1060)], fill=255)), 0.25)
    return render(t)

def scene_lamps():
    t = blank(0.72, 0.62)
    t = paint(t, mask(lambda d: d.rectangle([1500, 200, 2150, 800], fill=255)), 0.3)  # window to night sky
    t = stars(t, 0) if False else t
    t = paint(t, mask(lambda d: d.rectangle([1500, 200, 2150, 800], outline=255, width=30)), 0.8)
    t = paint(t, mask(lambda d: d.line([1825, 200, 1825, 800], fill=255, width=20)), 0.8)
    t = paint(t, mask(lambda d: d.ellipse([1600, 300, 1700, 400], fill=255)), 0.05)  # moon in window
    t = paint(t, mask(lambda d: d.rectangle([0, 950, W, H], fill=255)), 0.55)  # table
    t = paint(t, mask(lambda d: d.line([0, 950, W, 950], fill=255, width=14)), 0.8)
    t = glow(t, 1420, 740, 230, 0.8); t = glow(t, 1420, 760, 650, 0.3)
    t = paint(t, mask(lambda d: d.ellipse([650, 820, 1250, 1010], fill=255)), 0.7, 0.5)  # clay lamp body
    t = paint(t, mask(lambda d: d.polygon([(1180, 870), (1420, 850), (1430, 920), (1200, 960)], fill=255)), 0.7, 0.5)
    t = paint(t, mask(lambda d: d.ellipse([880, 840, 1000, 880], fill=255)), 0.85)  # filling hole
    t = paint(t, mask(lambda d: d.arc([520, 820, 720, 960], 90, 270, fill=255, width=26)), 0.7)  # handle
    t = paint(t, mask(lambda d: d.polygon([(1395, 855), (1415, 660), (1440, 855)], fill=255)), 0.0)
    return render(t, warm=True)

def scene_street():
    t = blank(0.55, 0.35); t = glow(t, 1200, 900, 700, 0.3)  # pale dawn glow low in the sky
    t = paint(t, ridge(820, 40, 1.3, 5), 0.6)
    road = mask(lambda d: d.polygon([(0, H), (1050, 820), (1350, 820), (W, H)], fill=255))
    t = paint(t, road, 0.4)
    for i in range(1, 16):
        y = 820 + (H - 820) * (i / 15) ** 1.8
        t = paint(t, mask(lambda d: d.line([0, y, W, y], fill=255, width=3)), 0.75) * road + t * (1 - road)
    for side in (0, 1):
        for i in range(7):
            k = 0.15 + i / 7.0
            x = 1050 - 1100 * k if side == 0 else 1350 + 1100 * k
            h = 900 * k; w = 15 + 90 * k; base = 820 + (H - 820) * k * 0.9
            t = paint(t, mask(lambda d: d.rectangle([x - w / 2, base - h, x + w / 2, base], fill=255)), 0.55, 0.3)
            t = paint(t, mask(lambda d: d.rectangle([x - w * 0.8, base - h - 20 * k - 10, x + w * 0.8, base - h], fill=255)), 0.75)
    cx, cy = 1250, 1030  # cart
    t = paint(t, mask(lambda d: d.polygon([(cx - 260, cy - 120), (cx + 260, cy - 120), (cx + 220, cy - 30), (cx - 220, cy - 30)], fill=255)), 0.75)
    for wx in (cx - 150, cx + 150):
        t = paint(t, mask(lambda d: d.ellipse([wx - 90, cy - 90, wx + 90, cy + 90], outline=255, width=16)), 0.85)
        for a in range(0, 180, 45):
            v = np.deg2rad(a)
            t = paint(t, mask(lambda d: d.line([wx - 85 * np.cos(v), cy - 85 * np.sin(v), wx + 85 * np.cos(v), cy + 85 * np.sin(v)], fill=255, width=7)), 0.85)
    return render(t)

if __name__ == "__main__":
    import sys
    for name in sys.argv[1:]:
        globals()["scene_" + name]().save(f"img_{name}.jpg", quality=90)
        print(name)
