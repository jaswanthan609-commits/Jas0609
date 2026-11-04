import sys, json, subprocess, numpy as np, soundfile as sf
sys.path.insert(0, '.')
from core.audio import sampler as S
from core.audio.sfx import SR
K = 2.2; D = 'styles/engraving/demo'; V = '/home/claude/Jas0609/demo/voice/out'
E = json.load(open(f'{D}/out/sonia/events.json')); DUR = E['dur'] * K
# --- score: slow D major lullaby, 4 bars of 8 s, repeated
prog = [('D3', ['D4', 'F#4', 'A4', 'D5']), ('B2', ['B3', 'D4', 'F#4', 'B4']), ('G2', ['G3', 'B3', 'D4', 'G4']), ('A2', ['A3', 'C#4', 'E4', 'A4'])]
ev = []; t = 0.5; bar = 8.0; k = 0
while t < DUR - 4:
    root, ch = prog[k % 4]
    ev.append((t, 'cellos', root, bar + 1.0, .32, -.2, .55))
    ev.append((t, 'violins', ch[2] if k % 2 else ch[1], bar + 1.0, .22, .3, .28))
    for j, n in enumerate([ch[0], ch[1], ch[2], ch[3], ch[2], ch[1]]):
        ev.append((t + j * 1.3 + (0.1 if j % 2 else 0), 'piano', n, 3.0, .30 - .03 * (j % 3), -.3 + .12 * j, .8))
    if k % 2 == 1: ev.append((t + 7.0, 'piano', ch[3].replace('4','5').replace('5','5'), 4.0, .2, .4, .5))
    t += bar; k += 1
ev.append((t, 'piano', 'D4', 6.0, .25, 0, .8)); ev.append((t, 'piano', 'A4', 6.0, .2, .2, .6))
mus = S.render(ev, dur=DUR + 1)
mus = S.room(mus, size=.7, mix=.35)
mus = mus / (np.abs(mus).max() + 1e-9) * 0.5
n = len(mus); vo = np.zeros((n, 2), np.float32); mask = np.zeros(n, np.float32)
def place(path, t0):
    a = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True).stdout
    x = np.frombuffer(a, np.float32); i = int(t0 * SR); j = min(n, i + len(x))
    vo[i:j] += x[:j - i, None] * 0.95; mask[i:j] = 1
place(f'{V}/sleep2/en-GB-SoniaNeural/intro.mp3', 0.3)
for e in E['ev']:
    if e['type'] == 'vo': place(f"{V}/sleep/en-GB-SoniaNeural/{e['id']}.mp3", e['t'] * K)
kk = int(.6 * SR); sm = np.convolve(mask, np.ones(kk) / kk, 'same')
mix = vo + mus * (0.55 - 0.35 * sm)[:, None]
sf.write(f'{D}/out/sonia/mix.wav', mix, SR); print('ok', DUR)
