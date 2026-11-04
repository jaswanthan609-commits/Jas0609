import numpy as np, sys
W, H, FPS, DUR = 960, 540, 24, float(sys.argv[1]); N = 70
r = np.random.default_rng(3)
x0, y0 = r.uniform(0, W, N), r.uniform(0, H, N); vx, vy = r.uniform(-4, 4, N), r.uniform(-9, -2, N)
rad = r.uniform(0.8, 2.6, N); ph = r.uniform(0, 6.28, N); br = r.uniform(.25, .8, N)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
out = sys.stdout.buffer
for f in range(int(DUR * FPS)):
    t = f / FPS; img = np.zeros((H, W), np.float32)
    px = (x0 + vx * t + 10 * np.sin(t * .3 + ph)) % W; py = (y0 + vy * t) % H
    a = br * (0.5 + 0.5 * np.sin(t * .8 + ph))
    for i in range(N):
        x, y, R = px[i], py[i], rad[i] * 3
        x1, x2, y1, y2 = int(max(0, x - R * 3)), int(min(W, x + R * 3)), int(max(0, y - R * 3)), int(min(H, y + R * 3))
        if x2 <= x1 or y2 <= y1: continue
        img[y1:y2, x1:x2] += a[i] * np.exp(-((xx[y1:y2, x1:x2] - x) ** 2 + (yy[y1:y2, x1:x2] - y) ** 2) / (2 * (R / 2) ** 2))
    rgb = np.stack([img * 255, img * 200, img * 130], -1).clip(0, 255).astype(np.uint8)
    out.write(rgb.tobytes())
