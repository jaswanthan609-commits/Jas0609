// NRI Money Guide: 3D hook shot (three.js, deterministic render(t)).
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const q = new URLSearchParams(location.search);
const W = +(q.get('w') || 1920), H = +(q.get('h') || 1080), S = W / 1920;
const DUR = 15.7, VO = 0.25; // voice starts 0.25 s in (same as the HyperFrames cut)
for (const [n, f] of [['SG5', 'space-grotesk-latin-500-normal.woff2'], ['SG7', 'space-grotesk-latin-700-normal.woff2']]) { const ff = new FontFace(n, `url(./fonts/${f})`); await ff.load(); document.fonts.add(ff); }
const WORDS = await (await fetch('./nri_hook_words.json')).json();
const wt = (w, n = 0) => { let k = 0; for (const x of WORDS) if (x.w.toLowerCase().replace(/[^a-z0-9]/g, '') === w && k++ === n) return x.t + VO; throw w; };
const T_BIG = wt('thirtyone'), T_WRONG = wt('wrong'), T_TAKE = wt('take'), T_LAKH = wt('lakh'), T_NRE = wt('nre'), T_NRO = wt('nro'), T_THREE = wt('three');

let seed = 3; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const ease = x => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const back = x => { x = clamp(x); const c = 1.9; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a1324); scene.fog = new THREE.Fog(0x0a1324, 10, 26);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), .04).texture; scene.environmentIntensity = .55;
const camera = new THREE.PerspectiveCamera(34, W / H, .05, 60);

function canvasTex(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; }

// generic, stylised ₹500 note (not a reproduction of the real design)
const noteTex = canvasTex(1024, 480, (g, w, h) => {
  const gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#c9c3b0'); gr.addColorStop(.5, '#b9b7a6'); gr.addColorStop(1, '#a8ae9c');
  g.fillStyle = gr; g.fillRect(0, 0, w, h);
  g.strokeStyle = 'rgba(70,80,70,.25)'; g.lineWidth = 2;
  for (let i = 0; i < 60; i++) { g.beginPath(); for (let x = 0; x <= w; x += 16) g.lineTo(x, h * .5 + Math.sin(x * .012 + i * .4) * (60 + i * 3)); g.stroke(); }
  g.fillStyle = 'rgba(255,255,255,.35)'; g.beginPath(); g.ellipse(w * .74, h * .5, 120, 150, 0, 0, 7); g.fill();
  g.strokeStyle = 'rgba(60,60,55,.6)'; g.lineWidth = 6; g.strokeRect(18, 18, w - 36, h - 36);
  g.fillStyle = '#3e4340'; g.font = '700 150px "SG7"'; g.fillText('₹500', 60, 190);
  g.font = '500 44px "SG5"'; g.fillStyle = 'rgba(50,55,50,.75)'; g.fillText('FIVE HUNDRED RUPEES', 64, 260);
  g.fillStyle = 'rgba(90,70,40,.35)'; g.fillRect(w * .52, 0, 18, h);
  g.font = '700 70px "SG7"'; g.fillStyle = 'rgba(50,55,50,.55)'; g.fillText('500', w - 210, h - 60);
});
const edgeTex = canvasTex(256, 64, (g, w, h) => { for (let y = 0; y < h; y++) { const v = 170 + (rnd() * 40 | 0); g.fillStyle = `rgb(${v},${v - 4},${v - 16})`; g.fillRect(0, y, w, 1); } });
const noteMat = new THREE.MeshStandardMaterial({ map: noteTex, roughness: .75, color: 0xd0d0d0 });
const edgeMat = new THREE.MeshStandardMaterial({ map: edgeTex, roughness: .85 });

// a stack of 24 bundles = "₹1 lakh of interest"
const NS = 24, SH = .064, stack = [];
const slabGeo = new THREE.BoxGeometry(1.7, SH * .92, .8);
for (let i = 0; i < NS; i++) {
  const mats = [edgeMat, edgeMat, noteMat, edgeMat, edgeMat, edgeMat].map(m => m.clone());
  const m = new THREE.Mesh(slabGeo, mats); m.castShadow = m.receiveShadow = true;
  m.userData = { y: SH * (i + .5), r: (rnd() - .5) * .05, dx: (rnd() - .5) * .04, dz: (rnd() - .5) * .03, a: rnd() * 6.28 };
  scene.add(m); stack.push(m);
}
const CUT = Math.round(NS * .312); // top 31.2% leaves

// floor, coins, cards
const floor = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshStandardMaterial({ color: 0x0d1830, roughness: .32, metalness: .35 }));
floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
const gold = new THREE.MeshStandardMaterial({ color: 0xe6b450, metalness: 1, roughness: .28 });
const coins = [];
for (let i = 0; i < 14; i++) {
  const c = new THREE.Mesh(new THREE.CylinderGeometry(.16, .16, .035, 48), gold); c.castShadow = true;
  const a = rnd() * 6.28, r = 1.4 + rnd() * 1.6;
  c.userData = { x: Math.cos(a) * r, z: Math.sin(a) * r * .8 + .4, h: Math.floor(rnd() * 3), d: rnd() * .6 };
  coins.push(c); scene.add(c);
}
function cardTex(title, sub, col) {
  return canvasTex(1024, 560, (g, w, h) => {
    g.fillStyle = '#13213b'; g.fillRect(0, 0, w, h);
    g.strokeStyle = col; g.lineWidth = 16; g.beginPath(); g.roundRect(14, 14, w - 28, h - 28, 50); g.stroke();
    g.fillStyle = col; g.font = '700 230px "SG7"'; g.textAlign = 'center'; g.fillText(title, w / 2, 290);
    g.fillStyle = '#eef3fb'; g.font = '500 78px "SG5"'; g.fillText(sub, w / 2, 430);
  });
}
function card(title, sub, col, x) {
  const grp = new THREE.Group();
  const body = new THREE.Mesh(new RoundedBoxGeometry(2.1, 1.15, .12, 6, .08), new THREE.MeshStandardMaterial({ color: 0x13213b, roughness: .4, metalness: .3 }));
  body.castShadow = true; grp.add(body);
  const face = new THREE.Mesh(new THREE.PlaneGeometry(2.0, 1.05), new THREE.MeshBasicMaterial({ map: cardTex(title, sub, col), toneMapped: false, color: 0xd8d8d8 }));
  face.position.z = .061; grp.add(face);
  grp.userData.x = x; scene.add(grp); return grp;
}
const nre = card('NRE', 'interest: tax-free', '#3ccf8e', -2.55);
const nro = card('NRO', 'interest: 31.2% TDS', '#ff5d5d', 2.55);

// lights
scene.add(new THREE.HemisphereLight(0x9fb4e0, 0x0a1324, .5));
const key = new THREE.SpotLight(0xffe2c0, 32, 0, .5, .6, 1.4); key.position.set(3, 7, 4); key.target.position.set(0, .7, 0);
key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 4; scene.add(key, key.target);
const rimO = new THREE.PointLight(0xff9933, 14, 0, 1.6); rimO.position.set(-3, 2.2, -2.5); scene.add(rimO);
const rimB = new THREE.PointLight(0x4f7cff, 10, 0, 1.6); rimB.position.set(3.5, 1.8, -2.8); scene.add(rimB);
const redL = new THREE.PointLight(0xff3b3b, 0, 0, 1.4); redL.position.set(1.2, 2.6, 1.2); scene.add(redL);

const composer = new EffectComposer(renderer); composer.setPixelRatio(1); composer.setSize(W, H);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(new THREE.Vector2(W, H), .35, .5, .88));
composer.addPass(new OutputPass());

// camera keys [t, pos, target]
const K = [
  [0, [0.6, 6.5, 8.6], [0, .9, 0]],
  [2.6, [3.0, 2.5, 5.0], [0, .95, 0]],
  [5.2, [2.4, 2.4, 4.4], [0, 1.15, 0]],
  [7.8, [1.6, 2.3, 5.4], [0, 1.0, 0]],
  [10.2, [0.0, 2.3, 8.4], [0, .45, 0]],
  [13.4, [-0.5, 2.1, 7.6], [0, .5, 0]],
  [15.7, [0.0, 1.4, 4.6], [0, 1.0, 0]],
];
function camAt(t) {
  let i = 0; while (i < K.length - 2 && t > K[i + 1][0]) i++;
  const [t0] = K[i], [t1] = K[i + 1], u = clamp((t - t0) / (t1 - t0)), dt = t1 - t0;
  const tan = (a, b, idx) => b[idx].map((v, k) => (v - a[idx][k]) / (b[0] - a[0]));
  return [1, 2].map(idx => {
    const m0 = i === 0 ? [0, 0, 0] : tan(K[i - 1], K[i + 1], idx), m1 = i + 2 >= K.length ? [0, 0, 0] : tan(K[i], K[i + 2], idx);
    const u2 = u * u, u3 = u2 * u;
    return K[i][idx].map((v, k) => (2 * u3 - 3 * u2 + 1) * v + (u3 - 2 * u2 + u) * dt * m0[k] + (-2 * u3 + 3 * u2) * K[i + 1][idx][k] + (u3 - u2) * dt * m1[k]);
  });
}

// overlay
const out = document.createElement('canvas'); out.width = W; out.height = H; document.body.appendChild(out);
const g2 = out.getContext('2d');
const inr = n => '₹' + Math.round(n).toLocaleString('en-IN');
const chunks = []; { let cur = []; for (const w of WORDS) { cur.push(w); if (cur.length === 5 || /[.?!,]$/.test(w.w)) { chunks.push(cur); cur = []; } } if (cur.length) chunks.push(cur); }
function overlay(t) {
  g2.clearRect(0, 0, W, H); g2.drawImage(renderer.domElement, 0, 0);
  // brand
  g2.globalAlpha = 1; g2.fillStyle = '#ff9933'; g2.beginPath(); g2.arc(127 * S, 82 * S, 7 * S, 0, 7); g2.fill();
  g2.font = `700 ${30 * S}px SG7`; g2.letterSpacing = `${5 * S}px`; g2.textAlign = 'left'; g2.fillText('NRI MONEY GUIDE', 148 * S, 93 * S); g2.letterSpacing = '0px';
  g2.textAlign = 'center'; g2.shadowColor = 'rgba(0,0,0,.6)'; g2.shadowBlur = 24 * S;
  // big number
  const bigA = clamp((t - T_BIG + .1) / .3) * clamp((T_NRE - .2 - t) / .4);
  if (bigA > 0) {
    const n = 31200 * ease((t - T_BIG) / 1.3), lost = clamp((t - T_TAKE) / .3);
    const sc = 1 + .08 * Math.sin(clamp((t - T_TAKE) / .4) * Math.PI);
    g2.save(); g2.translate(W / 2, 250 * S); g2.scale(sc, sc); g2.globalAlpha = bigA;
    g2.fillStyle = lost > 0 ? `rgb(255,${153 - 60 * lost | 0},${51 + 42 * lost | 0})` : '#ff9933';
    g2.font = `700 ${190 * S}px SG7`; g2.fillText((lost > .5 ? '−' : '') + inr(n), 0, 0); g2.restore();
    const la = clamp((t - T_LAKH + .15) / .35) * bigA;
    if (la > 0) { g2.globalAlpha = la; g2.fillStyle = '#eef3fb'; g2.font = `500 ${54 * S}px SG5`; g2.fillText('on every ₹1,00,000 of interest', W / 2, 335 * S + (1 - la) * 20 * S); }
  }
  // "3 rules" chip
  const ra = clamp((t - T_THREE + .1) / .3);
  if (ra > 0) {
    g2.globalAlpha = ra; g2.shadowBlur = 0; const y = 220 * S, s = .7 + .3 * back((t - T_THREE + .1) / .45);
    g2.save(); g2.translate(W / 2, y); g2.scale(s, s);
    g2.fillStyle = 'rgba(10,19,36,.85)'; g2.beginPath(); g2.roundRect(-420 * S, -70 * S, 840 * S, 120 * S, 24 * S); g2.fill();
    g2.fillStyle = '#ff9933'; g2.beginPath(); g2.roundRect(-400 * S, -55 * S, 92 * S, 92 * S, 20 * S); g2.fill();
    g2.fillStyle = '#0a1324'; g2.font = `700 ${64 * S}px SG7`; g2.fillText('3', -354 * S, 14 * S);
    g2.fillStyle = '#eef3fb'; g2.textAlign = 'left'; g2.font = `700 ${58 * S}px SG7`; g2.fillText('rules that decide it', -280 * S, 14 * S); g2.textAlign = 'center';
    g2.restore();
  }
  // captions: ≤5 words, current word in orange
  g2.shadowBlur = 0; g2.globalAlpha = 1;
  const tv = t - VO; const ch = chunks.find((c, i) => tv >= c[0].t - .05 && (i === chunks.length - 1 ? tv < c[c.length - 1].t + .8 : tv < chunks[i + 1][0].t - .05));
  if (ch) {
    g2.font = `700 ${60 * S}px SG7`; const parts = ch.map(w => w.w), sp = g2.measureText(' ').width;
    const widths = parts.map(p => g2.measureText(p).width), total = widths.reduce((a, b) => a + b, 0) + sp * (parts.length - 1);
    let x = W / 2 - total / 2; const y = H - 84 * S;
    g2.fillStyle = 'rgba(10,19,36,.78)'; g2.beginPath(); g2.roundRect(x - 30 * S, y - 64 * S, total + 60 * S, 90 * S, 18 * S); g2.fill();
    g2.textAlign = 'left';
    ch.forEach((w, k) => { g2.fillStyle = tv >= w.t - .02 && tv < w.t + w.d + .1 ? '#ff9933' : '#eef3fb'; g2.fillText(parts[k], x, y); x += widths[k] + sp; });
    g2.textAlign = 'center';
  }
  g2.globalAlpha = 1;
}

function render(t) {
  // stack builds 0.05 – 1.6 s, bundles drop in from above
  stack.forEach((m, i) => {
    const d = m.userData, t0 = .05 + i * .055, u = clamp((t - t0) / .45);
    let y = d.y + (1 - u * u) * 4.5, x = d.dx, z = d.dz, rx = 0, rz = 0, ry = d.r;
    m.visible = t >= t0;
    if (i >= NS - CUT) { // the taxed share lifts and flies off
      const j = i - (NS - CUT), f = clamp((t - T_TAKE - j * .05) / 1.4), f2 = f * f;
      y += f2 * 5 + Math.sin(f * Math.PI) * .4; x += f2 * 7.5 + j * .04 * f; z -= f2 * 3; rz = -f2 * 1.6 - j * .05 * f; rx = f2 * .8; ry += f * (j % 2 ? .6 : -.6);
      const red = clamp((t - T_TAKE + .2) / .3);
      m.material.forEach(mm => { mm.emissive.setRGB(.55 * red, .02 * red, .02 * red); });
    }
    m.position.set(x, y, z); m.rotation.set(rx, ry, rz);
  });
  redL.intensity = 18 * clamp((t - T_TAKE + .2) / .3) * clamp((T_TAKE + 1.6 - t) / .6);
  coins.forEach((c, i) => {
    const d = c.userData, t0 = 1.0 + d.d, u = clamp((t - t0) / .55), b = Math.abs(Math.sin(u * Math.PI * 2.5)) * (1 - u) * .5;
    c.visible = t >= t0; c.position.set(d.x, .018 + d.h * .036 + (1 - u) * 3 * (1 - u) + b, d.z); c.rotation.set((1 - u) * 4, i, (1 - u) * 2);
  });
  for (const [cd, tt, sgn] of [[nre, T_NRE, -1], [nro, T_NRO, 1]]) {
    const u = back((t - tt + .1) / .7), e = ease((t - tt + .1) / .7);
    cd.visible = t > tt - .2;
    cd.position.set(cd.userData.x + sgn * (1 - e) * 1.5, -0.7 + u * 1.45, .9); cd.rotation.set(0, -sgn * .32 + sgn * (1 - e) * .8, 0);
    cd.position.y += Math.sin(t * 1.3 + sgn) * .03 * e;
  }
  const [p, a] = camAt(t);
  camera.position.set(p[0] + Math.sin(t * .4) * .05, p[1] + Math.sin(t * .5) * .03, p[2]); camera.lookAt(...a);
  composer.render(); overlay(t);
}

window.DUR = DUR; window.render = render;
window.frame = (t, qual = .92) => { render(t); return out.toDataURL('image/jpeg', qual); };
render(0); window.READY = true;
