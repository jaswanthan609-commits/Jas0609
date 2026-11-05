// Mango-tree glass aviary walk-in. Deterministic: window.frame(t) renders time t (s) and returns a JPEG data URL.
import * as THREE from 'three';
import {Sky} from 'three/addons/objects/Sky.js';

const W = 1920, H = 1080, DUR = 42;
const renderer = new THREE.WebGLRenderer({antialias: true, preserveDrawingBuffer: true});
renderer.setSize(W, H); renderer.setPixelRatio(1);
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 0.95;
renderer.outputColorSpace = THREE.SRGBColorSpace;
const out = document.createElement('canvas'); out.width = W; out.height = H; document.body.appendChild(out);
const ctx = out.getContext('2d');

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(58, W / H, 0.04, 3000);

// ---------- helpers ----------
let seed = 12345;
const rnd = () => (seed = (seed * 16807) % 2147483647, (seed - 1) / 2147483646);
const R = (a, b) => a + (b - a) * rnd();
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const sstep = (a, b, x) => { const u = clamp((x - a) / (b - a)); return u * u * (3 - 2 * u); };
const lerp = (a, b, u) => a + (b - a) * u;
const TAU = Math.PI * 2;
const SPH = new THREE.SphereGeometry(1, 22, 16), SPHL = new THREE.SphereGeometry(1, 12, 8);
const std = (color, o = {}) => new THREE.MeshStandardMaterial({color, roughness: 0.7, metalness: 0, ...o});
function mesh(geo, mat, cast = true, recv = true) { const m = new THREE.Mesh(geo, mat); m.castShadow = cast; m.receiveShadow = recv; return m; }
function ell(rx, ry, rz, mat, x = 0, y = 0, z = 0, cast = true, lo = false) { const m = mesh(lo ? SPHL : SPH, mat, cast); m.scale.set(rx, ry, rz); m.position.set(x, y, z); return m; }
function box(w, h, d, mat, x = 0, y = 0, z = 0, cast = true) { const m = mesh(new THREE.BoxGeometry(w, h, d), mat, cast); m.position.set(x, y, z); return m; }
function rod(a, b, r0, r1, mat, seg = 8, cast = true) { // cylinder from point a to b
  const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), d = B.clone().sub(A), L = d.length();
  const m = mesh(new THREE.CylinderGeometry(r1, r0, L, seg), mat, cast);
  m.position.copy(A).addScaledVector(d, 0.5); m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize()); return m;
}
function ctex(w, h, draw, rep, srgb = true) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  if (rep) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep[0], rep[1]); }
  t.anisotropy = 8; return t;
}
const add = (o, p = scene) => (p.add(o), o);

// ---------- sky + light ----------
const sky = new Sky(); sky.scale.setScalar(2000); scene.add(sky);
const sun = new THREE.Vector3().setFromSphericalCoords(1, THREE.MathUtils.degToRad(90 - 30), THREE.MathUtils.degToRad(-35));
const su = sky.material.uniforms; su.turbidity.value = 2.6; su.rayleigh.value = 2.2; su.mieCoefficient.value = 0.004; su.mieDirectionalG.value = 0.85; su.sunPosition.value.copy(sun);
const pm = new THREE.PMREMGenerator(renderer); const envScene = new THREE.Scene(); const sky2 = new Sky(); sky2.scale.setScalar(1000); sky2.material.uniforms.sunPosition.value.copy(sun); envScene.add(sky2);
scene.environment = pm.fromScene(envScene).texture; scene.environmentIntensity = 0.55;
scene.fog = new THREE.Fog(0xcfdbd6, 70, 420);
add(new THREE.HemisphereLight(0xe4f0ff, 0x52683a, 0.75));
const sunL = new THREE.DirectionalLight(0xffe0b5, 3.1); sunL.position.copy(sun).multiplyScalar(60); sunL.target.position.set(0, 0, -6);
sunL.castShadow = true; sunL.shadow.mapSize.set(2048, 2048); const sc = sunL.shadow.camera; sc.left = -24; sc.right = 24; sc.top = 24; sc.bottom = -24; sc.near = 10; sc.far = 140;
sunL.shadow.bias = -0.0004; sunL.shadow.normalBias = 0.03; add(sunL); add(sunL.target);

// ---------- textures ----------
const grassTex = ctex(512, 512, (g, w, h) => {
  g.fillStyle = '#4b7a2e'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 26000; i++) { const x = R(0, w), y = R(0, h), l = R(3, 9); g.strokeStyle = `hsl(${R(78, 105)},${R(35, 60)}%,${R(22, 42)}%)`; g.lineWidth = R(0.8, 1.8); g.beginPath(); g.moveTo(x, y); g.lineTo(x + R(-2, 2), y - l); g.stroke(); }
}, [0.16, 0.16]);
const paveTex = ctex(512, 512, (g, w, h) => {
  g.fillStyle = '#c9b89a'; g.fillRect(0, 0, w, h);
  for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) { g.fillStyle = `hsl(${R(30, 40)},${R(18, 28)}%,${R(66, 76)}%)`; g.fillRect(x * 128 + 3, y * 128 + 3, 122, 122); }
}, [1, 1]);
const marbleTex = ctex(1024, 1024, (g, w, h) => {
  g.fillStyle = '#f1eee8'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 70; i++) { g.strokeStyle = `rgba(120,115,110,${R(0.05, 0.22)})`; g.lineWidth = R(0.6, 2.4); g.beginPath(); let x = R(0, w), y = R(0, h); g.moveTo(x, y); for (let k = 0; k < 6; k++) { x += R(-120, 160); y += R(-60, 90); g.quadraticCurveTo(x + R(-40, 40), y + R(-40, 40), x, y); } g.stroke(); }
  g.strokeStyle = '#c6a04c'; g.lineWidth = 6; for (let k = 0; k <= 2; k++) { g.beginPath(); g.moveTo(0, k * 512); g.lineTo(w, k * 512); g.stroke(); g.beginPath(); g.moveTo(k * 512, 0); g.lineTo(k * 512, h); g.stroke(); }
}, [1, 1]);
const stoneTex = ctex(256, 256, (g, w, h) => { g.fillStyle = '#7b736a'; g.fillRect(0, 0, w, h); for (let i = 0; i < 3000; i++) { g.fillStyle = `rgba(${R(60, 160)},${R(60, 150)},${R(55, 140)},0.35)`; g.fillRect(R(0, w), R(0, h), R(1, 4), R(1, 4)); } }, [2, 2]);
const waterN = ctex(256, 256, (g, w, h) => {
  const img = g.createImageData(w, h); const hf = (x, y) => Math.sin(TAU * (3 * x + y)) * 0.5 + Math.sin(TAU * (-2 * x + 5 * y)) * 0.35 + Math.sin(TAU * (7 * x - 4 * y)) * 0.18 + Math.sin(TAU * (11 * x + 9 * y)) * 0.08;
  for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) { const x = i / w, y = j / h, e = 1 / w; const dx = (hf(x + e, y) - hf(x - e, y)) / (2 * e) * 0.012, dy = (hf(x, y + e) - hf(x, y - e)) / (2 * e) * 0.012; const n = new THREE.Vector3(-dx, -dy, 1).normalize(); const k = (j * w + i) * 4; img.data[k] = (n.x * 0.5 + 0.5) * 255; img.data[k + 1] = (n.y * 0.5 + 0.5) * 255; img.data[k + 2] = (n.z * 0.5 + 0.5) * 255; img.data[k + 3] = 255; }
  g.putImageData(img, 0, 0);
}, [3, 3], false);
const fallTex = ctex(64, 256, (g, w, h) => { g.fillStyle = 'rgba(255,255,255,0)'; g.clearRect(0, 0, w, h); for (let i = 0; i < 90; i++) { const x = R(0, w); g.strokeStyle = `rgba(235,248,255,${R(0.25, 0.8)})`; g.lineWidth = R(1, 3); g.beginPath(); g.moveTo(x, R(-40, h)); g.lineTo(x + R(-1, 1), R(0, h) + 60); g.stroke(); } }, [1, 1]);
const dotTex = ctex(64, 64, (g) => { const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32); gr.addColorStop(0, 'rgba(255,250,230,1)'); gr.addColorStop(1, 'rgba(255,250,230,0)'); g.fillStyle = gr; g.fillRect(0, 0, 64, 64); });
const shaftTex = ctex(64, 256, (g, w, h) => { const gr = g.createLinearGradient(0, 0, w, 0); gr.addColorStop(0, 'rgba(255,240,200,0)'); gr.addColorStop(0.5, 'rgba(255,240,200,1)'); gr.addColorStop(1, 'rgba(255,240,200,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, h); const v = g.createLinearGradient(0, 0, 0, h); v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(0.3, 'rgba(0,0,0,1)'); v.addColorStop(1, 'rgba(0,0,0,0)'); g.globalCompositeOperation = 'destination-in'; g.fillStyle = v; g.fillRect(0, 0, w, h); });

// ---------- materials ----------
const M = {
  grass: std(0xffffff, {map: grassTex, roughness: 0.95}), pave: std(0xffffff, {map: paveTex, roughness: 0.9}),
  marble: std(0xffffff, {map: marbleTex, roughness: 0.25}), marblePlain: std(0xf0ece4, {roughness: 0.3}),
  stone: std(0xffffff, {map: stoneTex, roughness: 0.95}), bark: std(0x5b4331, {roughness: 0.95}),
  frame: std(0x1d1b18, {metalness: 0.75, roughness: 0.35}), gold: std(0xd1a94e, {metalness: 1, roughness: 0.22}),
  glass: new THREE.MeshPhysicalMaterial({color: 0xd8eef2, transparent: true, opacity: 0.16, roughness: 0.03, metalness: 0, envMapIntensity: 2.2, side: THREE.DoubleSide, depthWrite: false, specularIntensity: 1}),
  wood: std(0x8a5a35, {roughness: 0.8}), white: std(0xf4f1ea, {roughness: 0.85}), houseWhite: std(0xece8df, {roughness: 0.9}),
  win: std(0x2a3d4f, {roughness: 0.15, metalness: 0.4}), black: std(0x111111, {roughness: 0.25}), roofTile: std(0x9c4a33, {roughness: 0.85}),
  water: new THREE.MeshStandardMaterial({color: 0x2a6662, transparent: true, opacity: 0.6, roughness: 0.06, metalness: 0.1, normalMap: waterN, normalScale: new THREE.Vector2(0.22, 0.22), envMapIntensity: 1.3, depthWrite: false}),
  chanWater: new THREE.MeshStandardMaterial({color: 0x3c6a63, roughness: 0.08, metalness: 0.1, normalMap: waterN, normalScale: new THREE.Vector2(0.4, 0.4), envMapIntensity: 1.4}),
  pondBed: std(0x4e5a47, {roughness: 1}), leafDark: std(0x1d3d16, {roughness: 0.9}),
};

// ---------- ground ----------
const PC = {x: 3, z: -7, rx: 3.6, rz: 3.0}; // pond
function groundShape(z0, z1, hole) { // world z range
  const s = new THREE.Shape(); s.moveTo(-220, -z1); s.lineTo(220, -z1); s.lineTo(220, -z0); s.lineTo(-220, -z0); s.closePath();
  if (hole) { const p = new THREE.Path(); p.absellipse(PC.x, -PC.z, PC.rx, PC.rz, 0, TAU, true); s.holes.push(p); }
  const g = new THREE.ShapeGeometry(s, 64); g.rotateX(-Math.PI / 2); return g;
}
add(mesh(groundShape(-220, 9.5, true), M.grass, false));
add(mesh(groundShape(12.5, 220, false), M.grass, false));
// channel + embankments
add(mesh(new THREE.PlaneGeometry(440, 3).rotateX(-Math.PI / 2), M.pondBed, false)).position.set(0, -1.1, 11);
add(mesh(new THREE.PlaneGeometry(440, 3).rotateX(-Math.PI / 2), M.chanWater, false)).position.set(0, -0.45, 11);
add(box(440, 1.2, 0.3, M.stone, 0, -0.5, 9.5, false)); add(box(440, 1.2, 0.3, M.stone, 0, -0.5, 12.5, false));
// paths
const path1 = add(mesh(new THREE.PlaneGeometry(2.2, 12).rotateX(-Math.PI / 2), M.pave, false)); path1.position.set(0, 0.012, 20.5); path1.material = path1.material.clone(); path1.material.map = paveTex.clone(); path1.material.map.repeat.set(1, 5.5); path1.material.map.needsUpdate = true;
const path2 = add(mesh(new THREE.PlaneGeometry(2.2, 7.5).rotateX(-Math.PI / 2), path1.material, false)); path2.position.set(0, 0.012, 3.75);

// ---------- bridge ----------
const deckY = z => 0.05 + 0.55 * Math.sin(Math.PI * clamp((z - 7.5) / 7));
const groundAt = (x, z) => (Math.abs(x) < 1.25 && z > 7.5 && z < 14.5) ? deckY(z) : 0;
for (let z = 7.55; z < 14.5; z += 0.25) { const s = add(box(2.3, 0.06, 0.22, std(new THREE.Color().setHSL(0.07, 0.45, R(0.28, 0.36))), 0, deckY(z), z)); s.rotation.x = -Math.atan(0.55 * Math.PI / 7 * Math.cos(Math.PI * (z - 7.5) / 7)); }
for (const sx of [-1.12, 1.12]) {
  const pts = [], pts2 = []; for (let z = 7.5; z <= 14.5; z += 0.35) { pts.push(new THREE.Vector3(sx, deckY(z) + 0.95, z)); pts2.push(new THREE.Vector3(sx, deckY(z) - 0.12, z)); }
  add(mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 60, 0.045, 8), M.wood));
  add(mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts2), 60, 0.11, 8), M.wood));
  for (let z = 7.6; z <= 14.5; z += 1.15) add(rod([sx, deckY(z), z], [sx, deckY(z) + 0.95, z], 0.05, 0.05, M.wood));
}

// ---------- house (from the satellite view: white flat roofs, round drum, red-tiled patch) ----------
{ const hx = -21, hz = -6;
  add(box(12, 7, 11, M.houseWhite, hx, 3.5, hz)); add(box(12.4, 0.5, 11.4, M.houseWhite, hx, 7.25, hz));
  add(box(7, 3.5, 6, M.houseWhite, hx - 2, 9, hz - 1));
  const drum = add(mesh(new THREE.CylinderGeometry(3, 3, 7.6, 40), M.houseWhite)); drum.position.set(hx + 5.5, 3.8, hz + 4.5);
  add(mesh(new THREE.CylinderGeometry(3.15, 3.15, 0.4, 40), M.houseWhite)).position.set(hx + 5.5, 7.7, hz + 4.5);
  const rt = add(box(4.5, 0.4, 4, M.roofTile, hx + 4, 4.2, hz + 7.5)); rt.rotation.x = 0.25; add(box(4.5, 4, 3.6, M.houseWhite, hx + 4, 2, hz + 7.3));
  for (let i = 0; i < 4; i++) for (let j = 0; j < 2; j++) add(box(1.3, 1.6, 0.1, M.win, hx - 4.5 + i * 3, 2 + j * 3.2, hz + 5.52, false));
  for (let i = 0; i < 4; i++) { const a = 0.2 + i * 0.45; add(box(0.9, 1.6, 0.1, M.win, hx + 5.5 + Math.sin(a) * 3.02, 2 + (i % 2) * 3, hz + 4.5 + Math.cos(a) * 3.02, false)).rotation.y = a; }
}
// spinning mill shed behind
add(box(30, 6, 14, std(0xb9bcbf, {roughness: 0.6, metalness: 0.3}), 24, 3, -38));
add(box(30, 6, 14, std(0x9fa3a6, {roughness: 0.6, metalness: 0.3}), -18, 3, -44));
// compound walls
const wallM = std(0xdccfb8, {roughness: 0.95});
add(box(80, 2, 0.3, wallM, 0, 1, 30)); add(box(80, 2, 0.3, wallM, 0, 1, -30)); add(box(0.3, 2, 60, wallM, 40, 1, 0)); add(box(0.3, 2, 60, wallM, -40, 1, 0));
for (let i = 0; i < 40; i++) { const x = R(-38, 38), z = rnd() < 0.5 ? R(26, 29) : R(-29, -24); add(ell(R(0.8, 1.6), R(0.7, 1.2), R(0.8, 1.6), std(new THREE.Color().setHSL(R(0.24, 0.3), 0.45, R(0.18, 0.3)), {flatShading: true}), x, 0.6, z, true, true)); }

// ---------- trees ----------
const leafGeo = (() => { const s = new THREE.Shape(); s.moveTo(0, 0); s.quadraticCurveTo(0.06, 0.14, 0, 0.3); s.quadraticCurveTo(-0.06, 0.14, 0, 0); return new THREE.ShapeGeometry(s, 3); })();
const leafMat = std(0xffffff, {roughness: 0.5, side: THREE.DoubleSide});
function mangoTree(x, z, h, spread, n = 2600, extraBranch) {
  const g = add(new THREE.Group()); g.position.set(x, 0, z);
  g.add(rod([0, 0, 0], [0, 3.1, 0], 0.42, 0.26, M.bark, 12));
  const blobs = [];
  for (let i = 0; i < 6; i++) {
    const a = i * TAU / 6 + R(-0.3, 0.3), r = spread * R(0.45, 0.62), ey = h - R(2.0, 3.2);
    g.add(rod([0, 2.8, 0], [Math.cos(a) * r, ey, Math.sin(a) * r], 0.2, 0.08, M.bark, 8));
    blobs.push([Math.cos(a) * r, ey + 0.4, Math.sin(a) * r, R(1.3, 1.8)]);
  }
  blobs.push([0, h - 1.5, 0, 1.45]);
  for (let i = 0; i < 9; i++) { const a = R(0, TAU), r = R(0.2, spread * 0.7); const rr = R(1.0, 1.6); blobs.push([Math.cos(a) * r, Math.min(h - rr, R(h * 0.55, h - 1.6)), Math.sin(a) * r, rr]); }
  if (extraBranch) g.add(rod([0, 2.9, 0], extraBranch, 0.13, 0.06, M.bark, 8));
  const ico = new THREE.IcosahedronGeometry(1, 2);
  for (const [bx, by, bz, br] of blobs) { const m = mesh(ico, M.leafDark); m.position.set(bx, by, bz); m.scale.setScalar(br * 0.92); g.add(m); }
  const inst = new THREE.InstancedMesh(leafGeo, leafMat, n); inst.castShadow = true; inst.receiveShadow = true;
  const o = new THREE.Object3D(), c = new THREE.Color();
  for (let i = 0; i < n; i++) {
    const [bx, by, bz, br] = blobs[Math.floor(rnd() * blobs.length)]; const v = new THREE.Vector3(R(-1, 1), R(-1, 1), R(-1, 1)).normalize();
    o.position.set(bx + v.x * br * R(0.92, 1.1), by + v.y * br * R(0.92, 1.1), bz + v.z * br * R(0.92, 1.1));
    o.rotation.set(R(0, TAU), R(0, TAU), R(0, TAU)); o.scale.setScalar(R(0.9, 1.5)); o.updateMatrix(); inst.setMatrixAt(i, o.matrix);
    const k = rnd(); c.setHSL(k < 0.07 ? R(0.02, 0.06) : R(0.25, 0.33), k < 0.07 ? 0.5 : R(0.45, 0.7), k < 0.07 ? 0.3 : R(0.1, 0.24)); inst.setColorAt(i, c);
  }
  g.add(inst);
  for (let i = 0; i < 20; i++) { // mangoes
    const [bx, by, bz, br] = blobs[Math.floor(rnd() * blobs.length)]; const v = new THREE.Vector3(R(-1, 1), R(-1, -0.3), R(-1, 1)).normalize();
    const p = [bx + v.x * br * 0.95, by + v.y * br * 0.95, bz + v.z * br * 0.95];
    g.add(ell(0.07, 0.1, 0.065, std(new THREE.Color().setHSL(R(0.1, 0.2), 0.8, R(0.4, 0.5)), {roughness: 0.45}), p[0], p[1] - 0.12, p[2], true, true));
    g.add(rod(p, [p[0], p[1] - 0.04, p[2]], 0.008, 0.008, M.bark, 4, false));
  }
  return g;
}
const T1 = mangoTree(-6, -9, 8.6, 3.2, 6500, [2.6, 3.1, 1.3]);
mangoTree(6.4, -14, 8.7, 3.0, 6000);
mangoTree(-5, -15.6, 8.4, 2.6, 5000);
// outside trees + palms
mangoTree(-12, 18, 7.5, 3.0, 1800); mangoTree(13, 20, 8, 3.2, 1800); mangoTree(16, -4, 8.2, 3.0, 1800);
function palm(x, z, h) {
  const pts = []; const lean = R(-1, 1); for (let i = 0; i <= 8; i++) { const u = i / 8; pts.push(new THREE.Vector3(x + lean * u * u * 1.5, u * h, z + u * u * 0.6)); }
  add(mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 30, 0.16, 8), std(0x7a6a55, {roughness: 1})));
  const top = pts[8]; const fm = std(0x3d7a2a, {roughness: 0.8, side: THREE.DoubleSide});
  for (let i = 0; i < 12; i++) { const a = i * TAU / 12; const f = mesh(new THREE.PlaneGeometry(0.5, 3.4, 1, 6), fm); const pos = f.geometry.attributes.position; for (let k = 0; k < pos.count; k++) { const yy = pos.getY(k) + 1.7; pos.setZ(k, -0.12 * yy * yy); pos.setX(k, pos.getX(k) * (1 - yy / 3.6)); } f.geometry.translate(0, 1.7, 0); f.position.copy(top); f.rotation.set(0, a, 0); f.rotateX(1.15); add(f); }
}
palm(-15, 24, 11); palm(18, 26, 12); palm(-28, 10, 10); palm(24, 6, 11.5);

// ---------- aviary ----------
const X0 = -10, X1 = 10, Z0 = -18, Z1 = 0, EAVE = 8.6, RIDGE = 9.5;
const roofY = x => EAVE + (RIDGE - EAVE) * (1 - Math.abs(x) / 10);
const AV = add(new THREE.Group());
const glassM = M.glass;
function gableShape(withDoor) { const s = new THREE.Shape(); s.moveTo(X0, 0.4); s.lineTo(X1, 0.4); s.lineTo(X1, EAVE); s.lineTo(0, RIDGE); s.lineTo(X0, EAVE); s.closePath(); if (withDoor) { const p = new THREE.Path(); p.moveTo(-1.3, 0.3); p.lineTo(1.3, 0.3); p.lineTo(1.3, 3.2); p.lineTo(-1.3, 3.2); p.closePath(); s.holes.push(p); } return new THREE.ShapeGeometry(s); }
// doorway: shape with the hole cut from the plinth line; front glass from y=0.4
{ const f = mesh(gableShape(true), glassM, false, false); f.position.z = Z1; f.renderOrder = 5; AV.add(f);
  const b = mesh(gableShape(false), glassM, false, false); b.position.z = Z0; b.renderOrder = 5; AV.add(b);
  for (const sx of [X0, X1]) { const s = mesh(new THREE.PlaneGeometry(18, EAVE - 0.4), glassM, false, false); s.rotation.y = Math.PI / 2; s.position.set(sx, (EAVE + 0.4) / 2, (Z0 + Z1) / 2); s.renderOrder = 5; AV.add(s); }
  const L = Math.hypot(10, RIDGE - EAVE), ang = Math.atan2(RIDGE - EAVE, 10);
  for (const sgn of [-1, 1]) { const r = mesh(new THREE.PlaneGeometry(L, 18), glassM, false, false); r.rotation.x = -Math.PI / 2; r.rotation.y = sgn * -ang; r.position.set(sgn * 5, (EAVE + RIDGE) / 2, (Z0 + Z1) / 2); r.renderOrder = 5; AV.add(r);
    for (let z = Z0; z <= Z1 + 0.01; z += 2) { const rf = box(L, 0.1, 0.08, M.frame, sgn * 5, (EAVE + RIDGE) / 2 - 0.05, z); rf.rotation.z = sgn * -ang; AV.add(rf); }
    for (const u of [0.33, 0.66]) { AV.add(box(0.08, 0.08, 18, M.frame, sgn * 10 * (1 - u), EAVE + (RIDGE - EAVE) * u, (Z0 + Z1) / 2)); }
  }
  AV.add(box(0.14, 0.14, 18.1, M.gold, 0, RIDGE + 0.02, (Z0 + Z1) / 2));
  for (const z of [Z0, Z1]) AV.add(ell(0.22, 0.3, 0.22, M.gold, 0, RIDGE + 0.32, z));
  // side wall mullions + transoms
  for (const sx of [X0, X1]) { for (let z = Z0; z <= Z1 + 0.01; z += 2) AV.add(box(0.09, EAVE, 0.09, M.frame, sx, EAVE / 2, z)); for (const y of [3.2, 5.9]) AV.add(box(0.07, 0.07, 18, M.frame, sx, y, (Z0 + Z1) / 2)); AV.add(box(0.16, 0.16, 18.1, M.gold, sx, EAVE, (Z0 + Z1) / 2)); }
  for (const z of [Z0, Z1]) {
    for (let x = X0 + 2; x < X1 - 0.01; x += 2) { if (z === Z1 && Math.abs(x) < 1.4) { AV.add(box(0.09, roofY(x) - 3.2, 0.09, M.frame, x, (roofY(x) + 3.2) / 2, z)); continue; } AV.add(box(0.09, roofY(x), 0.09, M.frame, x, roofY(x) / 2, z)); }
    for (const y of [3.2, 5.9]) AV.add(box(20, 0.07, 0.07, M.frame, 0, y, z));
    for (const sgn of [-1, 1]) { const e = box(Math.hypot(10, RIDGE - EAVE), 0.14, 0.14, M.gold, sgn * 5, (EAVE + RIDGE) / 2, z); e.rotation.z = sgn * -Math.atan2(RIDGE - EAVE, 10); AV.add(e); }
  }
  // plinth
  const pm2 = M.marblePlain;
  AV.add(box(20.4, 0.4, 0.35, pm2, 0, 0.2, Z0)); AV.add(box(0.35, 0.4, 18.4, pm2, X0, 0.2, -9)); AV.add(box(0.35, 0.4, 18.4, pm2, X1, 0.2, -9));
  AV.add(box(8.7, 0.4, 0.35, pm2, -5.65, 0.2, Z1)); AV.add(box(8.7, 0.4, 0.35, pm2, 5.65, 0.2, Z1));
  AV.add(box(0.12, 3.25, 0.14, M.gold, -1.33, 1.62, Z1)); AV.add(box(0.12, 3.25, 0.14, M.gold, 1.33, 1.62, Z1)); AV.add(box(2.8, 0.14, 0.14, M.gold, 0, 3.25, Z1));
}
// sliding doors
const doors = [];
for (const s of [-1, 1]) { const d = new THREE.Group(); const gl = mesh(new THREE.PlaneGeometry(1.3, 3.15), glassM, false, false); gl.position.y = 1.6; gl.renderOrder = 6; d.add(gl);
  d.add(box(1.3, 0.06, 0.06, M.frame, 0, 0.05, 0)); d.add(box(1.3, 0.06, 0.06, M.frame, 0, 3.15, 0)); d.add(box(0.06, 3.15, 0.06, M.frame, -0.65, 1.6, 0)); d.add(box(0.06, 3.15, 0.06, M.frame, 0.65, 1.6, 0));
  d.add(box(0.035, 1.1, 0.035, M.gold, -s * 0.52, 1.25, 0.06)); d.position.set(s * 0.65, 0, Z1 + 0.08); add(d); doors.push([d, s]); }
// steps, pots, lanterns
add(box(3.4, 0.08, 1.0, M.marble, 0, 0.04, 0.5));
function topiary(x, z) { add(mesh(new THREE.CylinderGeometry(0.32, 0.24, 0.6, 20), std(0x2b2b2b, {roughness: 0.4, metalness: 0.3}))).position.set(x, 0.3, z); add(ell(0.42, 0.42, 0.42, std(0x2f6a28, {flatShading: true}), x, 0.95, z)); add(ell(0.3, 0.3, 0.3, std(0x356f2c, {flatShading: true}), x, 1.45, z)); }
topiary(-2.0, 0.7); topiary(2.0, 0.7);
const lampGlow = new THREE.MeshStandardMaterial({color: 0xffe6b0, emissive: 0xffc970, emissiveIntensity: 2.2});
function lantern(x, z, h = 1.4) { add(rod([x, 0, z], [x, h, z], 0.03, 0.025, M.frame)); add(box(0.2, 0.03, 0.2, M.gold, x, h + 0.02, z, false)); add(box(0.2, 0.03, 0.2, M.gold, x, h + 0.3, z, false)); add(mesh(new THREE.ConeGeometry(0.15, 0.1, 4), M.gold, false)).position.set(x, h + 0.36, z);
  for (const [dx, dz] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) add(box(0.015, 0.28, 0.015, M.gold, x + dx * 0.09, h + 0.16, z + dz * 0.09, false)); add(ell(0.045, 0.07, 0.045, lampGlow, x, h + 0.15, z, false)); }
lantern(-2.6, 0.9); lantern(2.6, 0.9); lantern(-1.3, -3.4, 1.1); lantern(4.9, -3.0, 1.1);
// inside walkway + seat deck
add(mesh(new THREE.PlaneGeometry(2.2, 3.4).rotateX(-Math.PI / 2), M.marble, false)).position.set(0, 0.01, -1.7);
{ const sm = M.marble.clone(); sm.map = marbleTex.clone(); sm.map.repeat.set(2, 0.7); sm.map.needsUpdate = true; add(mesh(new THREE.PlaneGeometry(5.4, 1.3).rotateX(-Math.PI / 2), sm, false)).position.set(2.4, 0.011, -3.05); }
// flower beds along inner walls
{ const n = 900, inst = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1), std(0xffffff, {roughness: 0.6}), n); const o = new THREE.Object3D(), c = new THREE.Color(); const hues = [0.97, 0.0, 0.12, 0.83, 0.58, 0.14];
  for (let i = 0; i < n; i++) { const side = Math.floor(rnd() * 3); const x = side === 0 ? R(-9.6, -8.6) : side === 1 ? R(8.6, 9.6) : R(-9.5, 9.5), z = side === 2 ? R(-17.6, -16.6) : R(-17.5, -0.6); o.position.set(x, R(0.15, 0.55), z); o.scale.setScalar(R(0.05, 0.09)); o.updateMatrix(); inst.setMatrixAt(i, o.matrix); c.setHSL(hues[Math.floor(rnd() * hues.length)], 0.75, R(0.5, 0.65)); inst.setColorAt(i, c); }
  add(inst);
  for (let i = 0; i < 70; i++) { const side = i % 3; const x = side === 0 ? R(-9.5, -8.7) : side === 1 ? R(8.7, 9.5) : R(-9.5, 9.5), z = side === 2 ? R(-17.5, -16.7) : R(-17.5, -0.8); add(ell(R(0.4, 0.7), R(0.3, 0.55), R(0.4, 0.7), std(new THREE.Color().setHSL(R(0.25, 0.33), 0.5, R(0.18, 0.28)), {flatShading: true}), x, 0.25, z, true, true)); }
}
// grass blades (instanced, swaying)
const gTime = {value: 0};
{ const geo = new THREE.ConeGeometry(0.016, 0.22, 3); geo.translate(0, 0.11, 0); const mat = std(0xffffff, {roughness: 0.9});
  mat.onBeforeCompile = sh => { sh.uniforms.uT = gTime; sh.vertexShader = 'uniform float uT;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n float sw = sin(uT*1.7 + instanceMatrix[3].x*0.9 + instanceMatrix[3].z*0.7)*0.06*position.y*3.0; transformed.x += sw; transformed.z += sw*0.5;'); };
  const n = 16000, inst = new THREE.InstancedMesh(geo, mat, n); const o = new THREE.Object3D(), c = new THREE.Color(); let k = 0;
  while (k < n) { let x, z; if (k < 11000) { x = R(-9.6, 9.6); z = R(-17.6, -0.3); if (Math.abs(x) < 1.2 && z > -3.4) continue; if (x > -0.4 && x < 5.2 && z > -3.75 && z < -2.35) continue; if (((x - PC.x) / (PC.rx + 0.5)) ** 2 + ((z - PC.z) / (PC.rz + 0.5)) ** 2 < 1) continue; } else { x = R(-8, 8); z = R(1, 28); if (Math.abs(x) < 1.25 || (z > 9.3 && z < 12.7)) continue; }
    o.position.set(x, 0, z); o.rotation.set(R(-0.25, 0.25), R(0, TAU), R(-0.25, 0.25)); o.scale.set(1, R(0.6, 1.4), 1); o.updateMatrix(); inst.setMatrixAt(k, o.matrix); c.setHSL(R(0.22, 0.3), R(0.4, 0.6), R(0.22, 0.38)); inst.setColorAt(k, c); k++; }
  inst.receiveShadow = true; add(inst); }

// light shafts + dust
const shafts = [];
{ const sm = new THREE.MeshBasicMaterial({map: shaftTex, transparent: true, opacity: 0.07, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, fog: false});
  const dir = sun.clone().normalize();
  for (const [x, z, w] of [[-2, -6, 1.6], [2.5, -10, 2.2], [-4, -12, 1.4], [5, -5, 1.2], [0.5, -14, 1.8]]) { const g = new THREE.Group(); for (const a of [0, Math.PI / 2]) { const p = new THREE.Mesh(new THREE.PlaneGeometry(w, 13), sm); p.rotation.y = a; g.add(p); } g.position.set(x, 0, z).addScaledVector(dir, 6.2); g.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir); add(g); shafts.push(g); } }
const dust = (() => { const n = 500, pos = new Float32Array(n * 3), base = []; for (let i = 0; i < n; i++) base.push([R(-9, 9), R(0.5, 8), R(-17, -0.5), R(0, TAU)]); const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); const p = new THREE.Points(g, new THREE.PointsMaterial({map: dotTex, size: 0.035, transparent: true, opacity: 0.8, depthWrite: false, blending: THREE.AdditiveBlending})); add(p); return {p, base, pos}; })();

// ---------- pond ----------
const pondY = -0.12;
{ const wall = mesh(new THREE.CylinderGeometry(1, 1, 0.95, 64, 1, true), std(0x5d5a50, {roughness: 1, side: THREE.BackSide}), false); wall.scale.set(PC.rx, 1, PC.rz); wall.position.set(PC.x, -0.47, PC.z); add(wall);
  const bed = mesh(new THREE.CircleGeometry(1, 64).rotateX(-Math.PI / 2), M.pondBed, false); bed.scale.set(PC.rx, 1, PC.rz); bed.position.set(PC.x, -0.9, PC.z); add(bed);
  for (let i = 0; i < 28; i++) { const a = R(0, TAU), r = Math.sqrt(rnd()) * 0.95; add(ell(R(0.04, 0.1), R(0.03, 0.05), R(0.04, 0.09), std(new THREE.Color().setHSL(R(0.06, 0.12), R(0.1, 0.25), R(0.08, 0.15))), PC.x + Math.cos(a) * r * PC.rx, -0.88, PC.z + Math.sin(a) * r * PC.rz, false, true)); }
  const wat = mesh(new THREE.CircleGeometry(1, 72).rotateX(-Math.PI / 2), M.water, false, true); wat.scale.set(PC.rx, 1, PC.rz); wat.position.set(PC.x, pondY, PC.z); wat.renderOrder = 2; add(wat);
  // rim: marble ledge on the front half, rocks on the back half
  for (let i = 0; i < 96; i++) { const a = i / 96 * TAU, a2 = (i + 1) / 96 * TAU; const front = Math.sin(a + TAU / 192) > 0.05;
    const p = [PC.x + Math.cos(a) * (PC.rx + 0.3), PC.z + Math.sin(a) * (PC.rz + 0.3)], q = [PC.x + Math.cos(a2) * (PC.rx + 0.3), PC.z + Math.sin(a2) * (PC.rz + 0.3)];
    if (front) { const L = Math.hypot(q[0] - p[0], q[1] - p[1]) + 0.02; const b = box(L, 0.17, 0.62, M.marblePlain, (p[0] + q[0]) / 2, 0.075, (p[1] + q[1]) / 2); b.rotation.y = -Math.atan2(q[1] - p[1], q[0] - p[0]); add(b);
      if (i % 2 === 0) { const gb = box(L * 2, 0.02, 0.03, M.gold, PC.x + Math.cos(a2) * (PC.rx + 0.0), 0.16, PC.z + Math.sin(a2) * (PC.rz + 0.0), false); gb.rotation.y = -Math.atan2(q[1] - p[1], q[0] - p[0]); add(gb); } }
    else { add(ell(R(0.25, 0.45), R(0.18, 0.32), R(0.25, 0.4), std(new THREE.Color().setHSL(R(0.07, 0.11), R(0.1, 0.2), R(0.2, 0.32)), {roughness: 0.95, flatShading: true}), p[0], 0.02, p[1], true, true)).rotation.y = R(0, TAU); } }
  // waterfall rock pile
  const wx = PC.x + 0.3, wz = PC.z - PC.rz - 0.5;
  for (let i = 0; i < 22; i++) add(ell(R(0.4, 0.8), R(0.3, 0.6), R(0.4, 0.7), std(new THREE.Color().setHSL(R(0.07, 0.1), 0.12, R(0.17, 0.27)), {roughness: 0.95, flatShading: true}), wx + R(-1.4, 1.4), R(0.1, 1.3) * (i < 8 ? 1 : 0.5), wz - R(0, 1.0), true, true)).rotation.set(R(0, 3), R(0, 3), 0);
  add(ell(0.9, 0.35, 0.7, std(0x4a443c, {roughness: 0.95, flatShading: true}), wx, 1.35, wz - 0.4));
}
const fall = mesh(new THREE.PlaneGeometry(0.9, 1.6), new THREE.MeshBasicMaterial({map: fallTex, transparent: true, opacity: 0.85, depthWrite: false, side: THREE.DoubleSide}), false, false);
fall.position.set(PC.x + 0.3, 0.62, PC.z - PC.rz + 0.12); fall.rotation.x = -0.18; add(fall);
// lotus
const padM = std(0x3f7d2e, {roughness: 0.55, side: THREE.DoubleSide}), petalM = std(0xf5a7c4, {roughness: 0.5}), petalM2 = std(0xfbd9e5, {roughness: 0.5});
const lotusItems = [];
for (let i = 0; i < 16; i++) { const a = R(0, TAU), r = R(0.6, 0.9); if (Math.sin(a) > 0.55 && Math.abs(Math.cos(a)) < 0.5) continue; const x = PC.x + Math.cos(a) * r * PC.rx, z = PC.z + Math.sin(a) * r * PC.rz; const s = R(0.22, 0.38);
  const pad = mesh(new THREE.CircleGeometry(s, 24, 0.3, TAU - 0.3).rotateX(-Math.PI / 2), padM, false, true); pad.position.set(x, pondY + 0.012, z); pad.rotation.y = R(0, TAU); add(pad); lotusItems.push([pad, R(0, TAU)]);
  if (i % 3 === 0) { const f = add(new THREE.Group()); f.position.set(x + R(-0.1, 0.1), pondY + 0.03, z + R(-0.1, 0.1)); for (let ring = 0; ring < 2; ring++) for (let k = 0; k < 8; k++) { const p = ell(0.045, 0.13, 0.025, ring ? petalM : petalM2, 0, 0, 0, false); const pv = new THREE.Group(); pv.rotation.y = k / 8 * TAU + ring * 0.4; p.position.set(0, 0.11, 0.0); pv.add(p); const tilt = new THREE.Group(); tilt.add(pv); pv.rotation.x = 0; p.rotation.x = 0; const holder = new THREE.Group(); holder.rotation.y = k / 8 * TAU + ring * 0.4; const inner = new THREE.Group(); inner.rotation.x = ring ? 0.75 : 0.35; const pm = ell(0.045, 0.13, 0.025, ring ? petalM : petalM2, 0, 0.11, 0, false); inner.add(pm); holder.add(inner); f.add(holder); }
    f.add(mesh(new THREE.CylinderGeometry(0.04, 0.03, 0.05, 12), std(0xf0d040), false)).position.y = 0.06; }
}

// ---------- animals ----------
const anim = []; // functions (t) => void
// birds
function bird(o) {
  const s = o.s, root = new THREE.Group(), torso = new THREE.Group(), head = new THREE.Group(); root.add(torso);
  const m = c => std(c, {roughness: 0.62});
  torso.add(ell(0.42 * s, 0.42 * s, 0.8 * s, m(o.body)));
  torso.add(ell(0.37 * s, 0.34 * s, 0.6 * s, m(o.belly), 0, -0.12 * s, 0.18 * s));
  const tg = new THREE.ConeGeometry(0.18 * s, o.tailLen * s, 6); tg.rotateX(-Math.PI / 2); tg.scale(1, 0.25, 1); const tail = mesh(tg, m(o.tail)); tail.position.set(0, 0.05 * s, -0.72 * s - o.tailLen * s / 2); torso.add(tail);
  head.position.set(0, 0.32 * s, 0.62 * s); torso.add(head);
  head.add(ell(0.37 * s, 0.37 * s, 0.4 * s, m(o.head), 0, 0.02 * s, 0.25 * s));
  if (o.face) for (const sx of [-1, 1]) head.add(ell(0.08 * s, 0.2 * s, 0.2 * s, m(o.face), sx * 0.3 * s, 0.0, 0.32 * s, false));
  for (const sx of [-1, 1]) { head.add(ell(0.065 * s, 0.065 * s, 0.065 * s, M.black, sx * 0.33 * s, 0.08 * s, 0.34 * s, false)); if (o.face) head.add(ell(0.03 * s, 0.03 * s, 0.03 * s, std(0xfff4c0), sx * 0.37 * s, 0.09 * s, 0.36 * s, false)); }
  if (o.bigBeak) { head.add(ell(0.17 * s, 0.22 * s, 0.75 * s, std(o.beak, {roughness: 0.35}), 0, -0.02 * s, 0.95 * s)); }
  else { const bg = new THREE.ConeGeometry(0.17 * s, 0.42 * s, 10); const bk = mesh(bg, std(o.beak, {roughness: 0.35})); bk.position.set(0, -0.06 * s, 0.68 * s); bk.rotation.x = Math.PI / 2 + 0.75; head.add(bk); head.add(ell(0.12 * s, 0.09 * s, 0.13 * s, std(o.beak, {roughness: 0.35}), 0, -0.18 * s, 0.56 * s, false)); }
  if (o.crest) for (let k = 0; k < 6; k++) { const c = mesh(new THREE.ConeGeometry(0.05 * s, 0.5 * s, 5), m(o.crest), false); c.position.set(R(-0.08, 0.08) * s, 0.4 * s, (0.1 - k * 0.06) * s); c.rotation.x = -0.5 - k * 0.12; head.add(c); }
  const wings = [];
  for (const sx of [-1, 1]) { const pv = new THREE.Group(); pv.position.set(sx * 0.34 * s, 0.17 * s, 0.22 * s); pv.add(ell(0.8 * s, 0.07 * s, 0.42 * s, m(o.wing), sx * 0.75 * s, 0, -0.15 * s)); pv.add(ell(0.62 * s, 0.05 * s, 0.32 * s, m(o.tip), sx * 1.55 * s, 0, -0.38 * s)); torso.add(pv); wings.push([pv, sx]); }
  const feet = new THREE.Group(); for (const sx of [-1, 1]) feet.add(ell(0.08 * s, 0.05 * s, 0.13 * s, std(0x4a4a4a), sx * 0.14 * s, -0.6 * s, 0.05 * s, false)); root.add(feet);
  root.traverse(c => { if (c.isMesh && s < 0.08) c.castShadow = false; });
  const B = {root, torso, head, wings, feet, s,
    pose(perched, t, ph) {
      feet.visible = perched;
      if (perched) { torso.rotation.x = -0.8; head.rotation.x = 0.75 + 0.12 * Math.sin(t * 1.3 + ph); head.rotation.y = 0.55 * Math.sin(t * 0.55 + ph) * Math.sin(t * 0.23 + ph * 2); head.rotation.z = 0.25 * Math.sin(t * 0.4 + ph);
        for (const [pv, sx] of wings) pv.rotation.set(0.15, sx * 1.42, sx * 0.2); }
      else { torso.rotation.x = 0; head.rotation.set(0.05, 0, 0); for (const [pv, sx] of wings) pv.rotation.set(0, 0, 0); }
    },
    flap(t, f, amp, ph) { for (const [pv, sx] of wings) { pv.rotation.set(0, 0, sx * -amp * Math.sin(t * f * TAU + ph) - sx * 0.1); } }
  };
  return B;
}
const SPECIES = {
  scarlet: {s: 0.2, body: 0xd7191c, belly: 0xcf1a1e, head: 0xd81e1e, face: 0xf3eee8, wing: 0xf2b927, tip: 0x1f4fbf, tail: 0xc8181c, beak: 0xe8dfd0, tailLen: 2.4},
  bluegold: {s: 0.2, body: 0x1e72d4, belly: 0xf6b300, head: 0x2a8c6a, face: 0xf3eee8, wing: 0x1c66c9, tip: 0x173f8a, tail: 0x1a5fc0, beak: 0x1a1a1a, tailLen: 2.4},
  greenwing: {s: 0.21, body: 0xb3141a, belly: 0xb3141a, head: 0xbd171d, face: 0xf3eee8, wing: 0x2f9a48, tip: 0x1d48a8, tail: 0xb11b20, beak: 0xe6dccc, tailLen: 2.3},
  grey: {s: 0.15, body: 0x8a8d90, belly: 0xa2a6a9, head: 0x8f9295, face: 0xdedede, wing: 0x7a7e82, tip: 0x505458, tail: 0xc8102e, beak: 0x141414, tailLen: 0.7},
  cockatoo: {s: 0.16, body: 0xf6f4ee, belly: 0xfbf9f2, head: 0xf8f6f0, wing: 0xf0eee8, tip: 0xf3efd8, tail: 0xf2f0e8, beak: 0x2b2b2b, tailLen: 0.9, crest: 0xf5d63a},
  toucan: {s: 0.15, body: 0x161616, belly: 0xf3efe6, head: 0x181818, wing: 0x141414, tip: 0x101010, tail: 0x151515, beak: 0xf08a16, tailLen: 0.9, bigBeak: true},
  budgie: {s: 0.06, body: 0x6cc04a, belly: 0x9be04f, head: 0xf5e04a, wing: 0x4e8c3a, tip: 0x2f4a2a, tail: 0x2a5aa8, beak: 0xd9c08a, tailLen: 1.6},
  budgieB: {s: 0.06, body: 0x5aa0e8, belly: 0x7cb8f0, head: 0xf4f4f4, wing: 0x4a7fbf, tip: 0x26324a, tail: 0x23408a, beak: 0xd9c08a, tailLen: 1.6},
  lovebird: {s: 0.065, body: 0x3fb04a, belly: 0x7fd35a, head: 0xf05a28, wing: 0x2f9a40, tip: 0x204a2a, tail: 0x3a7fd0, beak: 0xe0402a, tailLen: 0.8},
  finch: {s: 0.05, body: 0xb8a48a, belly: 0xf4efe6, head: 0xd23a2a, wing: 0x8a7258, tip: 0x3a2e24, tail: 0x2a2a2a, beak: 0xe8781e, tailLen: 0.9},
};
function perched(sp, x, y, z, yaw, ph) { const b = bird(SPECIES[sp]); b.root.position.set(x, y + 0.62 * b.s, z); b.root.rotation.y = yaw; add(b.root); anim.push(t => b.pose(true, t, ph)); b.pose(true, 0, ph); return b; }
function flyer(sp, pathFn, f, amp, ph, glide = 0) { const b = bird(SPECIES[sp]); add(b.root); b.pose(false, 0, 0); const P = new THREE.Vector3(), Q = new THREE.Vector3();
  anim.push(t => { pathFn(t, P); pathFn(t + 0.06, Q); b.root.position.copy(P); b.root.lookAt(Q); const v = Q.clone().sub(P); b.root.rotateZ(clamp(-v.x * 0.0, -0.5, 0.5) + (glide ? 0.22 * Math.sin(t * 0.5 + ph) : 0)); const g = glide ? sstep(0.2, 0.6, 0.5 + 0.5 * Math.sin(t * 0.35 + ph)) : 1; b.flap(t, f, amp * (0.25 + 0.75 * g), ph); }); return b; }
// T-perch near the walkway with a scarlet macaw
const PERCH = {x: -1.9, z: -2.9, h: 1.35};
add(rod([PERCH.x, 0, PERCH.z], [PERCH.x, PERCH.h, PERCH.z], 0.04, 0.035, M.gold)); add(mesh(new THREE.CylinderGeometry(0.28, 0.32, 0.05, 24), M.gold)).position.set(PERCH.x, 0.025, PERCH.z);
{ const bar = rod([PERCH.x - 0.45, PERCH.h, PERCH.z], [PERCH.x + 0.45, PERCH.h, PERCH.z], 0.035, 0.035, M.wood); add(bar); for (const sx of [-1, 1]) add(ell(0.1, 0.06, 0.1, std(0xd8c9a5), PERCH.x + sx * 0.45, PERCH.h + 0.02, PERCH.z, false)); }
perched('scarlet', PERCH.x - 0.18, PERCH.h + 0.035, PERCH.z, 0.55, 0.3);
perched('bluegold', PERCH.x + 0.22, PERCH.h + 0.035, PERCH.z, 0.9, 2.1);
// gold ring swing with an African grey
const RING = {x: 0.95, y: 2.5, z: -1.7};
const ringG = add(new THREE.Group()); ringG.position.set(RING.x, roofY(RING.x), RING.z);
{ const L = roofY(RING.x) - RING.y; ringG.add(rod([0, 0, 0], [0, -L + 0.3, 0], 0.01, 0.01, M.gold, 6)); const tor = mesh(new THREE.TorusGeometry(0.3, 0.025, 12, 40), M.gold); tor.position.y = -L; ringG.add(tor); }
const ringBird = bird(SPECIES.grey); ringBird.root.position.set(0, -(roofY(RING.x) - RING.y) - 0.3 + 0.025 + 0.62 * ringBird.s, 0); ringBird.root.rotation.y = 0.6; ringG.add(ringBird.root);
anim.push(t => { ringG.rotation.z = 0.06 * Math.sin(t * 1.1); ringG.rotation.x = 0.04 * Math.sin(t * 0.8); ringBird.pose(true, t, 1.2); });
// greys + others on mango branches (T1 extra branch runs from trunk (-6,-9) toward (-3.4,-7.7) at y≈3.1)
const brP = u => [-6 + 2.6 * u, 2.9 + 0.2 * u + 0.08, -9 + 1.3 * u];
{ let p = brP(0.82); perched('grey', p[0], p[1], p[2], 0.9, 0.5); p = brP(0.62); perched('grey', p[0], p[1], p[2], 1.4, 2.6); p = brP(0.42); perched('toucan', p[0], p[1], p[2], 1.2, 4.1); }
for (const [x, y, z, sp, yaw] of [[-4.3, 5.4, -7.3, 'greenwing', 1.0], [-3.9, 6.6, -10.5, 'cockatoo', 0.6], [4.4, 5.4, -12.2, 'bluegold', -0.6], [-3.6, 5.3, -14.6, 'cockatoo', 0.3], [5.0, 4.6, -15.0, 'grey', -0.2]]) {
  add(rod([x - 0.4, y, z - 0.1], [x + 0.4, y, z + 0.1], 0.04, 0.03, M.bark)); perched(sp, x, y + 0.03, z, yaw, x * 3);
}
// flying macaws
flyer('scarlet', (t, P) => { const a = t * 0.42 + 0.5; P.set(1.6 + Math.cos(a) * 4.6, 6.1 + 0.6 * Math.sin(2 * a), -7.5 + Math.sin(a) * 4.8); }, 2.6, 1.0, 0.0, 1);
flyer('bluegold', (t, P) => { const a = -t * 0.36 + 2.6; P.set(1.0 + Math.cos(a) * 5.4, 6.8 + 0.5 * Math.sin(3 * a), -8.5 + Math.sin(a) * 5.0); }, 2.3, 1.0, 1.3, 1);
flyer('greenwing', (t, P) => { const a = t * 0.3 + 4.0; P.set(1.5 + Math.sin(a) * 5.0, 7.3 + 0.4 * Math.sin(2 * a + 1), -9 + Math.sin(2 * a) * 3.2); }, 2.4, 1.0, 2.2, 1);
// small birds flitting
const smalls = ['budgie', 'budgieB', 'lovebird', 'finch', 'budgie', 'lovebird', 'budgieB', 'finch', 'budgie', 'lovebird', 'finch', 'budgie'];
smalls.forEach((sp, i) => { const cx = R(-6, 6), cy = R(2.5, 6.5), cz = R(-15, -4), r = R(1.2, 2.6), w = R(0.9, 1.5) * (i % 2 ? 1 : -1), ph = R(0, TAU);
  flyer(sp, (t, P) => { const a = t * w + ph; P.set(cx + Math.cos(a) * r + 0.4 * Math.sin(a * 2.3), cy + 0.5 * Math.sin(a * 1.7 + ph), cz + Math.sin(a) * r * 0.8); }, 9, 1.1, ph); });
for (let i = 0; i < 6; i++) { const sp = smalls[i]; const p = [[-1.0, 0.7, -0.7], [2.0, 1.0, -9.6], [-2.8, 0.55, -5.0], [5.6, 1.1, -8.0], [-0.6, 3.2, -11], [3.0, 3.0, -15]][i]; perched(sp, p[0], p[1], p[2], R(0, TAU), i); }

// ducks
function duck(kind) { const g = new THREE.Group(), body = new THREE.Group(); g.add(body); const white = kind === 'pekin';
  const bm = std(white ? 0xf6f3ea : 0x8b7e6a, {roughness: 0.8});
  body.add(ell(0.15, 0.12, 0.27, bm, 0, 0.12, 0)); body.add(ell(0.1, 0.08, 0.1, bm, 0, 0.17, -0.22)).rotation.x = -0.6;
  if (!white) body.add(ell(0.13, 0.1, 0.12, std(0x6b3b28), 0, 0.12, 0.17));
  body.add(rod([0, 0.18, 0.18], [0, 0.32, 0.22], 0.05, 0.045, white ? bm : std(0xf0ece2)));
  const hm = white ? bm : std(0x1d6b3e, {roughness: 0.35, metalness: 0.2}); body.add(ell(0.075, 0.072, 0.09, hm, 0, 0.36, 0.25));
  body.add(ell(0.035, 0.016, 0.06, std(white ? 0xf2981a : 0xe0c23a, {roughness: 0.5}), 0, 0.345, 0.34, false));
  for (const sx of [-1, 1]) body.add(ell(0.012, 0.012, 0.012, M.black, sx * 0.055, 0.37, 0.29, false));
  const feet = []; for (const sx of [-1, 1]) { const f = ell(0.035, 0.01, 0.05, std(0xf0901a), sx * 0.06, 0.005, 0.03, false); g.add(f); feet.push(f); }
  return {g, body, feet}; }
const ducks = [];
[['pekin', 1.5, 1.1, 0.33, 0], ['pekin', 1.1, 0.8, -0.28, 2], ['mallard', 1.9, 1.3, 0.22, 4]].forEach(([k, rx, rz, w, ph]) => { const d = duck(k); add(d.g); for (const f of d.feet) f.visible = false; ducks.push(d);
  anim.push(t => { const a = t * w + ph, b = (t + 0.1) * w + ph; const x = PC.x + 0.2 + Math.cos(a) * rx, z = PC.z - 0.2 + Math.sin(a) * rz; d.g.position.set(x, pondY - 0.07 + 0.01 * Math.sin(t * 2 + ph), z); d.g.lookAt(PC.x + 0.2 + Math.cos(b) * rx, d.g.position.y, PC.z - 0.2 + Math.sin(b) * rz); d.body.rotation.z = 0.04 * Math.sin(t * 1.5 + ph); d.wakeX = x; d.wakeZ = z; }); });
[[-1.6, -8.4, 0.9, 0.25, 0], [-0.9, -10.6, 0.7, -0.3, 1.7]].forEach(([cx, cz, r, w, ph]) => { const d = duck('pekin'); add(d.g);
  anim.push(t => { const a = t * w + ph, b = (t + 0.1) * w + ph; d.g.position.set(cx + Math.cos(a) * r, 0, cz + Math.sin(a) * r); d.g.lookAt(cx + Math.cos(b) * r, 0, cz + Math.sin(b) * r); const st = t * 5 + ph; d.body.rotation.z = 0.12 * Math.sin(st); d.body.position.y = 0.012 * Math.abs(Math.sin(st)); d.feet[0].position.z = 0.03 + 0.04 * Math.sin(st); d.feet[1].position.z = 0.03 - 0.04 * Math.sin(st); }); });

// rabbits
function rabbit(col, col2) { const g = new THREE.Group(), b = new THREE.Group(); g.add(b); const m = std(col, {roughness: 0.95}), m2 = std(col2 ?? col, {roughness: 0.95});
  b.add(ell(0.12, 0.11, 0.17, m, 0, 0.12, 0)); b.add(ell(0.125, 0.115, 0.12, m, 0, 0.115, -0.07));
  const hd = new THREE.Group(); hd.position.set(0, 0.17, 0.13); b.add(hd); hd.add(ell(0.075, 0.07, 0.085, m2, 0, 0.02, 0.04));
  for (const sx of [-1, 1]) { const e = ell(0.022, 0.1, 0.035, m2, sx * 0.035, 0.13, 0.0); e.rotation.z = sx * -0.18; e.rotation.x = -0.25; hd.add(e); hd.add(ell(0.013, 0.013, 0.013, M.black, sx * 0.05, 0.04, 0.09, false)); }
  hd.add(ell(0.012, 0.01, 0.01, std(0xe08a9a), 0, 0.01, 0.125, false)); b.add(ell(0.04, 0.04, 0.04, std(0xffffff), 0, 0.15, -0.18, false));
  return {g, b, hd}; }
[[0xf0ece6, null, -2.4, -5.6, 1.0, 0], [0x8a6040, null, -3.6, -6.8, 0.8, 1.5], [0x9a9a9a, null, -1.6, -7.4, 0.7, 3], [0xf2eee8, 0x2a2420, -0.7, -4.0, 0.5, 4.5], [0x6e5038, null, 5.8, -11, 0.9, 2.2], [0xf0ece6, 0x8a6040, -7.5, -4.2, 0.8, 5]].forEach(([c, c2, cx, cz, r, ph]) => { const rb = rabbit(c, c2); add(rb.g);
  anim.push(t => { const P = 3.4, u = ((t + ph * 1.3) % P) / P, cyc = Math.floor((t + ph * 1.3) / P); const hopU = clamp(u / 0.38); const a0 = cyc * 0.9 + ph, a = a0 + 0.9 * sstep(0, 1, hopU);
    rb.g.position.set(cx + Math.cos(a) * r, u < 0.38 ? 0.16 * Math.abs(Math.sin(hopU * 3 * Math.PI)) : 0, cz + Math.sin(a) * r); rb.g.rotation.y = -a; rb.b.rotation.x = u < 0.38 ? -0.25 * Math.sin(hopU * 3 * Math.PI) : 0;
    rb.hd.rotation.x = u >= 0.38 ? 0.45 + 0.12 * Math.sin(t * 9 + ph) * (u > 0.5 ? 1 : 0) : 0; }); });

// guinea pigs
function gpig(c1, c2, c3) { const g = new THREE.Group(), b = new THREE.Group(); g.add(b); const m1 = std(c1, {roughness: 1}), m2 = std(c2, {roughness: 1});
  b.add(ell(0.095, 0.08, 0.14, m1, 0, 0.08, 0)); b.add(ell(0.098, 0.082, 0.085, m2, 0, 0.082, -0.06));
  if (c3) b.add(ell(0.06, 0.05, 0.06, std(c3, {roughness: 1}), 0.04, 0.12, 0.02));
  const hd = new THREE.Group(); hd.position.set(0, 0.09, 0.11); b.add(hd); hd.add(ell(0.065, 0.06, 0.07, m1, 0, 0, 0.02));
  for (const sx of [-1, 1]) { hd.add(ell(0.028, 0.022, 0.008, std(0xc9907a), sx * 0.05, 0.05, -0.01, false)); hd.add(ell(0.012, 0.012, 0.012, std(0x0a0a0a, {roughness: 0.1}), sx * 0.048, 0.02, 0.06, false)); }
  const nose = ell(0.012, 0.009, 0.008, std(0xe3a1a1), 0, 0.0, 0.088, false); hd.add(nose); return {g, b, hd, nose}; }
const GP = [gpig(0xf4efe6, 0xc27a3a, 0x1c1a18), gpig(0xe8d3a8, 0xe8d3a8), gpig(0x5a3d28, 0xf2ede4)];
const CUSH = {x: 2.15, z: -3.45};
add(ell(0.34, 0.07, 0.28, std(0x1f6f6a, {roughness: 0.85}), CUSH.x, 0.2, CUSH.z)); add(ell(0.35, 0.02, 0.29, M.gold, CUSH.x, 0.17, CUSH.z, false));
add(ell(0.3, 0.07, 0.26, std(0x7a2a3a, {roughness: 0.85}), 3.95, 0.2, -3.42));
GP.forEach(p => add(p.g));
// legs (POV), appear when seated
const SEAT = {x: 3, z: -3.66, y: 0.16};
const skin = std(0x8a5636, {roughness: 0.6}), linen = std(0xc9b48f, {roughness: 0.95});
const legs = add(new THREE.Group()); const shins = [];
for (const sx of [-1, 1]) { const x = SEAT.x + sx * 0.13; legs.add(rod([x, SEAT.y + 0.08, SEAT.z + 0.1], [x, SEAT.y + 0.08, SEAT.z - 0.52], 0.072, 0.066, linen, 14));
  const kn = new THREE.Group(); kn.position.set(x, SEAT.y + 0.08, SEAT.z - 0.53); legs.add(kn); kn.add(ell(0.066, 0.066, 0.066, linen));
  kn.add(rod([0, 0, 0], [0, -0.1, -0.01], 0.068, 0.064, linen, 14)); kn.add(rod([0, -0.1, -0.01], [0, -0.62, -0.03], 0.052, 0.04, skin, 14));
  const ft = ell(0.045, 0.032, 0.11, skin, 0, -0.64, -0.06); kn.add(ft); shins.push(kn); }
// ripples + splash
const ringM = new THREE.MeshBasicMaterial({color: 0xffffff, transparent: true, opacity: 0.3, depthWrite: false, side: THREE.DoubleSide});
const ripples = []; function rippleSet(n) { const a = []; for (let i = 0; i < n; i++) { const r = new THREE.Mesh(new THREE.RingGeometry(0.93, 1, 48).rotateX(-Math.PI / 2), ringM.clone()); r.renderOrder = 3; add(r); a.push(r); } ripples.push(a); return a; }
const ripFeet = rippleSet(6), ripDuck = ducks.map(() => rippleSet(3)), ripFall = rippleSet(4);
const drops = []; for (let i = 0; i < 46; i++) { const d = ell(0.012, 0.012, 0.012, new THREE.MeshStandardMaterial({color: 0xe8f6ff, roughness: 0.05, transparent: true, opacity: 0.85}), 0, 0, 0, false); add(d); drops.push([d, R(-0.9, 0.9), R(1.2, 2.6), R(-0.9, 0.6), i % 2 ? -1 : 1, R(0, 0.12)]); }
function setRipples(set, x, z, t, start, interval, maxR, op) { set.forEach((r, i) => { const age = (t - start) + i * interval / set.length; if (t < start) { r.visible = false; return; } const a = age % interval; r.visible = true; r.position.set(x, pondY + 0.006, z); r.scale.setScalar(0.04 + a / interval * maxR); r.material.opacity = op * (1 - a / interval); }); }
// koi
function koiTex(kind) { return ctex(256, 128, (g, w, h) => { const base = {kohaku: '#f7f3ea', ogon: '#f2b53a', showa: '#1b1b1d', chagoi: '#9a6a3a', sanke: '#f7f3ea', orange: '#f26a1b'}[kind]; g.fillStyle = base; g.fillRect(0, 0, w, h);
  const blobs = kind === 'kohaku' || kind === 'sanke' ? '#e2381f' : kind === 'showa' ? '#e44a1f' : kind === 'orange' ? '#f7f3ea' : null;
  if (blobs) for (let i = 0; i < 6; i++) { g.fillStyle = blobs; g.beginPath(); g.ellipse(R(20, 236), R(30, 98), R(15, 40), R(18, 40), R(0, 3), 0, TAU); g.fill(); }
  if (kind === 'sanke' || kind === 'showa') for (let i = 0; i < 6; i++) { g.fillStyle = kind === 'showa' ? '#f7f3ea' : '#141414'; g.beginPath(); g.ellipse(R(20, 236), R(30, 98), R(6, 18), R(6, 14), 0, 0, TAU); g.fill(); }
  if (kind === 'ogon') { const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, 'rgba(255,240,180,0.5)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, h); } }); }
const kois = [];
['kohaku', 'ogon', 'showa', 'sanke', 'orange', 'kohaku', 'chagoi', 'ogon', 'orange', 'kohaku', 'sanke'].forEach((k, i) => {
  const s = R(0.8, 1.25), g = new THREE.Group(), body = new THREE.Group(); g.add(body); const mt = std(0xffffff, {map: koiTex(k), roughness: 0.35, metalness: k === 'ogon' ? 0.4 : 0});
  const bm = mesh(SPH, mt, false); bm.scale.set(0.085 * s, 0.07 * s, 0.26 * s); body.add(bm);
  const tail = new THREE.Group(); tail.position.z = -0.24 * s; body.add(tail); const fm = new THREE.MeshStandardMaterial({color: k === 'showa' ? 0x333333 : 0xf8e8d8, transparent: true, opacity: 0.75, side: THREE.DoubleSide, roughness: 0.4});
  const tg = new THREE.Shape(); tg.moveTo(0, 0); tg.lineTo(0.09 * s, -0.16 * s); tg.lineTo(0, -0.11 * s); tg.lineTo(-0.09 * s, -0.16 * s); tg.closePath(); const tm = new THREE.Mesh(new THREE.ShapeGeometry(tg), fm); tm.rotation.x = Math.PI / 2; tm.rotation.z = Math.PI; tm.rotation.set(-Math.PI / 2, 0, 0); tail.add(tm);
  for (const sx of [-1, 1]) { const f = new THREE.Mesh(new THREE.CircleGeometry(0.05 * s, 12), fm); f.rotation.x = -Math.PI / 2; f.position.set(sx * 0.09 * s, -0.02, 0.1 * s); body.add(f); }
  add(g); const ph = R(0, TAU), rx = R(0.35, 0.75), rz = R(0.3, 0.7), w = R(0.25, 0.45) * (i % 2 ? 1 : -1), d = R(-0.42, -0.24);
  kois.push({g, body, tail, ph, rx, rz, w, d, gather: i < 5, gx: SEAT.x + R(-0.45, 0.45), gz: SEAT.z - 0.75 - R(0.05, 0.6)}); });
// ---------- camera ----------
const KEYS = [ // t, x, z, eyeH, look x,y,z
  [0, 0.4, 24, 1.62, 0, 3.6, -8], [4.5, 0.2, 17.2, 1.62, 0, 3.4, -8], [7.6, 0, 11, 1.62, 0, 2.9, -6], [10.6, 0, 3.0, 1.62, 0, 2.2, -6],
  [13.0, 0, -0.7, 1.62, 0.7, 2.5, -4], [16.0, -0.55, -1.8, 1.6, -1.85, 1.62, -2.95], [19.6, -0.3, -2.5, 1.6, -3.2, 6.0, -10], [23.0, 0.3, -2.95, 1.6, -2.8, 0.45, -6.4],
  [26.0, 1.9, -3.0, 1.6, 4.0, 0.3, -7.6], [28.5, 3.0, -3.45, 1.6, 3.0, -0.25, -6.0], [30.6, 3.0, -3.66, 1.02, 3.0, -0.28, -5.2], [32.8, 3.0, -3.66, 1.02, 3.05, -0.3, -4.9],
  [35.0, 3.0, -3.66, 1.02, 2.0, 0.25, -3.6], [37.4, 3.0, -3.66, 1.02, 2.95, 0.05, -4.7], [39.0, 3.0, -3.66, 1.02, 2.95, 0.07, -4.7], [42, 3.0, -3.66, 1.02, 3.6, 6.4, -10.5]];
function herm(t, idx) { const K = KEYS; let i = 0; while (i < K.length - 2 && t > K[i + 1][0]) i++; const a = K[i], b = K[i + 1]; const dt = b[0] - a[0]; const u = clamp((t - a[0]) / dt);
  const tan = j => { if (j <= 0 || j >= K.length - 1) return 0; return (K[j + 1][idx] - K[j - 1][idx]) / (K[j + 1][0] - K[j - 1][0]); };
  const m0 = tan(i) * dt, m1 = tan(i + 1) * dt; const u2 = u * u, u3 = u2 * u; return (2 * u3 - 3 * u2 + 1) * a[idx] + (u3 - 2 * u2 + u) * m0 + (-2 * u3 + 3 * u2) * b[idx] + (u3 - u2) * m1; }
function camAt(t, P, L) { const x = herm(t, 1), z = herm(t, 2), eh = herm(t, 3); const x2 = herm(t + 0.05, 1), z2 = herm(t + 0.05, 2); const sp = Math.hypot(x2 - x, z2 - z) / 0.05;
  const bob = 0.022 * Math.sin(t * TAU * 1.75) * clamp(sp / 1.2); P.set(x + 0.01 * Math.sin(t * TAU * 0.875) * clamp(sp), groundAt(x, z) + eh + bob, z); L.set(herm(t, 4) + 0.03 * Math.sin(t * 0.7), herm(t, 5) + 0.02 * Math.sin(t * 0.9), herm(t, 6)); }

// ---------- frame ----------
const P = new THREE.Vector3(), L = new THREE.Vector3();
function update(t) {
  gTime.value = t; waterN.offset.set(t * 0.012, t * 0.008); M.chanWater.normalMap.offset.set(-t * 0.02, 0); fallTex.offset.y = t * 1.4;
  for (const [d, s] of doors) d.position.x = s * (0.65 + 1.3 * sstep(8.4, 10.8, t));
  for (const f of anim) f(t);
  // dust drift
  dust.base.forEach(([x, y, z, ph], i) => { dust.pos[i * 3] = x + 0.3 * Math.sin(t * 0.2 + ph); dust.pos[i * 3 + 1] = y + 0.25 * Math.sin(t * 0.15 + ph * 2); dust.pos[i * 3 + 2] = z + 0.3 * Math.cos(t * 0.18 + ph); }); dust.p.geometry.attributes.position.needsUpdate = true;
  lotusItems.forEach(([p, ph]) => { p.position.y = pondY + 0.012 + 0.004 * Math.sin(t * 1.3 + ph); });
  // koi
  for (const k of kois) { const a = t * k.w + k.ph, a2 = (t + 0.08) * k.w + k.ph; const gt = k.gather ? sstep(31.0, 34.5, t) : 0;
    const px = t => lerp(PC.x + Math.cos(t * k.w + k.ph) * k.rx * PC.rx, k.gx + 0.18 * Math.cos(t * 0.9 + k.ph), gt), pz = t => lerp(PC.z + Math.sin(t * k.w + k.ph) * k.rz * PC.rz, k.gz + 0.15 * Math.sin(t * 0.8 + k.ph), gt);
    k.g.position.set(px(t), lerp(k.d, -0.2, gt), pz(t)); k.g.lookAt(px(t + 0.15), k.g.position.y, pz(t + 0.15)); k.tail.rotation.y = 0.45 * Math.sin(t * 7 + k.ph); k.body.rotation.y = 0.08 * Math.sin(t * 7 + k.ph + 1.5); }
  // legs
  const legOn = t > 28.9; legs.visible = legOn; const dip = sstep(29.2, 30.4, t); for (const kn of shins) kn.rotation.x = lerp(1.35, 0.78, dip) + 0.05 * Math.sin(t * 0.9) * (t > 31 ? 1 : 0);
  setRipples(ripFeet.slice(0, 3), SEAT.x - 0.13, SEAT.z - 0.95, t, 30.25, 2.2, 0.6, 0.45); setRipples(ripFeet.slice(3), SEAT.x + 0.13, SEAT.z - 0.95, t, 30.4, 2.4, 0.6, 0.45);
  ducks.forEach((d, i) => setRipples(ripDuck[i], d.wakeX, d.wakeZ, t, 0, 1.8, 0.5, 0.28));
  setRipples(ripFall, PC.x + 0.3, PC.z - PC.rz + 0.35, t, 0, 1.2, 0.8, 0.4);
  drops.forEach(([d, vx, vy, vz, sx, del]) => { const a = t - 30.25 - del; d.visible = a > 0 && a < 0.9; if (d.visible) { d.position.set(SEAT.x + sx * 0.13 + vx * a * 0.6, pondY + vy * a - 4.9 * a * a, SEAT.z - 0.95 + vz * a * 0.6); if (d.position.y < pondY) d.visible = false; } });
  // guinea pigs: two huddle on the cushion, one walks onto the lap
  const g0 = GP[0], g1 = GP[1], g2 = GP[2];
  g0.g.position.set(CUSH.x - 0.06, 0.25, CUSH.z + 0.03); g0.g.rotation.y = 1.9; g1.g.position.set(CUSH.x + 0.1, 0.25, CUSH.z - 0.08); g1.g.rotation.y = 2.4;
  const br = 1 + 0.03 * Math.sin(t * 5); g0.b.scale.set(br, br, 1); g1.b.scale.set(1, 1 + 0.03 * Math.sin(t * 5 + 1), 1);
  g0.nose.position.y = 0.004 * Math.sin(t * 30); g1.nose.position.y = 0.004 * Math.sin(t * 28 + 1); g0.hd.rotation.y = 0.2 * Math.sin(t * 0.8); g1.hd.rotation.x = 0.1 * Math.sin(t * 0.6);
  { const way = [[2.3, 0.0, -2.2], [2.55, 0.0, -2.95], [2.62, 0.17, -3.42], [2.88, 0.3, -3.8], [2.96, 0.3, -3.92]]; const u = sstep(32.8, 37.2, t) * (way.length - 1); const i = Math.min(way.length - 2, Math.floor(u)), f = u - i; const A = way[i], B = way[i + 1];
    g2.g.position.set(lerp(A[0], B[0], f), lerp(A[1], B[1], f) + (u > 0 && u < way.length - 1 ? 0.012 * Math.abs(Math.sin(t * 14)) : 0), lerp(A[2], B[2], f)); g2.g.rotation.y = Math.atan2(B[0] - A[0], B[2] - A[2]) * (u < way.length - 1 ? 1 : 0) + (u >= way.length - 1.01 ? 0.25 : 0);
    g2.nose.position.y = 0.004 * Math.sin(t * 32); g2.hd.rotation.y = t > 37.2 ? 0.25 * Math.sin(t * 0.9) : 0; }
  camAt(t, P, L); camera.position.copy(P); camera.lookAt(L); camera.rotateZ(0.006 * Math.sin(t * 0.6));
}
function drawText(txt, sub, a, y) { if (a <= 0) return; ctx.save(); ctx.globalAlpha = a; ctx.textAlign = 'center'; ctx.shadowColor = 'rgba(0,0,0,0.55)'; ctx.shadowBlur = 24; ctx.fillStyle = '#fff8ea';
  ctx.font = "italic 500 92px Corm"; ctx.fillText(txt, W / 2, y); if (sub) { ctx.font = "600 30px Corm"; ctx.letterSpacing = '8px'; ctx.fillText(sub, W / 2, y + 62); } ctx.restore(); }
window.DUR = DUR;
window.frame = t => { update(t); renderer.render(scene, camera);
  ctx.filter = 'saturate(1.1) contrast(1.04)'; ctx.drawImage(renderer.domElement, 0, 0); ctx.filter = 'none';
  const vg = ctx.createRadialGradient(W / 2, H / 2, H * 0.45, W / 2, H / 2, H * 1.05); vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(10,6,0,0.42)'); ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
  drawText('The Mango Aviary', 'HOME', sstep(1.0, 2.4, t) * (1 - sstep(4.6, 6.0, t)), H * 0.8);
  drawText('Living the best life.', null, sstep(39.6, 40.8, t), H * 0.52);
  const fade = Math.max(1 - sstep(0, 1.2, t), sstep(DUR - 0.9, DUR, t)); if (fade > 0) { ctx.fillStyle = `rgba(0,0,0,${fade})`; ctx.fillRect(0, 0, W, H); }
  return out.toDataURL('image/jpeg', 0.92); };
document.fonts.load("italic 500 92px Corm").then(() => document.fonts.load("600 30px Corm")).then(() => { window.frame(0); window.READY = true; });
