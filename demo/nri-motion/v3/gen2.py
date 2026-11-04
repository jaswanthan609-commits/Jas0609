"""NRI Money motion explainer v2: 3D icons (Fluent Emoji, MIT), flying notes and coins, word-timed captions.
usage: python gen2.py <voice_dir with 0..5.mp3 + .json word timings>"""
import json, html, sys, subprocess, random
VD = sys.argv[1]
# scene timing from the clips (lead 0.25 s, tail 0.35 s)
st, du, words, KWS = [], [], [], []
t = 0.0
for i in range(6):
    d = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f'{VD}/{i}.mp3']).decode())
    st.append(round(t, 3)); du.append(round(d + 0.6, 3))
    for w in json.load(open(f'{VD}/{i}.json')): words.append((t + 0.25 + w['t'], w['d'], w['w']))
    sw = [(t + 0.25 + w['t'], w['w'].lower().strip('.,?!:;')) for w in json.load(open(f'{VD}/{i}.json'))]
    KWS.append(sw)
    t += d + 0.6
D = round(t, 2)
# audio: concat with gaps
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y'] + sum([['-i', f'{VD}/{i}.mp3'] for i in range(6)], []) + ['-filter_complex',
    ''.join(f'[{i}:a]aresample=44100,adelay=250|250,apad=pad_dur=0.35[a{i}];' for i in range(6)) + ''.join(f'[a{i}]' for i in range(6)) + 'concat=n=6:v=0:a=1[o]',
    '-map', '[o]', '-ac', '2', 'assets/vo.wav'], check=True)
# captions: group words into chunks of <= 5 words, break at punctuation
caps, cur = [], []
for w in words:
    cur.append(w)
    if len(cur) >= 5 or w[2][-1:] in '.,?!:;':
        caps.append(cur); cur = []
if cur: caps.append(cur)
cap_html = []
for k, c in enumerate(caps):
    a = c[0][0]; b = (caps[k + 1][0][0] if k + 1 < len(caps) else c[-1][0] + c[-1][1] + 0.5)
    b = min(b, c[-1][0] + c[-1][1] + 0.8)
    spans = ''.join(f'<span class="w" data-t="{round(w[0] - a, 3)}">{html.escape(w[2])}</span> ' for w in c)
    cap_html.append(f'<div id="cap{k}" class="clip cap" data-start="{round(a, 3)}" data-duration="{round(max(0.3, b - a), 3)}" data-track-index="5"><div class="capbox">{spans}</div></div>')
I = lambda n, cls='', id_='': f'<img {f"id=\"{id_}\" " if id_ else ""}class="ico {cls}" src="assets/icons/{n if n.endswith(".png") else n + "_3d.png"}">'
def note(id_, cls='inr', label='₹500'):
    return f'<div id="{id_}" class="note-b {cls}"><span class="nsym">{label[0]}</span><span class="nval">{label}</span></div>'
R = random.Random(7)
rain = ''.join(f'<div class="rain" id="rn{k}" style="left:{R.randint(20, 1880)}px">' + (I('coin', 'rc') if k % 3 == 0 else note(f'rnn{k}', 'inr' if k % 2 else 'usd', '₹500' if k % 2 else '$100')) + '</div>' for k in range(26))
def scene(i, inner): return f'<div id="s{i}" class="clip scene" data-start="{st[i]}" data-duration="{du[i]}" data-track-index="1"><div class="cam" id="cam{i}">{inner}</div></div>'
S = []
S.append(scene(0, f'''<div id="rainbox">{rain}</div>
<div class="center col">
  <div class="row big"><span id="h-nre" class="g">NRE</span><span id="h-vs" class="vs">vs</span><span id="h-nro" class="o">NRO</span></div>
  <div id="h-sub" class="sub">3 rules every NRI should know</div>
</div>
{I('airplane', 'plane', 'plane0')}'''))
S.append(scene(1, f'''<div class="hdr"><span class="num">1</span><span>Where the money comes from</span></div>
<div class="lane" id="lane1">
  <div class="src">{I('woman_office_worker_3d_medium.png', 'big-ico', 'wk')}{I('globe_showing_americas', 'mini', 'gl1')}<div class="lbl">Salary abroad</div></div>
  <div class="flowzone" id="fz1">{note('n1a', 'usd', '$100')}{note('n1b', 'gbp', '£50')}{note('n1c', 'usd', '$100')}</div>
  <div class="acct g-bd" id="nre1">{I('bank', 'acc-ico')}<div><b class="g">NRE</b><span>money from abroad</span></div></div>
</div>
<div class="lane" id="lane2">
  <div class="src row3">{I('house_with_garden', 'mid-ico', 'ic-rent')}{I('chart_increasing', 'mid-ico', 'ic-div')}{I('receipt', 'mid-ico', 'ic-pen')}<div class="lbl">Rent · Dividends · Pension</div></div>
  <div class="flowzone" id="fz2">{note('n2a')}{note('n2b')}{note('n2c')}</div>
  <div class="acct o-bd" id="nro1">{I('bank', 'acc-ico')}<div><b class="o">NRO</b><span>money from India</span></div></div>
</div>'''))
S.append(scene(2, f'''<div class="hdr"><span class="num">2</span><span>Tax in India on ₹10,000 of interest</span></div>
<div class="taxgrid">
  <div class="tcol g-bd" id="t-nre"><b class="g">NRE</b><div class="stack" id="stk-nre">{''.join(note(f"sn{k}") for k in range(5))}</div>{I('check_mark_button', 'badge', 'chk')}<div class="tv g">Tax: ₹0</div></div>
  <div class="tcol o-bd" id="t-nro"><b class="o">NRO</b><div class="stack" id="stk-nro">{''.join(note(f"so{k}") for k in range(5))}</div>{I('scissors', 'badge sc', 'scis')}<div class="tv r">TDS: ₹<span id="tds">0</span></div><small>30% + 4% cess = 31.2%</small></div>
</div>
<div id="treaty" class="tip late">{I('light_bulb', 'tip-ico')}<div>A tax treaty (DTAA) can lower it: give your bank a Tax Residency Certificate + Form 10F.<br><small>Surcharge also applies if total income is above ₹50 lakh.</small></div></div>'''))
S.append(scene(3, f'''<div class="hdr"><span class="num">3</span><span>Sending money back abroad</span></div>
<div class="rep">
  <div class="rcol g-bd" id="r-nre"><b class="g">NRE</b>{I('infinity', 'inf-ico', 'inf')}<div>Fully repatriable</div><small>principal + interest</small>{I('money_with_wings', 'wing', 'wing')}</div>
  <div class="rcol o-bd late" id="r-nro"><b class="o">NRO</b>{I('money_bag', 'bag-ico', 'bag')}<div class="meter"><div id="mfill" class="mfill o-bg"></div></div><div class="money">$<span id="usd">0</span></div><div>per financial year, after tax</div>
    <div class="row tight"><div class="doc" id="f15a">{I('page_facing_up', 'doc-ico')}15CA</div><div class="doc" id="f15b">{I('page_facing_up', 'doc-ico')}15CB</div></div></div>
</div>
{I('airplane_departure', 'plane2', 'plane3')}'''))
S.append(scene(4, f'''<div class="center col">
  <div class="kicker">{I('warning', 'kick-ico')} One catch</div>
  <div class="row mid"><span id="c-a">Tax free in India</span></div>
  <div class="row mid"><span id="neq" class="o">≠</span></div>
  <div class="row mid strike-wrap"><span id="c-b">tax free everywhere</span><div id="strike" class="strike"></div></div>
  <div id="c-us" class="us">{I('globe_showing_americas', 'us-ico', 'usg')}{I('magnifying_glass_tilted_left', 'mag', 'mag')}<div>Live in the US? NRE interest still goes on your US tax return.</div></div>
</div>'''))
S.append(scene(5, f'''<div class="hdr"><span class="num">✓</span><span>Check the official sources</span></div>
<div class="srcwrap">{I('ledger', 'led', 'led')}
<ul class="srcs">
<li id="sr1">RBI Master Direction: Deposits and Accounts · rbi.org.in</li>
<li id="sr2">RBI: NRO remittance up to USD 1 million a year · rbi.org.in</li>
<li id="sr3">Income Tax Dept: TDS for non-residents · incometax.gov.in</li>
<li id="sr4">IRS: US citizens and residents abroad · irs.gov</li>
</ul></div>
<div id="disc" class="disc">Education only, not financial or tax advice. Follow for part 2.</div>'''))
def kw(i, w, n=0, off=0.0):
    hits = [a for a, x in KWS[i] if x == w]
    return round(hits[min(n, len(hits) - 1)] + off, 3) if hits else None
JS = f'''
const tl = gsap.timeline({{ paused: true }});
const S = {json.dumps(st)}, DU = {json.dumps(du)}, DUR = {D};
const at = (i, o) => S[i] + o;
const fly = (sel, x0, x1, t, dur = 1.3) => tl.fromTo(sel, {{ x: x0, opacity: 0, rotation: -8 }}, {{ keyframes: [{{ opacity: 1, duration: 0.12 }}, {{ x: x1, rotation: 6, duration: dur, ease: 'power1.inOut' }}, {{ opacity: 0, scale: 0.6, duration: 0.15 }}] }}, t);
tl.fromTo('#grid', {{ backgroundPosition: '0px 0px' }}, {{ backgroundPosition: '-480px -240px', duration: DUR, ease: 'none' }}, 0);
tl.fromTo('#glow', {{ x: -300, y: -120 }}, {{ x: 380, y: 160, duration: DUR, ease: 'sine.inOut' }}, 0);
S.forEach((s, i) => {{
  tl.fromTo('#cam' + i, {{ scale: 1 }}, {{ scale: 1.045, duration: DU[i], ease: 'none' }}, s);
  tl.fromTo('#cam' + i + ' > *:not(.late)', {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: 0.5, stagger: 0.08, ease: 'power3.out' }}, s + 0.02);
  if (i < S.length - 1) tl.to('#cam' + i, {{ opacity: 0, scale: 1.12, filter: 'blur(8px)', duration: 0.4, ease: 'power2.in' }}, s + DU[i] - 0.42);
  tl.fromTo('#s' + i + ' .ico:not(.rc)', {{ y: 0 }}, {{ y: -10, duration: 1.1, yoyo: true, repeat: Math.max(1, Math.floor(DU[i] / 1.1) - 1), ease: 'sine.inOut' }}, s + 0.6);
}});
// s0: money rain, title, plane
document.querySelectorAll('#rainbox .rain').forEach((el, k) => tl.fromTo(el, {{ y: -260 - (k % 5) * 90, rotation: (k * 37) % 60 - 30 }}, {{ y: 1250, rotation: (k * 53) % 120 - 60, duration: 4 + (k % 4), ease: 'none' }}, (k * 0.23) % 4));
tl.from('#h-nre', {{ x: -500, opacity: 0, duration: 0.6, ease: 'expo.out' }}, 0.2);
tl.from('#h-nro', {{ x: 500, opacity: 0, duration: 0.6, ease: 'expo.out' }}, 0.45);
tl.from('#h-vs', {{ scale: 3, opacity: 0, duration: 0.45, ease: 'back.out(2)' }}, 0.9);
tl.from('#h-sub', {{ clipPath: 'inset(0 100% 0 0)', duration: 1.0, ease: 'power2.inOut' }}, {kw(0,'three')});
tl.fromTo('#plane0', {{ x: -300, y: 120, rotation: -10 }}, {{ x: 2200, y: -60, rotation: -18, duration: 3.2, ease: 'power1.inOut' }}, {kw(0,'abroad')});
// s1
const k1 = {kw(1,'nre')}; fly('#n1a', 0, 520, k1); fly('#n1b', 0, 520, k1 + 0.5); fly('#n1c', 0, 520, k1 + 1.0);
tl.from('#nre1', {{ scale: 0.6, opacity: 0, duration: 0.5, ease: 'back.out(2)' }}, k1 - 0.2);
[[ '#ic-rent', {kw(1,'rent')} ], [ '#ic-div', {kw(1,'dividends')} ], [ '#ic-pen', {kw(1,'pension')} ]].forEach(([c, t]) => tl.from(c, {{ y: 40, scale: 0.3, opacity: 0, duration: 0.45, ease: 'back.out(2)' }}, t));
const k2 = {kw(1,'nro')}; tl.from('#nro1', {{ scale: 0.6, opacity: 0, duration: 0.5, ease: 'back.out(2)' }}, k2);
fly('#n2a', 0, 520, {kw(1,'rent')}); fly('#n2b', 0, 520, {kw(1,'dividends')}); fly('#n2c', 0, 520, {kw(1,'pension')});
tl.from('#lane2', {{ opacity: 0.2, duration: 0.01 }}, at(1, 0.01)); tl.to('#lane2', {{ opacity: 1, duration: 0.5 }}, k2 - 0.3);
// s2
['#stk-nre .note-b', '#stk-nro .note-b'].forEach((sel, j) => tl.from(sel, {{ y: -300, opacity: 0, rotation: -20, duration: 0.45, stagger: 0.12, ease: 'bounce.out' }}, j ? {kw(2,'nro')} : {kw(2,'nre')}));
tl.from('#chk', {{ scale: 0, rotation: -90, duration: 0.5, ease: 'back.out(3)' }}, {kw(2,'free')});
tl.fromTo('#scis', {{ x: 260, y: -80, rotation: 30, opacity: 0 }}, {{ x: 0, y: 0, rotation: -10, opacity: 1, duration: 0.7, ease: 'power3.out' }}, {kw(2,'deducts',0,-0.6)});
tl.to('#scis', {{ rotation: 10, duration: 0.18, yoyo: true, repeat: 5 }}, {kw(2,'deducts')});
tl.to('#stk-nro .note-b:nth-child(-n+2)', {{ x: 340, y: 160, rotation: 40, opacity: 0, duration: 0.9, stagger: 0.15, ease: 'power2.in' }}, {kw(2,'deducts',0,0.4)});
const tds = {{ v: 0 }}; tl.to(tds, {{ v: 3120, duration: 1.6, ease: 'power2.inOut', onUpdate: () => document.getElementById('tds').textContent = Math.round(tds.v).toLocaleString('en-IN') }}, {kw(2,'thirty')});
tl.from('#treaty', {{ opacity: 0, y: 40, duration: 0.6, ease: 'power3.out' }}, {kw(2,'treaty',0,-0.4)});
// s3
tl.fromTo('#inf', {{ rotation: -180, scale: 0.3 }}, {{ rotation: 0, scale: 1, duration: 0.9, ease: 'back.out(2)' }}, {kw(3,'nre')});
tl.fromTo('#wing', {{ x: -40, y: 40, opacity: 0 }}, {{ x: 260, y: -220, opacity: 1, duration: 2.2, ease: 'power1.inOut' }}, {kw(3,'freely',0,-0.6)});
const k3 = {kw(3,'nro')}; tl.from('#r-nro', {{ x: 80, opacity: 0, duration: 0.6, ease: 'power3.out' }}, k3);
tl.fromTo('#mfill', {{ scaleX: 0 }}, {{ scaleX: 1, duration: 2.2, ease: 'power2.out', transformOrigin: '0 50%' }}, {kw(3,'one',0,-0.4)});
const usd = {{ v: 0 }}; tl.to(usd, {{ v: 1000000, duration: 2.2, ease: 'power2.out', onUpdate: () => document.getElementById('usd').textContent = Math.round(usd.v).toLocaleString('en-US') }}, {kw(3,'one',0,-0.4)});
tl.from('#bag', {{ scale: 0, duration: 0.5, ease: 'back.out(3)' }}, k3 + 0.3);
tl.from('#f15a', {{ y: 80, rotation: -15, opacity: 0, duration: 0.45, ease: 'back.out(2)' }}, {kw(3,'fifteen',0,-0.2)});
tl.from('#f15b', {{ y: 80, rotation: 15, opacity: 0, duration: 0.45, ease: 'back.out(2)' }}, {kw(3,'fifteen',1,-0.2)});
tl.fromTo('#plane3', {{ x: -200, y: 60 }}, {{ x: 2100, y: -140, duration: 3.5, ease: 'power1.in' }}, {kw(3,'abroad')});
// s4
tl.from('#c-a', {{ y: 60, opacity: 0, duration: 0.6, ease: 'power3.out' }}, at(4, 1.0));
tl.from('#neq', {{ scale: 0, rotation: -45, duration: 0.5, ease: 'back.out(3)' }}, at(4, 2.2));
tl.from('#c-b', {{ y: 60, opacity: 0, duration: 0.6, ease: 'power3.out' }}, at(4, 2.6));
tl.fromTo('#strike', {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.5, ease: 'power2.inOut', transformOrigin: '0 50%' }}, {kw(4,'everywhere')});
tl.from('#c-us', {{ opacity: 0, y: 40, duration: 0.6 }}, {kw(4,'live',0,-0.2)});
tl.fromTo('#mag', {{ x: -60, y: 20 }}, {{ x: 30, y: -10, duration: 1.2, yoyo: true, repeat: 2, ease: 'sine.inOut' }}, at(4, 5.2));
// s5
['#sr1', '#sr2', '#sr3', '#sr4'].forEach((x, k) => tl.from(x, {{ x: -60, opacity: 0, duration: 0.45, ease: 'power3.out' }}, at(5, 0.4 + k * 0.35)));
tl.from('#disc', {{ opacity: 0, duration: 0.5 }}, at(5, 2.2));
// captions: box pops, each word lights up on its spoken time
document.querySelectorAll('.cap').forEach(c => {{ const a = +c.dataset.start; tl.from(c.querySelector('.capbox'), {{ y: 16, opacity: 0, scale: 0.94, duration: 0.16, ease: 'power2.out' }}, a);
  c.querySelectorAll('.w').forEach(w => tl.fromTo(w, {{ color: '#ffffff' }}, {{ color: '#ffb35c', duration: 0.08 }}, a + +w.dataset.t)); }});
window.__timelines['main'] = tl; tl.seek(0);
'''
CSS = open('style2.css').read()
page = f'''<!doctype html><html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width=1920, height=1080" />
<script src="assets/gsap.min.js"></script><style>{CSS}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{D}" data-width="1920" data-height="1080">
<div id="bg" class="clip" data-start="0" data-duration="{D}" data-track-index="0"><div id="grid"></div><div id="glow"></div><div id="brand">NRI MONEY GUIDE</div></div>
{''.join(S)}
{''.join(cap_html)}
<audio id="vo" class="clip" src="assets/vo.wav" data-start="0" data-duration="{D}" data-track-index="9"></audio>
</div>
<script>{JS}</script></body></html>'''
open('index.html', 'w').write(page); print('ok', D, len(caps))
