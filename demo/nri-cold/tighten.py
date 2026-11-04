import json, subprocess, numpy as np
w = json.load(open('cold.json'))
sr = 24000
raw = subprocess.run(['ffmpeg','-loglevel','error','-i','cold.mp3','-f','f32le','-ac','1','-ar',str(sr),'-'],capture_output=True).stdout
a = np.frombuffer(raw, np.float32).copy()
segs = []; out_w = []; pos = 0.0; cur = 0.0
# cut points inside long gaps
cuts = []
for i in range(len(w)-1):
    end = w[i]['t'] + w[i]['d']; gap = w[i+1]['t'] - end
    if gap > 0.42: cuts.append((end + 0.12, w[i+1]['t'] - 0.18))  # remove this span (keep 0.30 s)
removed = 0.0; pieces = []; last = 0.0
for s, e in cuts:
    pieces.append(a[int(last*sr):int(s*sr)]); last = e
pieces.append(a[int(last*sr):])
fade = int(.01*sr)
for p in pieces:
    if len(p) > 2*fade: p[:fade] *= np.linspace(0,1,fade); p[-fade:] *= np.linspace(1,0,fade)
b = np.concatenate(pieces)
def shift(t):
    return t - sum(e - s for s, e in cuts if e <= t + 1e-6)
for x in w: out_w.append({'w': x['w'], 't': round(shift(x['t']),3), 'd': x['d']})
json.dump(out_w, open('words.json','w'))
b.astype(np.float32).tofile('vo.f32')
subprocess.run(['ffmpeg','-y','-loglevel','error','-f','f32le','-ar',str(sr),'-ac','1','-i','vo.f32','-ar','48000','vo.wav'])
print(len(a)/sr, '->', len(b)/sr)
print(' '.join(f"{x['w']}@{x['t']:.2f}" for x in out_w))
