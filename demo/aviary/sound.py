# Synthesised soundtrack for the aviary walk-in: breeze, footsteps, bridge, door, birds, waterfall, splash, music pad.
import numpy as np, wave, sys
SR = 48000; DUR = 42.0; N = int(SR * DUR)
rng = np.random.default_rng(7)
L = np.zeros(N); Rr = np.zeros(N)

def shaped_noise(n, lo, hi, tilt=0.0):
    x = rng.standard_normal(n); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR)
    g = ((f >= lo) & (f <= hi)).astype(float) * (np.maximum(f, 20) / 1000.0) ** tilt
    y = np.fft.irfft(X * g, n); return y / (np.abs(y).max() + 1e-9)

def env(n, a, r):
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e

def put(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR); j = min(N, i + len(sig))
    if i >= N or j <= i: return
    s = sig[: j - i] * gain; L[i:j] += s * np.sqrt((1 - pan) / 2); Rr[i:j] += s * np.sqrt((1 + pan) / 2)

def ramp(t0, t1, a, b, t):
    u = np.clip((t - t0) / (t1 - t0), 0, 1); return a + (b - a) * u * u * (3 - 2 * u)

T = np.arange(N) / SR
# ambience beds
breeze = shaped_noise(N, 80, 1200, -0.8) * (0.5 + 0.5 * np.sin(T * 0.4) ** 2)
put(breeze * ramp(9, 12.5, 0.10, 0.03, T), 0)
chan = shaped_noise(N, 300, 5000, -0.4) * (0.7 + 0.3 * np.sin(T * 3.1) * np.sin(T * 1.7))
put(chan * np.exp(-((T - 8.0) / 3.2) ** 2) * 0.10, 0, pan=-0.2)
fall = shaped_noise(N, 200, 9000, -0.2) * (0.8 + 0.2 * np.sin(T * 7.3))
put(fall * ramp(10.5, 26, 0.012, 0.075, T) * ramp(38, 42, 1, 0.7, T), 0, pan=0.25)

# footsteps
def step(kind):
    n = int(0.16 * SR); t = np.arange(n) / SR
    if kind == 'wood': s = np.sin(2 * np.pi * 140 * t) * np.exp(-t * 35) + 0.4 * shaped_noise(n, 200, 2500) * np.exp(-t * 60)
    elif kind == 'marble': s = 0.6 * shaped_noise(n, 1500, 7000) * np.exp(-t * 90) + 0.3 * np.sin(2 * np.pi * 220 * t) * np.exp(-t * 50)
    else: s = shaped_noise(n, 150, 3500, -0.5) * np.exp(-t * 28)
    return s
for k, t in enumerate(np.arange(0.4, 28.4, 0.56)):
    if 13.2 < t < 15.6 or 22.6 < t < 23.4: continue
    kind = 'wood' if 5.8 < t < 8.9 else 'marble' if (10.4 < t < 16 or 24.5 < t) else 'path' if t < 10.4 else 'grass'
    put(step(kind), t + rng.uniform(-0.02, 0.02), {'wood': 0.32, 'marble': 0.12, 'path': 0.13, 'grass': 0.08}[kind], pan=0.15 if k % 2 else -0.15)
# door slide
n = int(2.4 * SR); put(shaped_noise(n, 300, 3000, -0.6) * np.sin(np.linspace(0, np.pi, n)) ** 2, 8.4, 0.10)
put(step('marble') * 0.6, 10.8, 0.4)

# birds
def chirp(f0, f1, d, harm=0.2):
    n = int(d * SR); t = np.arange(n) / SR; f = np.linspace(f0, f1, n); ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + harm * np.sin(2 * ph)) * np.sin(np.pi * t / d) ** 2
def song(base):
    parts = []
    for _ in range(rng.integers(3, 7)):
        f0 = base * rng.uniform(0.85, 1.2); parts.append(chirp(f0, f0 * rng.uniform(0.7, 1.5), rng.uniform(0.04, 0.11))); parts.append(np.zeros(int(rng.uniform(0.03, 0.09) * SR)))
    return np.concatenate(parts)
t = 0.5
while t < DUR - 1:
    inside = t > 11
    put(song(rng.uniform(2600, 5200)), t, (0.05 if inside else 0.018) * rng.uniform(0.5, 1.2), pan=rng.uniform(-0.8, 0.8))
    t += rng.uniform(0.25, 0.7) if inside else rng.uniform(0.9, 2.0)
def squawk(d=0.45, f=700):
    n = int(d * SR); t = np.arange(n) / SR; fr = f * (1 + 0.15 * np.sin(2 * np.pi * 9 * t)) * np.linspace(1.1, 0.85, n)
    ph = 2 * np.pi * np.cumsum(fr) / SR; s = sum(np.sin(k * ph) / k for k in range(1, 9))
    s *= (0.6 + 0.4 * shaped_noise(n, 30, 300)); return s / np.abs(s).max() * env(n, 0.02, 0.15)
for tt, g, p in [(12.0, 0.07, -0.5), (16.4, 0.12, -0.6), (19.0, 0.06, 0.4), (25.0, 0.05, 0.6), (33.2, 0.045, 0.3), (40.2, 0.06, -0.2)]:
    put(squawk(rng.uniform(0.35, 0.55), rng.uniform(600, 900)), tt, g, p)
def whistle():
    return np.concatenate([chirp(1300, 2300, 0.35, 0.05), np.zeros(int(0.08 * SR)), chirp(2300, 1700, 0.28, 0.05)])
for tt, p in [(13.4, 0.5), (21.0, -0.5), (31.5, -0.3), (37.0, -0.4)]:
    put(whistle(), tt, 0.045, p)
def quack():
    n = int(0.22 * SR); t = np.arange(n) / SR; ph = 2 * np.pi * np.cumsum(np.linspace(330, 260, n)) / SR
    s = sum(np.sign(np.sin(k * ph)) * 0 + np.sin(k * ph) / k for k in range(1, 14)); X = np.fft.rfft(s); f = np.fft.rfftfreq(n, 1 / SR)
    X *= np.exp(-((f - 1200) / 700) ** 2) + 0.4 * np.exp(-((f - 2600) / 600) ** 2); s = np.fft.irfft(X, n); return s / np.abs(s).max() * env(n, 0.01, 0.06)
for tt in [24.2, 24.5, 27.6, 34.4]: put(quack(), tt, 0.06, 0.3)
# splash + gentle water movement
for tt in [30.25, 30.4]:
    n = int(0.9 * SR); x = np.arange(n) / SR; put(shaped_noise(n, 300, 8000, -0.3) * np.exp(-x * 6), tt, 0.16)
n = int(DUR * SR); put(shaped_noise(n, 400, 4000, -0.3) * (0.5 + 0.5 * np.sin(T * 1.6)) * ramp(30.4, 31.5, 0, 0.03, T), 0)

# music pad: Cmaj7 Am7 Fmaj7 G6
chords = [[261.6, 329.6, 392.0, 493.9], [220.0, 261.6, 329.6, 392.0], [174.6, 220.0, 261.6, 329.6], [196.0, 246.9, 293.7, 329.6]]
mus = np.zeros(N); cl = 5.25
for i in range(int(DUR / cl) + 1):
    t0 = i * cl; n = int((cl + 2.0) * SR); t = np.arange(n) / SR; e = np.minimum(1, t / 1.8) * np.clip((cl + 2.0 - t) / 2.0, 0, 1)
    s = np.zeros(n)
    for f in chords[i % 4]:
        for d in (-0.6, 0.6): s += np.sin(2 * np.pi * (f / 2 + d) * t) + 0.25 * np.sin(2 * np.pi * f * t + d)
    i0 = int(t0 * SR); j = min(N, i0 + n); mus[i0:j] += (s * e)[: j - i0]
    for k, f in enumerate(chords[i % 4] + [chords[i % 4][1] * 2]):  # soft arpeggio pluck
        tt = t0 + 0.6 + k * 0.9
        m = int(1.6 * SR); x = np.arange(m) / SR; pl = (np.sin(2 * np.pi * f * 2 * x) + 0.3 * np.sin(2 * np.pi * f * 4 * x)) * np.exp(-x * 3.2)
        a = int(tt * SR); b = min(N, a + m)
        if a < N: mus[a:b] += 1.6 * pl[: b - a]
mus /= np.abs(mus).max()
put(mus * ramp(0, 3, 0, 0.11, T) * ramp(36, 42, 1, 1.25, T), 0)

out = np.stack([L, Rr], 1); fade = np.ones(N); fade[: int(0.8 * SR)] = np.linspace(0, 1, int(0.8 * SR)); fade[-int(1.2 * SR):] = np.linspace(1, 0, int(1.2 * SR))
out *= fade[:, None]; out /= np.abs(out).max() / 0.85
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'aviary.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())
print('ok')
