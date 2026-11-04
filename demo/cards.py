"""Self-made explainer cards for the NRI Money demo (stand-in for Pexels stock + charts)."""
from PIL import Image, ImageDraw, ImageFont
W, H = 1920, 1080
NAVY, INK, SAFF, GREEN, MUTED = (14, 27, 48), (240, 244, 250), (255, 153, 51), (64, 190, 120), (150, 165, 190)
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf"
def font(sz, bold=True): return ImageFont.truetype(F.format("-Bold" if bold else ""), sz)

def base(step=None):
    im = Image.new("RGB", (W, H), NAVY); d = ImageDraw.Draw(im)
    for i in range(H):  # soft vertical gradient
        d.line([0, i, W, i], fill=tuple(int(c + 14 * i / H) for c in NAVY))
    d.rectangle([0, 0, W, 14], fill=SAFF)
    d.text((80, 50), "NRI MONEY GUIDE", font=font(34), fill=SAFF)
    if step: d.text((W - 80, 50), step, font=font(34), fill=MUTED, anchor="ra")
    return im, d

def title():
    im, d = base()
    d.text((W / 2, 380), "NRE  vs  NRO", font=font(150), fill=INK, anchor="mm")
    d.text((W / 2, 540), "3 differences every NRI should know", font=font(60, False), fill=MUTED, anchor="mm")
    for i, (lab, col) in enumerate([("NRE", GREEN), ("NRO", SAFF)]):
        x = W / 2 - 330 + i * 660
        d.rounded_rectangle([x - 250, 680, x + 250, 860], 30, outline=col, width=8)
        d.text((x, 770), lab, font=font(90), fill=col, anchor="mm")
    return im

def compare(step, head, nre, nro):
    im, d = base(step)
    d.text((W / 2, 200), head, font=font(80), fill=INK, anchor="mm")
    for i, (lab, col, body) in enumerate([("NRE", GREEN, nre), ("NRO", SAFF, nro)]):
        x0 = 100 + i * 880
        d.rounded_rectangle([x0, 320, x0 + 840, 790], 36, fill=(24, 42, 70), outline=col, width=6)
        d.text((x0 + 420, 400), lab, font=font(84), fill=col, anchor="mm")
        y = 500
        for line in body:
            d.text((x0 + 420, y), line, font=font(50, False), fill=INK, anchor="mm"); y += 80
    return im

def note(head, lines):
    im, d = base("ONE CATCH")
    d.text((W / 2, 300), head, font=font(74), fill=SAFF, anchor="mm")
    y = 470
    for line in lines:
        d.text((W / 2, y), line, font=font(58, False), fill=INK, anchor="mm"); y += 95
    return im

def sources():
    im, d = base("SOURCES")
    d.text((120, 200), "Check these before you act", font=font(70), fill=INK)
    src = ["RBI Master Direction: Deposits and Accounts (rbi.org.in)",
           "RBI: Remittance from NRO accounts, USD 1 million/FY (rbi.org.in)",
           "Income Tax Dept: NRI interest and TDS (incometax.gov.in)",
           "IRS: worldwide income, FBAR and FATCA (irs.gov)"]
    y = 330
    for s in src:
        d.ellipse([125, y + 18, 145, y + 38], fill=SAFF)
        d.text((175, y), s, font=font(48, False), fill=INK); y += 110
    d.text((120, 800), "Education only, not financial or tax advice.", font=font(44, False), fill=MUTED)
    return im

def safe(im):
    bg, _ = base(); bg = Image.new("RGB", (W, H), NAVY); d = ImageDraw.Draw(bg)
    for i in range(H): d.line([0, i, W, i], fill=tuple(int(c + 14 * i / H) for c in NAVY))
    sm = im.resize((int(W * 0.84), int(H * 0.84)), Image.LANCZOS)
    bg.paste(sm, ((W - sm.width) // 2, (H - sm.height) // 2 - 40)); return bg

_save = Image.Image.save
Image.Image.save = lambda self, p, *a, **k: _save(safe(self), p, *a, **k)
if __name__ == "__main__":
    title().save("nri_0.png")
    compare("1 OF 3", "Where the money comes from", ["Money earned abroad", "and brought into India"], ["Money earned in India:", "rent, dividends, pension"]).save("nri_1.png")
    compare("2 OF 3", "Tax in India on interest", ["Tax free in India"], ["Taxable in India", "TDS 30% + surcharge + cess", "(a tax treaty can lower it)"]).save("nri_2.png")
    compare("3 OF 3", "Sending money back abroad", ["Fully repatriable:", "principal + interest"], ["Up to USD 1 million", "per financial year,", "after tax (Form 15CA/15CB)"]).save("nri_3.png")
    note("Tax free in India ≠ tax free everywhere", ["Your country of residence may still tax it.", "Example: US residents report NRE interest", "on their US tax return."]).save("nri_4.png")
    sources().save("nri_5.png")
