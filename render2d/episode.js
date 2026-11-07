// Glow-up Shorts: one episode of an original cartoon series, drawn in SVG and timed with GSAP.
// ?ep=<url-encoded JSON> describes the episode (see facepipe/glowup.py). window.frame(t) seeks the paused
// timeline to t seconds; window.DURATION is the episode length. Everything is deterministic for a seed.
/* global gsap */
const ep = Object.assign({
  name: 'Gopal', day: 1, days_total: 30, glow: 0, glow_before: 0, meter: 'WEDDING READY',
  premise: "30 DAYS TO HIS SISTER'S WEDDING", title: 'HE SET AN ALARM', place: 'bedroom', sign: '', sign_good: true,
  beats: [], comment: null, ask: 'What should he fix tomorrow?', seed: 1, duration: 20,
}, JSON.parse(new URLSearchParams(location.search).get('ep') || '{}'));

const NS = 'http://www.w3.org/2000/svg';
const stage = document.getElementById('stage');
let s0 = (ep.seed * 9301 + 49297) % 233280 || 7;
const rnd = () => ((s0 = (s0 * 16807) % 2147483647) / 2147483647);
function el(tag, attrs = {}, parent = stage, text) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text;
  parent.appendChild(e); return e;
}
const g = ep.glow;                 // 0 = day 1 slob, 1 = wedding-ready
const mess = 1 - g;

// ---------- set: each episode happens where its change happens (bedroom, bathroom, gym, ...) ----------
const defs = el('defs');
const vig = el('radialGradient', { id: 'vig', cx: .5, cy: .55, r: .75 }, defs);
el('stop', { offset: .6, 'stop-color': '#000', 'stop-opacity': 0 }, vig);
el('stop', { offset: 1, 'stop-color': '#000', 'stop-opacity': .55 }, vig);
const room = el('g', { id: 'room' });
let clock = null, ring = null;   // the alarm clock lives in the bedroom
function wallFloor(top, bottom, floor, floorLines = '#000') {
  const id = 'wall' + Math.round(rnd() * 1e6);
  const gr = el('linearGradient', { id, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  el('stop', { offset: 0, 'stop-color': top }, gr); el('stop', { offset: 1, 'stop-color': bottom }, gr);
  el('rect', { x: 0, y: 0, width: 1080, height: 1920, fill: `url(#${id})` }, room);
  el('rect', { x: 0, y: 1400, width: 1080, height: 520, fill: floor }, room);
  for (let y = 1430; y < 1920; y += 70) el('rect', { x: 0, y, width: 1080, height: 4, fill: floorLines, opacity: .12 }, room);
}
// a prop held across both hands (barbell, razor, phone...) is drawn after the character: see heldProp below
const PLACES = {
  bedroom() {
    wallFloor(g < .5 ? '#3a3550' : '#4f6d8c', g < .5 ? '#2a263a' : '#3d566f', g < .5 ? '#5b4636' : '#8a6a4a');
    // wallpaper stripes
    for (let x = 0; x < 1080; x += 90) el('rect', { x, y: 0, width: 45, height: 1400, fill: '#fff', opacity: .03 }, room);
    // window with the time of day
    const win = el('g', {}, room);
    el('rect', { x: 640, y: 330, width: 330, height: 380, rx: 14, fill: '#5a3d2a' }, win);
    el('rect', { x: 660, y: 350, width: 290, height: 340, fill: g < .3 ? '#ffb347' : '#8fd3ff' }, win);    // he wakes at 2 pm on day 1
    el('circle', { cx: 880, cy: 430, r: 46, fill: '#fff6c8', opacity: .9 }, win);
    el('rect', { x: 800, y: 350, width: 10, height: 340, fill: '#5a3d2a' }, win);
    el('rect', { x: 660, y: 515, width: 290, height: 10, fill: '#5a3d2a' }, win);
    // poster
    el('rect', { x: 110, y: 380, width: 220, height: 290, rx: 8, fill: '#c0392b', transform: 'rotate(-4 220 525)' }, room);
    el('text', { x: 220, y: 545, 'text-anchor': 'middle', class: 'ui', 'font-size': 64, fill: '#fff', transform: 'rotate(-4 220 525)' }, room, 'LEVEL 99');
    // bed
    el('rect', { x: 40, y: 1180, width: 520, height: 230, rx: 26, fill: '#6b4a32' }, room);
    el('rect', { x: 50, y: 1130, width: 500, height: 110, rx: 40, fill: g < .5 ? '#9a9aa8' : '#f4efe6' }, room);
    el('ellipse', { cx: 130, cy: 1135, rx: 80, ry: 40, fill: '#e8e4dc' }, room);
    // mess: pizza box, socks, cans, clothes pile (fewer as he glows up)
    const MESS = [
      () => { el('rect', { x: 700, y: 1600, width: 200, height: 40, rx: 4, fill: '#d8a85a', transform: 'rotate(8 800 1620)' }, room);
              el('text', { x: 800, y: 1630, 'text-anchor': 'middle', class: 'ui', 'font-size': 26, fill: '#a33', transform: 'rotate(8 800 1620)' }, room, 'PIZZA'); },
      () => { el('ellipse', { cx: 180, cy: 1560, rx: 120, ry: 40, fill: '#41506a' }, room); el('ellipse', { cx: 230, cy: 1530, rx: 80, ry: 35, fill: '#7a3e3e' }, room); },
      () => { for (const x of [600, 640]) { el('rect', { x, y: 1460, width: 34, height: 60, rx: 6, fill: '#c0392b' }, room); el('rect', { x, y: 1460, width: 34, height: 10, fill: '#ccc' }, room); } },
      () => { el('path', { d: 'M 920 1700 q 30 -40 60 0 q -30 20 -60 0', fill: '#eee' }, room); el('path', { d: 'M 120 1760 q 40 -30 70 5', stroke: '#ddd', 'stroke-width': 18, fill: 'none', 'stroke-linecap': 'round' }, room); },
      () => { for (let i = 0; i < 4; i++) el('circle', { cx: 420 + i * 60 + rnd() * 20, cy: 1720 + rnd() * 60, r: 18, fill: '#e6e2d6' }, room); },
    ];
    MESS.slice(0, Math.round(mess * MESS.length)).forEach(f => f());
    if (g >= .5) {   // a plant and a rug once he starts caring
      el('ellipse', { cx: 540, cy: 1700, rx: 380, ry: 90, fill: '#b5523b', opacity: .9 }, room);
      el('rect', { x: 930, y: 1300, width: 90, height: 110, rx: 10, fill: '#c97b4a' }, room);
      for (let i = 0; i < 7; i++) el('ellipse', { cx: 975 + Math.cos(i) * 40, cy: 1260 - i * 12, rx: 22, ry: 55, fill: '#3f8f4f', transform: `rotate(${-40 + i * 13} 975 1300)` }, room);
    }
    // alarm clock prop (used by the 'alarm' action)
    clock = el('g', { id: 'clock', transform: 'translate(150 1075)', opacity: ep.beats.some(b => b.action === 'alarm') ? 1 : 0 }, room);
    el('circle', { cx: 0, cy: 0, r: 52, fill: '#e74c3c', stroke: '#222', 'stroke-width': 8 }, clock);
    el('circle', { cx: 0, cy: 0, r: 38, fill: '#fff' }, clock);
    el('line', { x1: 0, y1: 0, x2: 0, y2: -26, stroke: '#222', 'stroke-width': 6, 'stroke-linecap': 'round' }, clock);
    el('line', { x1: 0, y1: 0, x2: 18, y2: 6, stroke: '#222', 'stroke-width': 6, 'stroke-linecap': 'round' }, clock);
    for (const sx of [-1, 1]) el('circle', { cx: sx * 38, cy: -50, r: 16, fill: '#f1c40f', stroke: '#222', 'stroke-width': 6 }, clock);
    ring = el('g', { opacity: 0 }, clock);
    for (const sx of [-1, 1]) for (const k of [0, 1]) el('path', { d: `M ${sx * (70 + k * 22)} -30 q ${sx * 14} 30 0 60`, stroke: '#fff', 'stroke-width': 7, fill: 'none', 'stroke-linecap': 'round' }, ring);
  },
  bathroom() {
    wallFloor('#bfe6e0', '#9fd3cb', '#e9efe9', '#6aa');
    for (let x = 0; x < 1080; x += 90) el('rect', { x, y: 0, width: 3, height: 1400, fill: '#fff', opacity: .6 }, room);
    for (let y = 0; y < 1400; y += 90) el('rect', { x: 0, y, width: 1080, height: 3, fill: '#fff', opacity: .6 }, room);
    el('rect', { x: 90, y: 330, width: 260, height: 330, rx: 20, fill: '#dff6ff', stroke: '#8aa', 'stroke-width': 10 }, room);   // mirror
    el('path', { d: 'M 760 300 L 760 380 q 0 30 30 30 L 860 410', stroke: '#9aa', 'stroke-width': 18, fill: 'none', 'stroke-linecap': 'round' }, room);  // shower pipe
    el('ellipse', { cx: 880, cy: 420, rx: 60, ry: 24, fill: '#9aa' }, room);
    for (let i = 0; i < 9; i++) el('line', { x1: 840 + i * 10, y1: 450, x2: 820 + i * 14, y2: 620 + rnd() * 80, stroke: '#7cc8ff', 'stroke-width': 5, opacity: .7 }, room);
    el('path', { d: 'M 680 280 L 680 1400', stroke: '#fff', 'stroke-width': 8 }, room);
    for (let i = 0; i < 5; i++) el('path', { d: `M ${960 + i * 20} 280 q -20 560 0 1120`, stroke: '#f2a7c3', 'stroke-width': 40, fill: 'none', opacity: .8 }, room);  // curtain
    el('rect', { x: 120, y: 760, width: 200, height: 26, rx: 8, fill: '#fff' }, room);   // shelf + soap
    el('rect', { x: 150, y: 720, width: 60, height: 40, rx: 12, fill: '#ffd400' }, room); el('rect', { x: 240, y: 700, width: 40, height: 60, rx: 8, fill: '#6c5ce7' }, room);
  },
  gym() {
    wallFloor('#4a4f5a', '#2f333b', '#3b3b3b');
    el('rect', { x: 0, y: 760, width: 1080, height: 26, fill: '#ff8a3d' }, room);
    for (const x of [140, 940]) el('rect', { x: x - 14, y: 900, width: 28, height: 520, fill: '#aaa' }, room);   // rack
    for (const x of [100, 900]) for (let k = 0; k < 3; k++) el('circle', { cx: x + 40, cy: 1460 - k * 40, r: 70 - k * 12, fill: '#222', stroke: '#555', 'stroke-width': 6 }, room);
    el('text', { x: 540, y: 560, 'text-anchor': 'middle', class: 'ui', 'font-size': 120, fill: '#fff', opacity: .12 }, room, 'NO PAIN');
  },
  shop() {
    wallFloor('#efe6da', '#d8cbb8', '#b99a77');
    el('rect', { x: 60, y: 520, width: 960, height: 14, rx: 7, fill: '#666' }, room);   // clothes rail
    const cols = ['#1f8a8a', '#e17055', '#6c5ce7', '#fdcb6e', '#00b894', '#d63031', '#0984e3', '#e84393', '#2d3436'];
    for (let i = 0; i < 9; i++) { const x = 90 + i * 105;
      el('path', { d: `M ${x + 40} 527 l 0 20`, stroke: '#666', 'stroke-width': 5 }, room);
      el('path', { d: `M ${x} 560 l 25 -18 l 30 0 l 25 18 l -12 30 l -8 -6 l 0 260 l -70 0 l 0 -260 l -8 6 z`, fill: cols[i] }, room); }
    el('rect', { x: 860, y: 1000, width: 170, height: 400, rx: 16, fill: '#dff6ff', stroke: '#8a6a4a', 'stroke-width': 12 }, room);   // mirror
    el('text', { x: 540, y: 330, 'text-anchor': 'middle', class: 'ui', 'font-size': 90, fill: '#c0392b' }, room, 'SALE 50%');
  },
  kitchen() {
    wallFloor('#f6e3b4', '#e8cf95', '#7a5a3c');
    for (let x = 0; x < 1080; x += 60) for (let y = 820; y < 1060; y += 60) el('rect', { x: x + 2, y: y + 2, width: 56, height: 56, fill: '#fff', opacity: .5 }, room);
    el('rect', { x: 0, y: 1060, width: 1080, height: 340, fill: '#a0522d' }, room); el('rect', { x: 0, y: 1040, width: 1080, height: 30, fill: '#ddd' }, room);
    el('rect', { x: 780, y: 360, width: 240, height: 680, rx: 20, fill: '#e8eef2', stroke: '#9aa', 'stroke-width': 8 }, room);   // fridge
    el('rect', { x: 990, y: 480, width: 12, height: 120, rx: 6, fill: '#9aa' }, room);
    el('rect', { x: 120, y: 960, width: 200, height: 80, rx: 10, fill: '#555' }, room); el('ellipse', { cx: 220, cy: 950, rx: 120, ry: 22, fill: '#777' }, room);   // pot
    for (let i = 0; i < 3; i++) el('path', { d: `M ${180 + i * 40} 900 q 20 -40 0 -80 q -20 -40 0 -80`, stroke: '#fff', 'stroke-width': 8, fill: 'none', opacity: .6 }, room);
  },
  barber() {
    wallFloor('#2d3e50', '#1d2a38', '#e9e3cf', '#000');
    for (let y = 1400; y < 1920; y += 80) for (let x = (y / 80) % 2 ? 0 : 80; x < 1080; x += 160) el('rect', { x, y, width: 80, height: 80, fill: '#222', opacity: .8 }, room);
    el('rect', { x: 200, y: 300, width: 680, height: 520, rx: 30, fill: '#dff6ff', stroke: '#c9a227', 'stroke-width': 16 }, room);   // mirror
    for (const x of [90, 990]) { el('rect', { x: x - 22, y: 360, width: 44, height: 400, rx: 22, fill: '#fff' }, room);
      for (let k = 0; k < 6; k++) el('path', { d: `M ${x - 22} ${380 + k * 64} l 44 -30 l 0 24 l -44 30 z`, fill: k % 2 ? '#d63031' : '#0984e3' }, room); }
  },
  outside() {
    wallFloor('#8fd3ff', '#cdeeff', '#7bbf5a', '#2d6a2d');
    el('circle', { cx: 880, cy: 300, r: 90, fill: '#fff6c8' }, room);
    for (const [x, s] of [[120, 1], [330, .8], [800, 1.1]]) { el('rect', { x: x - 20 * s, y: 1000, width: 40 * s, height: 400, fill: '#6b4a32' }, room);
      el('circle', { cx: x, cy: 960, r: 150 * s, fill: '#3f8f4f' }, room); }
    el('path', { d: 'M 380 1920 L 500 1400 L 580 1400 L 700 1920 Z', fill: '#d8c8a0' }, room);
  },
};
(PLACES[ep.place] || PLACES.bedroom)();

// ---------- character: original design, glow-up level g ----------
const SKIN = '#c68642', HAIR = '#1b1410';
const ch = el('g', { id: 'char' });
const body = el('g', {}, ch);
const bellyRx = 205 - 70 * g;
el('rect', { x: 540 - 150 + 25 * g, y: 1520, width: 70, height: 230, rx: 30, fill: g < .6 ? '#2d3e50' : '#f2efe6' }, body);   // legs
el('rect', { x: 540 + 80 - 25 * g, y: 1520, width: 70, height: 230, rx: 30, fill: g < .6 ? '#2d3e50' : '#f2efe6' }, body);
for (const x of [540 - 160 + 25 * g, 540 + 70 - 25 * g]) el('ellipse', { cx: x + 45, cy: 1755, rx: 62, ry: 26, fill: '#222' }, body);  // feet
const shirt = g < .6 ? '#e9e3cf' : '#1f8a8a';      // stained vest -> kurta
el('ellipse', { cx: 540, cy: 1360, rx: bellyRx, ry: 240, fill: shirt }, body);
if (g < .6) for (let i = 0; i < 5; i++) el('circle', { cx: 470 + rnd() * 150, cy: 1300 + rnd() * 160, r: 12 + rnd() * 16, fill: '#a0703a', opacity: .55 * (1 - g / .6) }, body);
if (g >= .6) { el('path', { d: 'M 540 1150 L 540 1500', stroke: '#e8c547', 'stroke-width': 8, 'stroke-dasharray': '4 26' }, body);
               el('path', { d: 'M 470 1150 q 70 60 140 0', stroke: '#e8c547', 'stroke-width': 10, fill: 'none' }, body); }
// arms
const armL = el('g', { id: 'armL' }, ch), armR = el('g', { id: 'armR' }, ch);
el('rect', { x: 540 - bellyRx - 20, y: 1200, width: 70, height: 250, rx: 35, fill: shirt }, armL);
el('circle', { cx: 540 - bellyRx + 15, cy: 1450, r: 38, fill: SKIN }, armL);
el('rect', { x: 540 + bellyRx - 50, y: 1200, width: 70, height: 250, rx: 35, fill: shirt }, armR);
el('circle', { cx: 540 + bellyRx - 15, cy: 1450, r: 38, fill: SKIN }, armR);
if (g < .4) {   // glued to his phone
  el('rect', { x: 540 + bellyRx - 50, y: 1380, width: 70, height: 120, rx: 12, fill: '#111', stroke: '#555', 'stroke-width': 5 }, armR);
  el('rect', { x: 540 + bellyRx - 42, y: 1392, width: 54, height: 92, rx: 6, fill: '#5ad1ff', opacity: .85 }, armR);
}
// head
const head = el('g', { id: 'head' }, ch);
el('rect', { x: 500, y: 1080, width: 80, height: 90, fill: SKIN }, head);           // neck
el('circle', { cx: 400, cy: 920, r: 40, fill: SKIN }, head); el('circle', { cx: 680, cy: 920, r: 40, fill: SKIN }, head);  // ears
el('ellipse', { cx: 540, cy: 920, rx: 150, ry: 170, fill: SKIN }, head);
// hair: a wild mop that gets combed as he glows up
const hair = el('g', {}, head);
for (let i = 0; i < 16; i++) {
  const a = Math.PI * (1.05 + .9 * i / 15), wild = 1 - .8 * g;
  el('circle', { cx: 540 + Math.cos(a) * (150 + 25 * wild * rnd()), cy: 860 + Math.sin(a) * (150 + 40 * wild * rnd()) - 10,
                 r: 52 + 30 * wild * rnd(), fill: HAIR }, hair);
}
el('ellipse', { cx: 540, cy: 790, rx: 150, ry: 70 - 20 * g, fill: HAIR }, hair);
// stubble
for (let i = 0; i < 70; i++) { const a = Math.PI * (.15 + .7 * rnd()), r = 110 + 50 * rnd();
  el('circle', { cx: 540 + Math.cos(a) * r * .95, cy: 930 + Math.sin(a) * r * .85, r: 3.5, fill: '#3a2614', opacity: .7 * mess }, head); }
// eyes
const eyes = el('g', { id: 'eyes' }, head);
for (const sx of [-1, 1]) {
  const cx = 540 + sx * 58;
  el('ellipse', { cx, cy: 905, rx: 38, ry: 30, fill: '#fff' }, eyes);
  el('circle', { cx: cx + 4, cy: 910, r: 15, fill: '#2a1a10', class: 'pupil' }, eyes);
  el('circle', { cx: cx + 9, cy: 904, r: 5, fill: '#fff' }, eyes);
  el('path', { d: `M ${cx - 34} 942 q 34 ${16 * mess} 68 0`, stroke: '#6b3d7a', 'stroke-width': 6, fill: 'none', opacity: .7 * mess }, eyes);  // eye bags
  el('path', { d: `M ${cx - 42} ${858 + 8 * sx * mess} L ${cx + 42} ${858 - 8 * sx * mess}`, stroke: HAIR, 'stroke-width': 16, 'stroke-linecap': 'round' }, head);   // brows
}
const lids = el('g', { id: 'lids' }, head);    // eyelids: scaleY 0 = open, 1 = shut
for (const sx of [-1, 1]) el('rect', { x: 540 + sx * 58 - 42, y: 872, width: 84, height: 66, fill: SKIN, class: 'lid' }, lids);
el('ellipse', { cx: 540, cy: 965, rx: 34, ry: 28, fill: '#a96a32' }, head);   // nose
if (g >= .3) el('path', { d: 'M 480 1010 q 60 -24 120 0 q -60 10 -120 0', fill: HAIR }, head);   // groomed moustache
const mouth = el('g', { id: 'mouth', transform: 'translate(540 1040)' }, head);
const mouthShapes = {
  sleep: 'M -30 0 q 30 12 60 0', sad: 'M -45 14 q 45 -34 90 0', shock: 'M -28 0 a 28 34 0 1 0 56 0 a 28 34 0 1 0 -56 0',
  happy: 'M -55 -6 q 55 60 110 0 z', proud: 'M -60 -4 q 60 50 120 0 z', neutral: 'M -40 4 q 40 10 80 0',
};
const mouthPath = el('path', { d: mouthShapes.neutral, fill: '#5a1e1e', stroke: '#3a1010', 'stroke-width': 8, 'stroke-linejoin': 'round' }, mouth);
const zzz = el('g', { id: 'zzz', opacity: 0 }, ch);
['Z', 'z', 'z'].forEach((t, i) => el('text', { x: 700 + i * 50, y: 760 - i * 60, class: 'ui', 'font-size': 90 - i * 20, fill: '#fff' }, zzz, t));
const sparkle = el('g', { id: 'sparkle', opacity: 0 }, ch);
for (let i = 0; i < 8; i++) { const a = i / 8 * Math.PI * 2, x = 540 + Math.cos(a) * 330, y = 1180 + Math.sin(a) * 420;
  el('path', { d: `M ${x} ${y - 30} L ${x + 9} ${y - 9} L ${x + 30} ${y} L ${x + 9} ${y + 9} L ${x} ${y + 30} L ${x - 9} ${y + 9} L ${x - 30} ${y} L ${x - 9} ${y - 9} Z`, fill: '#fff8c0' }, sparkle); }
el('rect', { x: 0, y: 0, width: 1080, height: 1920, fill: 'url(#vig)', 'pointer-events': 'none' });

// ---------- HUD: the score that every episode moves ----------
const hud = el('g', { id: 'hud' });
function card(x, w, label, value, color = '#fff') {
  const c = el('g', { transform: `translate(${x} 70)` }, hud);
  el('rect', { x: 0, y: 0, width: w, height: 150, rx: 22, fill: '#14121c', stroke: '#fff', 'stroke-width': 5, opacity: .92 }, c);
  el('text', { x: w / 2, y: 46, 'text-anchor': 'middle', class: 'inter', 'font-size': 26, fill: '#bdb8d0' }, c, label);
  return el('text', { x: w / 2, y: 128, 'text-anchor': 'middle', class: 'ui', 'font-size': 76, fill: color }, c, value);
}
const daysLeft = ep.days_total - ep.day + 1;
card(40, 240, 'DAYS LEFT', String(daysLeft), '#ff5a5a');
const pct = card(310, 420, ep.meter, `${Math.round(ep.glow_before * 100)}%`, '#7dff9b');
const delta = el('text', { x: 310 + 420 - 22, y: 70 + 126, 'text-anchor': 'end', class: 'ui', 'font-size': 40, fill: '#7dff9b', opacity: 0 }, hud,
  `+${Math.round((ep.glow - ep.glow_before) * 100)}%`);
card(760, 280, 'DAY', `${ep.day}/${ep.days_total}`, '#ffd400');
const bar = el('g', { transform: 'translate(40 240)' }, hud);
el('rect', { x: 0, y: 0, width: 1000, height: 26, rx: 13, fill: '#14121c', stroke: '#fff', 'stroke-width': 4 }, bar);
const fill = el('rect', { x: 4, y: 4, width: Math.max(1, 992 * ep.glow_before), height: 18, rx: 9, fill: '#7dff9b' }, bar);

// ---------- captions ----------
const capG = el('g', { id: 'caps' });
// The cover (first frame, which the feed shows): DAY N and the outcome big in the top third, like a poster.
const titleG = el('g', { id: 'title' });
const shade = el('linearGradient', { id: 'shade', x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
el('stop', { offset: 0, 'stop-color': '#000', 'stop-opacity': .55 }, shade); el('stop', { offset: .7, 'stop-color': '#000', 'stop-opacity': .3 }, shade);
el('stop', { offset: 1, 'stop-color': '#000', 'stop-opacity': 0 }, shade);
el('rect', { x: 0, y: 0, width: 1080, height: 820, fill: 'url(#shade)' }, titleG);
el('text', { x: 540, y: 250, 'text-anchor': 'middle', class: 'cap', 'font-size': 120, fill: '#ffd400', 'stroke-width': 18 }, titleG, `DAY ${ep.day}`);
const titleWords = (ep.day === 1 ? ep.premise : ep.title).toUpperCase();
const titleText = el('text', { x: 540, y: 410, 'text-anchor': 'middle', class: 'cap', 'font-size': 150, 'stroke-width': 22 }, titleG);
(function poster() {   // up to 3 lines, the last one yellow: "HE WENT TO / THE GYM"
  const words = titleWords.split(' '), lines = [''];
  for (const w of words) { if ((lines[lines.length - 1] + ' ' + w).trim().length > 12) lines.push(w); else lines[lines.length - 1] = (lines[lines.length - 1] + ' ' + w).trim(); }
  const size = lines.length > 2 ? 118 : 150;
  titleText.setAttribute('font-size', size);
  lines.forEach((l, i) => el('tspan', { x: 540, dy: i ? size * 1.02 : 0, fill: i === lines.length - 1 && lines.length > 1 ? '#ffd400' : '#fff' }, titleText, l));
})();

// The sign gag he holds up ("BELLY: INDOORS"): on the cover, then again on the win.
const signG = el('g', { id: 'sign', opacity: ep.sign ? 1 : 0 });
if (ep.sign) {
  const len = ep.sign.length, w = Math.min(860, 120 + len * 40);
  const sg = el('g', { transform: `translate(540 1240) rotate(-4)` }, signG);
  el('rect', { x: -w / 2, y: -70, width: w, height: 140, rx: 18, fill: ep.sign_good ? '#7be06b' : '#ff5a5a', stroke: '#111', 'stroke-width': 10 }, sg);
  el('text', { x: 0, y: 26, 'text-anchor': 'middle', class: 'ui', 'font-size': len > 16 ? 64 : 78, fill: '#111' }, sg, ep.sign.toUpperCase());
}

function wrap(node, text, maxChars, lh) {
  const words = text.split(' '), lines = [''];
  for (const w of words) { if ((lines[lines.length - 1] + ' ' + w).trim().length > maxChars) lines.push(w); else lines[lines.length - 1] = (lines[lines.length - 1] + ' ' + w).trim(); }
  lines.forEach((l, i) => el('tspan', { x: node.getAttribute('x'), dy: i ? lh : 0 }, node, l));
}

// comment card (the viewer's comment that this episode answers, or the ask at the end)
function commentCard(user, text, likes, label) {
  const c = el('g', { opacity: 0 }, el('g', { transform: 'translate(90 300)' }));   // GSAP moves the inner group
  el('rect', { x: 0, y: 0, width: 900, height: 230, rx: 28, fill: '#fff', stroke: '#000', 'stroke-width': 6 }, c);
  el('circle', { cx: 70, cy: 80, r: 40, fill: '#6c5ce7' }, c);
  el('text', { x: 70, y: 96, 'text-anchor': 'middle', class: 'ui', 'font-size': 44, fill: '#fff' }, c, user[0].toUpperCase());
  el('text', { x: 130, y: 70, class: 'inter', 'font-size': 30, fill: '#555' }, c, '@' + user);
  const t = el('text', { x: 130, y: 120, class: 'inter', 'font-size': 40, fill: '#111' }, c); wrap(t, text, 30, 46);
  if (likes) { el('text', { x: 870, y: 70, 'text-anchor': 'end', class: 'ui', 'font-size': 44, fill: '#e0245e' }, c, '♥ ' + likes); }
  el('text', { x: 30, y: 212, class: 'inter', 'font-size': 22, fill: '#999' }, c, label);
  return c;
}
const fromComment = ep.comment ? commentCard(ep.comment.user, ep.comment.text, ep.comment.likes, 'TOP COMMENT YESTERDAY') : null;
const askCard = el('g', { opacity: 0 });
el('rect', { x: 90, y: 1430, width: 900, height: 250, rx: 30, fill: '#ffd400', stroke: '#000', 'stroke-width': 8 }, askCard);
const askT = el('text', { x: 540, y: 1525, 'text-anchor': 'middle', class: 'ui', 'font-size': 70, fill: '#000' }, askCard); wrap(askT, ep.ask.toUpperCase(), 22, 78);
el('text', { x: 540, y: 1655, 'text-anchor': 'middle', class: 'inter', 'font-size': 34, fill: '#000' }, askCard, 'THE TOP COMMENT DECIDES TOMORROW');

// ---------- timeline ----------
const tl = gsap.timeline({ paused: true });
const D = ep.duration;
// idle: breathing bob and blinks across the whole episode
tl.to(ch, { y: -10, duration: .9, yoyo: true, repeat: Math.ceil(D / .9), ease: 'sine.inOut' }, 0);
for (let t = 1.7; t < D; t += 2.3 + rnd()) tl.to('.lid', { scaleY: 1, transformOrigin: '50% 0%', duration: .06, yoyo: true, repeat: 1 }, t);
gsap.set('.lid', { scaleY: g < .2 ? .45 : 0, transformOrigin: '50% 0%' });    // day 1: half-asleep

// cover, then the HUD and yesterday's top comment
tl.set(hud, { opacity: 0 }, 0);
tl.to(titleG, { opacity: 0, y: -60, duration: .3 }, 2.2);
if (ep.sign) tl.to(signG, { opacity: 0, duration: .2 }, 2.2);
tl.fromTo(hud, { opacity: 0, y: -40 }, { opacity: 1, y: 0, duration: .3, ease: 'back.out(2)' }, 2.3);
if (fromComment) { tl.fromTo(fromComment, { opacity: 0, y: 60 }, { opacity: 1, y: 0, duration: .3, ease: 'back.out(2)' }, 2.5);
                   tl.to(fromComment, { opacity: 0, duration: .25 }, 2.5 + Math.min(4, (ep.beats[0] || { dur: 3 }).dur + .8)); }

// beats: kinetic captions + mood + mouth flaps while the narrator speaks
function setMood(m, t) { tl.call(() => mouthPath.setAttribute('d', mouthShapes[m] || mouthShapes.neutral), null, t);
  if (m === 'sleep') { tl.to('.lid', { scaleY: 1, duration: .2 }, t); tl.to(zzz, { opacity: 1, duration: .3 }, t); }
  else { tl.to('.lid', { scaleY: m === 'sad' ? .4 : 0, duration: .15 }, t); tl.to(zzz, { opacity: 0, duration: .2 }, t); } }
for (const b of ep.beats) {
  setMood(b.mood || 'neutral', b.t);
  const words = b.text.toUpperCase().split(' ');
  const lines = []; let cur = [];
  for (const w of words) { if ([...cur, w].join(' ').length > 14) { lines.push(cur); cur = [w]; } else cur.push(w); }
  if (cur.length) lines.push(cur);
  const per = Math.max(.12, (b.dur * .55) / words.length);
  let k = 0;
  lines.forEach((ln, li) => {
    const txt = el('text', { x: 540, y: 1560 + li * 120 - (lines.length - 1) * 60, 'text-anchor': 'middle', class: 'cap', 'font-size': 108, 'stroke-width': 16 }, capG);
    ln.forEach((w, wi) => {
      const span = el('tspan', { fill: b.hl && b.hl.includes(w.replace(/[^A-Z0-9%]/g, '')) ? '#ffd400' : '#fff', opacity: 0 }, txt, (wi ? ' ' : '') + w);
      tl.to(span, { opacity: 1, duration: .05 }, b.t + per * k++);
    });
    tl.fromTo(txt, { scale: .85, transformOrigin: '540px 1560px' }, { scale: 1, duration: .18, ease: 'back.out(3)' }, b.t);
    tl.to(txt, { opacity: 0, duration: .12 }, b.t + b.dur - .05);
  });
  if (b.talk) for (let t = b.t; t < b.t + b.dur - .2; t += .16)
    tl.to(mouth, { scaleY: .35, transformOrigin: '50% 50%', duration: .07, yoyo: true, repeat: 1 }, t);
  if (b.action === 'alarm' && clock) {
    tl.to(ring, { opacity: 1, duration: .05 }, b.t);
    tl.to(clock, { rotation: 12, transformOrigin: '50% 50%', duration: .05, yoyo: true, repeat: Math.round(b.dur / .1) }, b.t);
    tl.to(ring, { opacity: 0, duration: .05 }, b.t + b.dur);
  }
  if (b.action === 'jolt') tl.fromTo(ch, { y: 0 }, { y: -140, duration: .18, yoyo: true, repeat: 1, ease: 'power2.out' }, b.t);
  if (b.action === 'glow') {
    tl.to(sparkle, { opacity: 1, duration: .2 }, b.t);
    tl.fromTo(sparkle, { rotation: 0, transformOrigin: '540px 1180px' }, { rotation: 25, duration: b.dur, ease: 'none' }, b.t);
    tl.to(sparkle, { opacity: 0, duration: .3 }, b.t + b.dur - .2);
    tl.fromTo(ch, { scale: 1, transformOrigin: '540px 1750px' }, { scale: 1.06, duration: .2, yoyo: true, repeat: 1 }, b.t);
    const target = { v: ep.glow_before * 100 };
    tl.to(target, { v: ep.glow * 100, duration: .8, ease: 'power2.out', onUpdate: () => { pct.textContent = Math.round(target.v) + '%'; } }, b.t);
    tl.to(fill, { attr: { width: Math.max(1, 992 * ep.glow) }, duration: .8, ease: 'power2.out' }, b.t);
    tl.fromTo(delta, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: .3 }, b.t + .2);
    if (ep.sign) tl.fromTo(signG, { opacity: 0, scale: .5, transformOrigin: '540px 1240px' }, { opacity: 1, scale: 1, duration: .3, ease: 'back.out(3)', immediateRender: false }, b.t + .3);
  }
}
// ask for the next episode
tl.fromTo(askCard, { opacity: 0, y: 80 }, { opacity: 1, y: 0, duration: .35, ease: 'back.out(2)' }, D - 3.2);
tl.to({}, { duration: 0 }, D);

window.DURATION = D;
window.frame = t => { tl.seek(t, false); };
document.fonts.ready.then(() => { tl.seek(0); window.READY = true; });
