// A Roman clay oil lamp (lucerna), seen from above as on an antiquities plate.
// Same contract as scallop.js: buildLamp({ x, y, s }) → { ink, regions, focus, center, s }.
import * as B from '../engine/burin.js';
const { ring, clamp, hatch, outline, stroke, RNG, noise2, sphereTone, formTone, ellipse, ellipsePts } = B;
const LV = [-0.55, -0.62];

export function buildLamp({ x = 960, y = 600, s = 1, seed = 21 } = {}) {
  const ink = new B.Ink(), P = ([u, v]) => [x + u * s, y + v * s], S = v => v * s;
  const C = [-70, 0], R = 245;
  const body = ellipse(...P(C), S(R), S(R * 0.96));
  // nozzle: a rounded tongue to the right, tucked behind the body
  const noz = []; for (let i = 0; i <= 40; i++) { const a = -Math.PI / 2 + Math.PI * i / 40; noz.push(P([300 + Math.cos(a) * 78, Math.sin(a) * 78])); }
  const nozzle = ring([P([60, -112]), P([200, -82]), ...noz, P([200, 82]), P([60, 112])]);
  // ring handle on the left
  const handle = ellipse(...P([-345, 0]), S(70), S(52)), hole = ellipse(...P([-352, 0]), S(30), S(20));
  const discus = ellipse(...P(C), S(158), S(152)), rim = ellipse(...P(C), S(178), S(171));
  const fill = ellipse(...P([C[0] + 2, 4]), S(19), S(18)), wick = ellipse(...P([304, 0]), S(30), S(28)), air = ellipse(...P([150, 0]), S(7), S(7));
  const petals = []; for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4 + Math.PI / 8, c = P([C[0] + Math.cos(a) * 88, Math.sin(a) * 88]); petals.push(B.ring(ellipsePts(c[0], c[1], S(52), S(21), a, 40))); }
  const bodyP = body.polys, behind = [...bodyP];
  // --- outlines (cut first)
  ink.group('ol0'); outline(ink, bodyP[0], { w: 2.6, light: LV, vary: 0.9, seed, run: 180 });
  ink.group('ol');
  outline(ink, nozzle.polys[0], { w: 2.2, light: LV, seed: seed + 1, excl: behind });
  outline(ink, handle.polys[0], { w: 2.0, light: LV, seed: seed + 2, excl: behind });
  outline(ink, hole.polys[0], { w: 1.6, light: [0.6, 0.7], seed: seed + 3 });
  outline(ink, rim.polys[0], { w: 1.5, light: [0.6, 0.7], seed: seed + 4 });
  outline(ink, discus.polys[0], { w: 1.9, light: [0.6, 0.7], seed: seed + 5 });
  for (const [i, p] of petals.entries()) outline(ink, p.polys[0], { w: 1.2, light: LV, seed: seed + 10 + i, run: 0 });
  for (const h of [fill, wick, air]) outline(ink, h.polys[0], { w: 1.8, light: [0.6, 0.7], seed: seed + 30 });
  // the channel from discus to nozzle
  stroke(ink, [P([95, -16]), P([170, -14]), P([262, -20])], 1.2); stroke(ink, [P([95, 16]), P([170, 14]), P([262, 20])], 1.2);
  // --- tone fields
  const tBody = formTone(bodyP, { light: LV, base: 0.04, k: 0.95 });
  const tDisc = sphereTone(...P(C), S(160), S(155), { L: { x: 0.55, y: 0.6, z: 0.62 }, base: 0.02, k: 0.75 });   // dished: shadow falls on the lit side
  const tNoz = formTone(nozzle.polys, { light: LV, base: 0.12, k: 0.9 });
  const tHan = formTone(handle.polys, { light: LV, base: 0.1, k: 0.9 });
  const dark = () => 0.97;
  const holes = [fill, wick, air, hole].flatMap(h => h.polys), discX = [...discus.polys, ...petals.flatMap(p => p.polys), ...holes];
  const bodyTone = (px, py) => clamp(tBody(px, py) + 0.08 * (noise2(px / 30, py / 30, seed) - 0.5));
  ink.group('h1');
  hatch(ink, bodyP, { angle: -0.7, spacing: 4.2, tone: bodyTone, thr: 0.12, wMax: 1.7, seed: seed + 40, excl: discX });
  hatch(ink, nozzle.polys, { angle: -0.4, spacing: 4.2, tone: tNoz, thr: 0.12, wMax: 1.6, seed: seed + 41, excl: [...behind, ...wick.polys] });
  hatch(ink, handle.polys, { angle: -1.0, spacing: 4.0, tone: tHan, thr: 0.12, wMax: 1.5, seed: seed + 42, excl: [...behind, ...hole.polys] });
  hatch(ink, discus.polys, { angle: 0.6, spacing: 3.8, tone: tDisc, thr: 0.1, wMax: 1.4, seed: seed + 43, excl: [...petals.flatMap(p => p.polys), ...fill.polys] });
  for (const [i, p] of petals.entries()) { const tp = formTone(p.polys, { light: LV, base: 0.06, k: 0.9, res: 60 }); hatch(ink, p.polys, { angle: i * Math.PI / 4 + Math.PI / 8 + 1.57, spacing: 3.0, tone: tp, thr: 0.2, wMax: 1.1, seed: seed + 50 + i }); }
  ink.group('h2');
  hatch(ink, bodyP, { angle: 0.4, spacing: 4.6, tone: bodyTone, thr: 0.5, wMax: 1.3, seed: seed + 60, excl: discX });
  hatch(ink, nozzle.polys, { angle: 0.7, spacing: 4.6, tone: tNoz, thr: 0.5, wMax: 1.2, seed: seed + 61, excl: [...behind, ...wick.polys] });
  hatch(ink, discus.polys, { angle: -0.6, spacing: 4.2, tone: tDisc, thr: 0.45, wMax: 1.1, seed: seed + 62, excl: [...petals.flatMap(p => p.polys), ...fill.polys] });
  for (const h of [fill, wick, air, hole]) hatch(ink, h.polys, { angle: 0.3, spacing: 2.2, tone: dark, thr: 0.1, wMax: 1.3, taper: 2, seed: seed + 70 });
  ink.group('h3');
  hatch(ink, bodyP, { angle: -0.1, spacing: 5.2, tone: bodyTone, thr: 0.76, wMax: 1.0, seed: seed + 80, excl: discX });
  for (const h of [fill, wick, air, hole]) hatch(ink, h.polys, { angle: -1.2, spacing: 2.4, tone: dark, thr: 0.1, wMax: 1.1, taper: 2, seed: seed + 81 });
  // soot round the wick hole: fine stipple
  B.stipple(ink, nozzle.polys, { density: 0.05, tone: B.blobTone(...P([300, 0]), S(70), S(60), 0.9, 0.7), r: 0.8, seed: seed + 90, thr: 0.25, excl: wick.polys });
  const mk = list => { const p = new Path2D(); for (const sh of list) p.addPath(sh.path); return { path: p, polys: list.flatMap(sh => sh.polys), bbox: B.bboxOf(list.flatMap(sh => sh.polys)) }; };
  const soot = ellipse(...P([292, 0]), S(62), S(56));
  const regions = { body: mk([body, nozzle, handle]), discus: mk([discus, ...petals]), soot: mk([soot]) };
  const fp = (u, v, r) => { const [fx, fy] = P([u, v]); return { x: fx, y: fy, r: S(r) }; };
  const focus = { wick: fp(304, 0, 46), fill: fp(C[0] + 2, 4, 40), handle: fp(-352, 0, 48), petals: fp(C[0] + 70, -70, 44) };
  return { ink, regions, focus, center: [x, y], s };
}
