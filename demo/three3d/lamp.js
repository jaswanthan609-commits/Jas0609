// Slow History for Sleep: "The Oil Lamp" as a real 3D scene (three.js, deterministic render(t)).
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const q = new URLSearchParams(location.search);
const W = +(q.get('w') || 1920), H = +(q.get('h') || 1080);
const DUR = 88;

// ---------- deterministic noise ----------
let seed = 7;
const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
const hash = n => { const s = Math.sin(n * 127.1) * 43758.5453; return s - Math.floor(s); };
const vnoise = x => { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return hash(i) * (1 - u) + hash(i + 1) * u; };
const fbm = x => vnoise(x) * 0.55 + vnoise(x * 2.3 + 11) * 0.3 + vnoise(x * 5.1 + 31) * 0.15;

// ---------- renderer ----------
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x07050a);
scene.fog = new THREE.FogExp2(0x07050a, 0.035);
const camera = new THREE.PerspectiveCamera(32, W / H, 0.05, 80);

// ---------- procedural textures ----------
function canvasTex(w, h, draw, srgb = true) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8;
  return t;
}
const clayTex = canvasTex(512, 512, (g, w, h) => {
  g.fillStyle = '#b86a42'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 9000; i++) {
    const v = rnd(); g.fillStyle = v < .5 ? `rgba(70,30,15,${.05 + rnd() * .12})` : `rgba(240,190,140,${.04 + rnd() * .1})`;
    const r = rnd() * 2.2 + .3; g.beginPath(); g.arc(rnd() * w, rnd() * h, r, 0, 7); g.fill();
  }
  for (let i = 0; i < 40; i++) { g.fillStyle = `rgba(60,25,10,${rnd() * .08})`; g.beginPath(); g.arc(rnd() * w, rnd() * h, 20 + rnd() * 60, 0, 7); g.fill(); }
});
const clayBump = canvasTex(512, 512, (g, w, h) => {
  g.fillStyle = '#808080'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 14000; i++) { const v = rnd() * 255 | 0; g.fillStyle = `rgba(${v},${v},${v},.35)`; g.fillRect(rnd() * w, rnd() * h, 1.5, 1.5); }
}, false);
const woodTex = canvasTex(1024, 1024, (g, w, h) => {
  g.fillStyle = '#3a2416'; g.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += 2) {
    const k = fbm(y * .02) * .6 + fbm(y * .003 + 5) * .4;
    g.fillStyle = `rgba(${90 + k * 60 | 0},${55 + k * 35 | 0},${30 + k * 20 | 0},.55)`;
    g.fillRect(0, y + Math.sin(y * .01) * 2, w, 2);
  }
  for (let i = 0; i < 6; i++) { g.strokeStyle = 'rgba(15,8,4,.5)'; g.lineWidth = 2; const y = rnd() * h; g.beginPath(); g.moveTo(0, y); g.lineTo(w, y + rnd() * 6); g.stroke(); }
  for (let i = 0; i < 3000; i++) { g.fillStyle = `rgba(0,0,0,${rnd() * .15})`; g.fillRect(rnd() * w, rnd() * h, 6 + rnd() * 30, 1); }
});
woodTex.repeat.set(3, 3);
const plasterTex = canvasTex(512, 512, (g, w, h) => {
  g.fillStyle = '#4a3a30'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 400; i++) { g.fillStyle = `rgba(${rnd() < .5 ? '20,14,10' : '120,100,85'},${rnd() * .07})`; g.beginPath(); g.arc(rnd() * w, rnd() * h, 10 + rnd() * 50, 0, 7); g.fill(); }
});
plasterTex.repeat.set(4, 2);
const softDot = canvasTex(64, 64, (g) => {
  const r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(.4, 'rgba(255,255,255,.35)'); r.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = r; g.fillRect(0, 0, 64, 64);
});

const clay = new THREE.MeshStandardMaterial({ map: clayTex, bumpMap: clayBump, bumpScale: 0.6, roughness: 0.82, metalness: 0, vertexColors: true });
const clayPlain = new THREE.MeshStandardMaterial({ map: clayTex, bumpMap: clayBump, bumpScale: 0.6, roughness: 0.85, color: 0xd09070 });

function shade(geo, fn) { // vertex colours for soot / discus tone
  const p = geo.attributes.position, c = new Float32Array(p.count * 3);
  for (let i = 0; i < p.count; i++) { const k = fn(p.getX(i), p.getY(i), p.getZ(i)); c[i * 3] = k[0]; c[i * 3 + 1] = k[1]; c[i * 3 + 2] = k[2]; }
  geo.setAttribute('color', new THREE.BufferAttribute(c, 3));
  return geo;
}
const soot = (x, y) => { const s = THREE.MathUtils.smoothstep(x, 1.15, 1.75) * THREE.MathUtils.smoothstep(y, 0.12, 0.34); const k = 1 - 0.78 * s; return [k, k * 0.95, k * 0.92]; };

// ---------- the lamp ----------
const lamp = new THREE.Group(); scene.add(lamp);
const prof = [[0, 0], [.5, 0], [.56, .02], [.58, .06], [.8, .1], [.95, .18], [1.0, .26], [.98, .32], [.9, .38], [.8, .41], [.74, .41], [.7, .38], [.55, .345], [.2, .33], [0, .33]]
  .map(([r, y]) => new THREE.Vector2(r, y));
const bodyGeo = shade(new THREE.LatheGeometry(prof, 128), (x, y, z) => { const r = Math.hypot(x, z); const d = r < .72 && y > .3 ? .82 : 1; const s = soot(x, y); return [s[0] * d, s[1] * d, s[2] * d]; });
const body = new THREE.Mesh(bodyGeo, clay); lamp.add(body);

// nozzle: rounded stadium extruded upward
const ns = new THREE.Shape();
ns.moveTo(.55, -.3); ns.lineTo(1.5, -.2); ns.absarc(1.55, 0, .2, -Math.PI / 2, Math.PI / 2, false); ns.lineTo(.55, .3); ns.lineTo(.55, -.3);
const nozGeo = new THREE.ExtrudeGeometry(ns, { depth: .16, bevelEnabled: true, bevelThickness: .05, bevelSize: .05, bevelSegments: 6, curveSegments: 40 });
nozGeo.rotateX(-Math.PI / 2); nozGeo.translate(0, .12, 0);
shade(nozGeo, soot);
const noz = new THREE.Mesh(nozGeo, clay); lamp.add(noz);
const wickHole = new THREE.Mesh(new THREE.CircleGeometry(.075, 32), new THREE.MeshStandardMaterial({ color: 0x0c0705, roughness: 1 }));
wickHole.rotation.x = -Math.PI / 2; wickHole.position.set(1.58, .335, 0); lamp.add(wickHole);
const wick = new THREE.Mesh(new THREE.CylinderGeometry(.025, .035, .09, 12), new THREE.MeshStandardMaterial({ color: 0x1a1210, roughness: 1, emissive: 0x501800, emissiveIntensity: .6 }));
wick.position.set(1.58, .36, 0); lamp.add(wick);
// little volutes beside the nozzle
for (const s of [-1, 1]) {
  const v = new THREE.Mesh(new THREE.TorusGeometry(.07, .022, 12, 32), clayPlain);
  v.rotation.x = -Math.PI / 2; v.position.set(.95, .335, s * .2); lamp.add(v);
}
// ring handle
const handle = new THREE.Mesh(new THREE.TorusGeometry(.2, .065, 24, 64), clayPlain);
handle.position.set(-1.16, .28, 0); lamp.add(handle);
// discus: rosette petals + filling hole
for (let i = 0; i < 12; i++) {
  const a = i / 12 * Math.PI * 2;
  const p = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 12), clayPlain);
  p.scale.set(.16, .022, .055); p.position.set(Math.cos(a) * .4, .345, Math.sin(a) * .4); p.rotation.y = -a; lamp.add(p);
}
const ringIn = new THREE.Mesh(new THREE.TorusGeometry(.16, .018, 12, 48), clayPlain);
ringIn.rotation.x = -Math.PI / 2; ringIn.position.set(0, .34, 0); lamp.add(ringIn);
const fillHole = new THREE.Mesh(new THREE.CircleGeometry(.07, 32), new THREE.MeshStandardMaterial({ color: 0x090504, roughness: 1 }));
fillHole.rotation.x = -Math.PI / 2; fillHole.position.set(0, .3355, 0); lamp.add(fillHole);
// oil glint inside the filling hole
const oil = new THREE.Mesh(new THREE.CircleGeometry(.055, 32), new THREE.MeshStandardMaterial({ color: 0x2a1a05, roughness: .08, metalness: .2 }));
oil.rotation.x = -Math.PI / 2; oil.position.set(0, .333, 0); lamp.add(oil);
lamp.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });

// ---------- room ----------
const table = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({ map: woodTex, roughness: .72, color: 0xb09080 }));
table.rotation.x = -Math.PI / 2; table.receiveShadow = true; scene.add(table);
const wall = new THREE.Mesh(new THREE.PlaneGeometry(40, 14), new THREE.MeshStandardMaterial({ map: plasterTex, roughness: 1 }));
wall.position.set(0, 7, -5); wall.receiveShadow = true; scene.add(wall);
// window with moonlight
const winTex = canvasTex(256, 384, (g, w, h) => {
  const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#5d79a8'); gr.addColorStop(1, '#22304e');
  g.fillStyle = gr; g.fillRect(0, 0, w, h); g.fillStyle = '#0a0806'; g.fillRect(w / 2 - 6, 0, 12, h); g.fillRect(0, h / 2 - 6, w, 12);
  g.fillStyle = 'rgba(230,235,255,.9)'; g.beginPath(); g.arc(w * .72, h * .2, 16, 0, 7); g.fill();
});
const win = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 3.2), new THREE.MeshBasicMaterial({ map: winTex, color: 0x9aa6c0 }));
win.position.set(-4.5, 3.6, -4.98); scene.add(win);
const moon = new THREE.DirectionalLight(0x8aa0d8, .35); moon.position.set(-6, 6, -3); scene.add(moon);
scene.add(new THREE.HemisphereLight(0x223048, 0x120a06, .12));

// props: a cup, an oil jug and a scroll
function lathe(pts, mat, seg = 64) { const m = new THREE.Mesh(new THREE.LatheGeometry(pts.map(([r, y]) => new THREE.Vector2(r, y)), seg), mat); m.castShadow = m.receiveShadow = true; return m; }
const cup = lathe([[0, 0], [.3, 0], [.34, .05], [.38, .4], [.42, .62], [.39, .62], [.34, .42], [0, .4]], new THREE.MeshStandardMaterial({ map: clayTex, color: 0x7a5040, roughness: .6 }));
cup.position.set(-2.3, 0, -1.3); scene.add(cup);
const jug = lathe([[0, 0], [.35, 0], [.55, .35], [.58, .7], [.42, 1.05], [.2, 1.25], [.17, 1.5], [.22, 1.58], [.19, 1.6], [.13, 1.5], [0, 1.45]], new THREE.MeshStandardMaterial({ map: clayTex, color: 0x9c6a50, roughness: .75 }));
jug.position.set(2.6, 0, -2.3); scene.add(jug);
const scroll = new THREE.Group();
const paper = new THREE.Mesh(new THREE.CylinderGeometry(.14, .14, 1.5, 32), new THREE.MeshStandardMaterial({ color: 0xcdb48a, roughness: .9 }));
paper.rotation.z = Math.PI / 2; scroll.add(paper);
for (const s of [-1, 1]) { const k = new THREE.Mesh(new THREE.CylinderGeometry(.05, .05, .2, 16), new THREE.MeshStandardMaterial({ color: 0x2c1a10 })); k.rotation.z = Math.PI / 2; k.position.x = s * .85; scroll.add(k); }
scroll.position.set(0.4, .14, -2.4); scroll.rotation.y = .35; scroll.traverse(o => { if (o.isMesh) { o.castShadow = o.receiveShadow = true; } }); scene.add(scroll);

// ---------- flame ----------
const FLAME = new THREE.Vector3(1.58, .43, 0);
const flameMat = new THREE.ShaderMaterial({
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  uniforms: { uT: { value: 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader: `varying vec2 vUv; uniform float uT;
    float h(float n){return fract(sin(n)*43758.5453);} float n1(float x){float i=floor(x),f=fract(x);f=f*f*(3.-2.*f);return mix(h(i),h(i+1.),f);}
    void main(){ float y=vUv.y; float sway=(n1(uT*2.1+y*1.5)-.5)*.18*y*y; float x=(vUv.x-.5-sway)*2.;
      float w=.62*pow(sin(3.14159*pow(clamp(y,0.,1.),.55)),1.3)*(1.-.15*n1(uT*7.)); float d=abs(x)/max(w,1e-3);
      float a=smoothstep(1.,.55,d)*smoothstep(0.,.08,y)*smoothstep(1.,.75,y);
      float core=smoothstep(.65,0.,d)*smoothstep(.75,.2,y);
      vec3 col=mix(vec3(1.,.35,.05),vec3(1.,.75,.35),smoothstep(.2,.9,1.-d)); col=mix(col,vec3(1.,.97,.85),core);
      float blue=smoothstep(.18,.0,y)*smoothstep(1.,.3,d)*.6; col=mix(col,vec3(.25,.35,1.),blue);
      gl_FragColor=vec4(col*a*2.4,a); }`,
});
const flame = new THREE.Mesh(new THREE.PlaneGeometry(.17, .42), flameMat); scene.add(flame);
const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: softDot, color: 0xff9440, transparent: true, opacity: .55, blending: THREE.AdditiveBlending, depthWrite: false }));
glow.scale.set(1.3, 1.3, 1); scene.add(glow);
const fire = new THREE.PointLight(0xff9a4c, 9, 0, 1.6);
fire.castShadow = true; fire.shadow.mapSize.set(1024, 1024); fire.shadow.radius = 6; fire.shadow.bias = -0.002; fire.shadow.camera.near = .05;
scene.add(fire);
const fill = new THREE.PointLight(0xff7a30, 1.2, 0, 1.8); fill.position.set(1.0, 2.6, 2.5); scene.add(fill);
const bounce = new THREE.PointLight(0xffa060, 0, 0, 1.5); bounce.position.set(-2.2, 1.4, 1.6); scene.add(bounce);

// ---------- dust ----------
const ND = 700, dpos = new Float32Array(ND * 3), dseed = [];
for (let i = 0; i < ND; i++) dseed.push([rnd() * 8 - 4, rnd() * 3.2, rnd() * 6 - 3, rnd() * 6.28, .02 + rnd() * .05]);
const dgeo = new THREE.BufferGeometry(); dgeo.setAttribute('position', new THREE.BufferAttribute(dpos, 3));
const dust = new THREE.Points(dgeo, new THREE.PointsMaterial({ map: softDot, size: .035, color: 0xffc890, transparent: true, opacity: .55, blending: THREE.AdditiveBlending, depthWrite: false }));
scene.add(dust);

// ---------- post ----------
const composer = new EffectComposer(renderer);
composer.setPixelRatio(1); composer.setSize(W, H);
composer.addPass(new RenderPass(scene, camera));
const bokeh = new BokehPass(scene, camera, { focus: 5, aperture: 0.0016, maxblur: 0.008 });
composer.addPass(bokeh);
composer.addPass(new UnrealBloomPass(new THREE.Vector2(W, H), .55, .6, .82));
composer.addPass(new OutputPass());
const grade = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, uT: { value: 0 }, uFade: { value: 1 } },
  vertexShader: `varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uT,uFade; varying vec2 vUv;
    float h(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233))+uT*37.)*43758.5453);}
    void main(){ vec3 c=texture2D(tDiffuse,vUv).rgb; vec2 d=vUv-.5; float v=smoothstep(.85,.25,length(d*vec2(1.25,1.)));
      c*=mix(.35,1.,v); c=mix(c,c*vec3(1.05,.98,.9),.5); c+=(h(vUv*1000.)-.5)*.035; gl_FragColor=vec4(c*uFade,1.); }`,
});
composer.addPass(grade);

// ---------- camera path (time-based Catmull-Rom / Hermite) ----------
const K = [
  [0, [10, 5.2, 10.5], [0.2, .4, 0]],
  [13.7, [4.4, 2.1, 5.0], [0.3, .38, 0]],
  [20.0, [3.0, 1.7, 3.9], [0.15, .36, 0]],
  [25.5, [-2.6, 1.15, 2.1], [-1.0, .32, 0]],
  [32.0, [-2.2, .95, 2.5], [-1.0, .32, 0]],
  [36.5, [0.35, 3.0, 0.9], [0, .34, 0]],
  [42.0, [0.15, 2.45, 0.7], [0, .34, 0]],
  [47.0, [2.75, .85, 1.55], [1.55, .44, 0]],
  [57.5, [2.35, .7, 1.15], [1.58, .46, 0]],
  [64.0, [4.8, 2.4, 6.0], [0.3, .4, 0]],
  [88.0, [8.2, 3.9, 9.4], [0.2, .5, 0]],
];
function camAt(t) {
  t = Math.max(0, Math.min(DUR, t));
  let i = 0; while (i < K.length - 2 && t > K[i + 1][0]) i++;
  const [t0, p0, a0] = K[i], [t1, p1, a1] = K[i + 1];
  const pm = K[Math.max(0, i - 1)], pn = K[Math.min(K.length - 1, i + 2)];
  const u = (t - t0) / (t1 - t0), dt = t1 - t0;
  const tan = (prev, next, idx) => (next[0] - prev[0]) > 0 ? (next[idx].map((v, k) => (v - prev[idx][k]) / (next[0] - prev[0]))) : [0, 0, 0];
  const out = idx => {
    const m0 = i === 0 ? [0, 0, 0] : tan(pm, K[i + 1], idx), m1 = i + 1 === K.length - 1 ? [0, 0, 0] : tan(K[i], pn, idx);
    const u2 = u * u, u3 = u2 * u, h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
    const A = K[i][idx], B = K[i + 1][idx];
    return A.map((v, k) => h00 * v + h10 * dt * m0[k] * .8 + h01 * B[k] + h11 * dt * m1[k] * .8);
  };
  return [out(1), out(2)];
}

// ---------- 2D overlay (titles, labels, subtitles) ----------
const out = document.createElement('canvas'); out.width = W; out.height = H; document.body.appendChild(out);
renderer.domElement.style.display = 'none'; document.body.appendChild(renderer.domElement);
const g2 = out.getContext('2d');
const S = W / 1920;
const SUBS = [
  [0.3, 14.1, 'Tonight, in the quiet hour before dawn in old Rome, one small clay lamp is still burning. We’ll follow its soft light, slowly, piece by piece, until your eyes grow heavy.'],
  [14.1, 19.6, 'Plate three. The oil lamp, in Latin, lucerna.'],
  [21.6, 29.2, 'At the back, a small ring, just wide enough for one finger, to carry the light from room to room.'],
  [33.7, 42.0, 'In the middle of the shallow dish, a little hole, where olive oil was poured in, slowly, so it would not spill.'],
  [43.3, 50.8, 'And at the narrow end, a twist of linen drew up the oil, and held one small, steady flame.'],
  [58.85, 67.5, 'Made by the thousand in clay moulds, lamps like this kept the long Roman nights soft, and warm, and quiet.'],
];
const LABELS = [
  [22.0, 32.5, 'FIG. I · HANDLE', 'ansa'],
  [34.0, 42.4, 'FIG. II · FILLING HOLE', 'infundibulum'],
  [44.0, 56.5, 'FIG. III · NOZZLE', 'rostrum'],
];
const fadeIO = (t, a, b, f = .8) => Math.max(0, Math.min(1, (t - a) / f, (b - t) / f));
function wrap(text, maxW) { const words = text.split(' '), lines = []; let cur = ''; for (const w of words) { const n = cur ? cur + ' ' + w : w; if (g2.measureText(n).width > maxW && cur) { lines.push(cur); cur = w; } else cur = n; } if (cur) lines.push(cur); return lines; }
function overlay(t) {
  g2.clearRect(0, 0, W, H); g2.drawImage(renderer.domElement, 0, 0);
  g2.textAlign = 'center'; g2.textBaseline = 'alphabetic';
  // title card
  const ta = fadeIO(t, 14.0, 20.4, 1.2);
  if (ta > 0) {
    g2.globalAlpha = ta; g2.fillStyle = '#f3e3c8'; g2.shadowColor = 'rgba(0,0,0,.8)'; g2.shadowBlur = 18 * S;
    g2.font = `500 ${78 * S}px Bodoni`; g2.letterSpacing = `${10 * S}px`; g2.fillText('THE OIL LAMP', W / 2, H * .2);
    g2.letterSpacing = '0px'; g2.font = `${58 * S}px Pinyon`; g2.fillStyle = '#e6b77a'; g2.fillText('Lucerna', W / 2, H * .2 + 72 * S);
    g2.font = `italic ${26 * S}px BodoniI`; g2.fillStyle = '#cdbb9c'; g2.fillText('Plate III · Rome, the first century', W / 2, H * .2 + 118 * S);
  }
  // detail labels, top-left
  for (const [a, b, name, lat] of LABELS) {
    const la = fadeIO(t, a, b, 1.0); if (la <= 0) continue;
    g2.globalAlpha = la; g2.textAlign = 'left'; g2.shadowColor = 'rgba(0,0,0,.85)'; g2.shadowBlur = 14 * S;
    const x = 110 * S, y = 150 * S, slide = (1 - la) * 20 * S;
    g2.fillStyle = '#f0dcbc'; g2.font = `500 ${34 * S}px Bodoni`; g2.letterSpacing = `${5 * S}px`; g2.fillText(name, x + slide, y);
    g2.letterSpacing = '0px'; g2.fillStyle = '#e6b77a'; g2.font = `${46 * S}px Pinyon`; g2.fillText(lat, x + slide, y + 56 * S);
    g2.globalAlpha = la * .7; g2.fillRect(x + slide, y + 18 * S - 56 * S - 22 * S, 60 * S * la, 2 * S);
    g2.textAlign = 'center';
  }
  // subtitles
  g2.shadowBlur = 0; g2.font = `italic ${36 * S}px BodoniI`;
  for (const [a, b, txt] of SUBS) {
    const sa = fadeIO(t, a, b + .4, .5); if (sa <= 0) continue;
    const lines = wrap(txt, 1250 * S), lh = 48 * S, y0 = H - 70 * S - (lines.length - 1) * lh;
    let mw = 0; for (const l of lines) mw = Math.max(mw, g2.measureText(l).width);
    g2.globalAlpha = sa * .55; g2.fillStyle = '#0b0705';
    const bx = W / 2 - mw / 2 - 30 * S, by = y0 - 44 * S, bw = mw + 60 * S, bh = lines.length * lh + 30 * S;
    g2.beginPath(); g2.roundRect(bx, by, bw, bh, 12 * S); g2.fill();
    g2.globalAlpha = sa; g2.fillStyle = '#f2e6d2';
    lines.forEach((l, k) => g2.fillText(l, W / 2, y0 + k * lh));
  }
  // end card
  const ea = Math.min(fadeIO(t, 70.5, 200, 2.0), 1);
  if (ea > 0) {
    g2.globalAlpha = ea; g2.fillStyle = '#f3e3c8'; g2.shadowColor = 'rgba(0,0,0,.9)'; g2.shadowBlur = 20 * S;
    g2.font = `${84 * S}px Pinyon`; g2.fillText('Slow History', W / 2, H * .44);
    g2.font = `500 ${28 * S}px Bodoni`; g2.letterSpacing = `${12 * S}px`; g2.fillStyle = '#d9b98a'; g2.fillText('FOR SLEEP', W / 2, H * .44 + 56 * S); g2.letterSpacing = '0px';
  }
  g2.globalAlpha = 1; g2.shadowBlur = 0;
}

// ---------- render(t) ----------
const tmpV = new THREE.Vector3();
function render(t) {
  seed = 7;
  const [p, a] = camAt(t);
  // a slow breathing drift so the camera never fully stops
  camera.position.set(p[0] + Math.sin(t * .23) * .06, p[1] + Math.sin(t * .31 + 1) * .04, p[2] + Math.cos(t * .19) * .06);
  camera.lookAt(a[0], a[1], a[2]);
  const fl = 1 + .1 * (fbm(t * 3.1) - .5) + .05 * (vnoise(t * 11) - .5);
  fire.intensity = 9 * fl; fire.position.copy(FLAME).add(tmpV.set((vnoise(t * 2) - .5) * .02, .02, (vnoise(t * 2 + 9) - .5) * .02));
  bounce.intensity = 3.2 * Math.min(1, Math.max(0, (t - 19) / 3), Math.max(0, (35 - t) / 3));
  flameMat.uniforms.uT.value = t;
  flame.position.copy(FLAME); flame.quaternion.copy(camera.quaternion); flame.scale.setScalar(.95 + .1 * fbm(t * 4));
  glow.position.copy(FLAME); glow.material.opacity = .45 * fl;
  for (let i = 0; i < ND; i++) {
    const [x, y, z, ph, sp] = dseed[i];
    let yy = (y + t * sp * .35) % 3.2;
    dpos[i * 3] = x + Math.sin(t * sp * 2 + ph) * .25; dpos[i * 3 + 1] = yy; dpos[i * 3 + 2] = z + Math.cos(t * sp * 1.7 + ph) * .25;
  }
  dgeo.attributes.position.needsUpdate = true;
  const fd = camera.position.distanceTo(tmpV.set(a[0], a[1], a[2]));
  bokeh.uniforms.focus.value = fd; bokeh.uniforms.aperture.value = .0035 / Math.max(fd, 1);
  grade.uniforms.uT.value = t;
  grade.uniforms.uFade.value = Math.min(1, t / 2.5, Math.max(0, (DUR - t) / 3));
  composer.render();
  overlay(t);
}

async function boot() {
  const fonts = [['Bodoni', 'BodoniModa-VF.ttf', {}], ['BodoniI', 'BodoniModa-Italic-VF.ttf', { style: 'normal' }], ['Pinyon', 'PinyonScript-Regular.ttf', {}]];
  for (const [n, f, o] of fonts) { const ff = new FontFace(n, `url(./fonts/${f})`, o); await ff.load(); document.fonts.add(ff); }
  render(0); render(0);
  window.READY = true;
}
window.DUR = DUR;
window.render = render;
window.frame = (t, qual = .92) => { render(t); return out.toDataURL('image/jpeg', qual); };
boot();
