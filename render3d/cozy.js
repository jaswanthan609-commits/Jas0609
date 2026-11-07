// Cozy Hours: a seamless-loop 3D window nook, built from a scene spec (?spec=<url-encoded JSON>).
// Everything that moves is periodic in LOOP seconds, so the loop can repeat for hours without a seam.
// window.frame(t) renders time t and returns a JPEG data URL; window.LOOP and window.FPS describe the loop.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const q = new URLSearchParams(location.search);
const spec = Object.assign({
  weather: 'rain',        // rain | snow | clear | autumn | autumn_rain
  time: 'night',          // night | dusk | dawn
  light: 'candle',        // candle | lamp
  fire: true,             // warm fireplace glow from the left
  outside: 'city',        // city | forest | sea | village
  wall: '#3b2b25', accent: '#8a3b2a', wood: '#5a3a22',
  props: ['books', 'mug', 'plant'],
  seed: 1, loop: 12, fps: 24,
  mess: 0,                // 0 = the finished nook, 1 = a dark, cluttered room (30 Days to Cozy, day 1)
  w: 1920, h: 1080,       // 1080x1920 for Shorts
}, JSON.parse(q.get('spec') || '{}'));
const W = +(q.get('w') || spec.w), H = +(q.get('h') || spec.h), PORTRAIT = H > W;
const LOOP = spec.loop, TAU = Math.PI * 2;
window.LOOP = LOOP; window.FPS = spec.fps;

let s0 = (spec.seed * 9301 + 49297) % 233280 || 7;
const rnd = () => ((s0 = (s0 * 16807) % 2147483647) / 2147483647);
const hash = n => { const s = Math.sin(n * 127.1 + spec.seed * 3.7) * 43758.5453; return s - Math.floor(s); };
// Periodic flicker: only whole-number frequencies of the loop, so frame(0) == frame(LOOP).
const flick = (ph, k) => (Math.sin(TAU * (7 * ph + hash(k))) * .5 + Math.sin(TAU * (13 * ph + hash(k + 1))) * .3
  + Math.sin(TAU * (29 * ph + hash(k + 2))) * .2);

// ---------- renderer ----------
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x050407);
const camera = new THREE.PerspectiveCamera(PORTRAIT ? 64 : 36, W / H, 0.05, 60);

function canvasTex(w, h, draw, srgb = true, rep = [1, 1]) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...rep); t.anisotropy = 8; return t;
}
const col = c => new THREE.Color(c);
const woodTex = canvasTex(1024, 512, (g, w, h) => {
  g.fillStyle = spec.wood; g.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += 2) { const k = rnd(); g.fillStyle = `rgba(${k < .5 ? '0,0,0' : '255,220,180'},${.03 + rnd() * .06})`; g.fillRect(0, y + Math.sin(y * .03) * 3, w, 2); }
  for (let i = 0; i < 2500; i++) { g.fillStyle = `rgba(0,0,0,${rnd() * .12})`; g.fillRect(rnd() * w, rnd() * h, 10 + rnd() * 50, 1); }
}, true, [2, 1]);
const plaster = canvasTex(512, 512, (g, w, h) => {
  g.fillStyle = spec.wall; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 500; i++) { g.fillStyle = `rgba(${rnd() < .5 ? '0,0,0' : '255,240,220'},${rnd() * .05})`; g.beginPath(); g.arc(rnd() * w, rnd() * h, 8 + rnd() * 40, 0, 7); g.fill(); }
}, true, [3, 2]);
const softDot = canvasTex(64, 64, g => {
  const r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(.4, 'rgba(255,255,255,.3)'); r.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = r; g.fillRect(0, 0, 64, 64);
});

// ---------- room: back wall with a window opening ----------
const WX = 1.15, WY0 = 0.95, WY1 = 2.45;   // window half-width, bottom, top
const wallMat = new THREE.MeshStandardMaterial({ map: plaster, roughness: .95 });
const woodMat = new THREE.MeshStandardMaterial({ map: woodTex, roughness: .7 });
function box(w, h, d, mat, x, y, z, shadow = true) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); m.position.set(x, y, z);
  m.castShadow = shadow; m.receiveShadow = true; scene.add(m); return m;
}
box(8, WY0, .2, wallMat, 0, WY0 / 2, -.1);
box(8, 4 - WY1, .2, wallMat, 0, WY1 + (4 - WY1) / 2, -.1);
box(4 - WX, WY1 - WY0, .2, wallMat, -WX - (4 - WX) / 2, (WY0 + WY1) / 2, -.1);
box(4 - WX, WY1 - WY0, .2, wallMat, WX + (4 - WX) / 2, (WY0 + WY1) / 2, -.1);
const fw = .07;
box(2 * WX + .1, fw, .14, woodMat, 0, WY1, -.05); box(2 * WX + .1, fw, .14, woodMat, 0, WY0, -.05);
box(fw, WY1 - WY0, .14, woodMat, -WX, (WY0 + WY1) / 2, -.05); box(fw, WY1 - WY0, .14, woodMat, WX, (WY0 + WY1) / 2, -.05);
box(.04, WY1 - WY0, .1, woodMat, 0, (WY0 + WY1) / 2, -.06); box(2 * WX, .04, .1, woodMat, 0, WY0 + (WY1 - WY0) * .62, -.06);
box(8, .1, 6, woodMat, 0, -.05, 2.8);                    // floor
// desk / window seat in front of the window
const DESK = .82;
box(2.9, .07, .8, woodMat, 0, DESK, .42);
box(.08, DESK, .7, woodMat, -1.35, DESK / 2, .42); box(.08, DESK, .7, woodMat, 1.35, DESK / 2, .42);
// curtains, softly folded, in the accent colour
const curtainMat = new THREE.MeshStandardMaterial({ color: col(spec.accent).lerp(col('#4a4a4e'), spec.mess), roughness: 1, side: THREE.DoubleSide });
for (const sx of [-1, 1]) {
  const g = new THREE.PlaneGeometry(.55, 2.3, 40, 1); const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) p.setZ(i, Math.sin(p.getX(i) * 28) * .03);
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, curtainMat); m.position.set(sx * (WX + .12), 1.75, .08); m.castShadow = true; scene.add(m);
}

// ---------- outside: sky, horizon, distant lights, weather (one shader plane) ----------
const SKY = {
  night: ['#060a18', '#141c34', '#ffcf8a'], dusk: ['#1d1838', '#c06a4a', '#ffd9a0'], dawn: ['#28304e', '#d9a07c', '#fff0d0'],
}[spec.time];
const outsideMat = new THREE.ShaderMaterial({
  uniforms: { uPh: { value: 0 }, uCam: { value: 0 }, uTop: { value: col(SKY[0]) }, uLow: { value: col(SKY[1]) }, uLamp: { value: col(SKY[2]) },
    uSeed: { value: spec.seed }, uSnow: { value: spec.weather === 'snow' ? 1 : 0 }, uRain: { value: spec.weather.includes('rain') ? 1 : 0 },
    uLeaves: { value: spec.weather.startsWith('autumn') ? 1 : 0 },
    uKind: { value: ['city', 'forest', 'sea', 'village'].indexOf(spec.outside) } },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader: `varying vec2 vUv; uniform float uPh,uCam,uSeed,uSnow,uRain,uKind,uLeaves; uniform vec3 uTop,uLow,uLamp;
    float h(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)) + uSeed*1.7)*43758.5453); }
    float n(float x){ float i=floor(x), f=fract(x); f=f*f*(3.-2.*f); return mix(h(vec2(i,0.)), h(vec2(i+1.,0.)), f); }
    void main(){
      vec2 uv=vUv; vec3 c=mix(uLow, uTop, smoothstep(.25,.95,uv.y));
      float horizon=.32 + (uKind==1.? .12*n(uv.x*9.)+.05*n(uv.x*31.) : uKind==2.? .0 : .06*n(uv.x*14.));
      if(uKind==0.){
        // three skyline layers; nearer layers slide further as the camera drifts (parallax) and sit darker,
        // farther ones fade into the haze, so the view outside has depth instead of one flat backdrop
        for(int l=0;l<3;l++){ float L=float(l); float x=uv.x+uCam*(.04+.09*L); float cols=14.+10.*(2.-L);
          float id=floor(x*cols); float top=.16+.07*L+.16*h(vec2(id,3.+L))*step(.35,h(vec2(id,7.+L)));
          top=top*(1.-.35*(2.-L)/2.);
          float b=step(uv.y, top); vec3 bc=mix(uLow*.75, uTop*.25, L/2.);
          c=mix(c, bc, b);
          vec2 w=vec2(fract(x*cols)*5., uv.y*90.); vec2 wi=floor(w);   // lit windows, a few per building
          vec2 fw=fract(w); float lit=step(.8,h(wi+id*13.+L))
            *smoothstep(.1,.25,fw.x)*smoothstep(.8,.65,fw.x)*smoothstep(.25,.4,fw.y)*smoothstep(.85,.7,fw.y);
          vec3 tint=mix(uLamp, vec3(1.,.75,.45), h(wi+5.));                    // some warmer, some paler rooms
          c+=tint*lit*b*step(uv.y, top-.012)*(.14+.12*L)*(.85+.15*sin(6.2831*(uPh+h(wi))));
        }
        c=mix(c, uLow*1.15, smoothstep(.34,.0,uv.y)*.25);   // low haze over the city
      }
      else c=mix(c, uTop*.3, step(uv.y, horizon));
      if(uKind==2.){ float sea=step(uv.y,.3); c=mix(c, uTop*.55 + .06*sin(uv.x*90.+uv.y*300.), sea); }
      // distant warm windows / lamps as soft bokeh
      for(int i=0;i<36;i++){ float fi=float(i); vec2 p=vec2(h(vec2(fi,1.)), (uKind==0.? .08+.3*h(vec2(fi,2.)) : .1+.2*h(vec2(fi,2.))));
        if(uKind==1. && h(vec2(fi,9.))>.25) continue;
        float tw=.75+.25*sin(6.2831*(uPh*float(1+i%3))+fi);
        float d=length((uv-p)*vec2(1.6,1.)); c+=uLamp*smoothstep(.022,.0,d)*.55*tw*h(vec2(fi,4.)); }
      // falling snow (periodic in the loop)
      if(uSnow>0.){ for(int l=0;l<3;l++){ float L=float(l)+1.; vec2 g=uv*vec2(18.,10.)*L; vec2 id=floor(g);
        float off=h(id+L); vec2 f=fract(vec2(g.x+.3*sin(6.2831*(uPh+off)), g.y+uPh*L*2.+off*10.))-.5;
        c+=vec3(.9)*smoothstep(.09/L,.0,length(f))*.6/L; } }
      // autumn leaves tumbling past (sparse, swaying, whole cells per loop so it is seamless)
      if(uLeaves>0.){ for(int l=0;l<2;l++){ float L=float(l)+1.; vec2 g=uv*vec2(7.,4.)*L; g.y+=uPh*L*2.; vec2 id=floor(g);
        if(h(id+L*3.)<.3) continue;
        vec2 f=fract(g)-.5; f.x+=.25*sin(6.2831*(uPh*L+h(id))); float a=6.2831*(uPh*L+h(id+1.));
        vec2 r=vec2(cos(a)*f.x-sin(a)*f.y, sin(a)*f.x+cos(a)*f.y);
        float leaf=smoothstep(.1/L,.02/L,length(r*vec2(1.,2.2)));
        c=mix(c, mix(vec3(.82,.3,.06),vec3(.95,.6,.14),h(id+7.))*(.7+.25*L), leaf); } }
      // far rain streaks
      if(uRain>0.){ vec2 g=vec2(uv.x*320., uv.y*30.+uPh*90.); float r=h(floor(g)); c+=vec3(.25,.3,.4)*step(.985,r)*fract(g.y)*.12; }
      gl_FragColor=vec4(c,1.);
    }`,
});
const outside = new THREE.Mesh(new THREE.PlaneGeometry(9, 5), outsideMat); outside.position.set(0, 1.9, -2.6); scene.add(outside);

// ---------- rain on the glass ----------
const glassMat = new THREE.ShaderMaterial({
  transparent: true, depthWrite: false,
  uniforms: { uPh: { value: 0 }, uOn: { value: spec.weather.includes('rain') ? 1 : 0 }, uFrost: { value: spec.weather === 'snow' ? 1 : 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader: `varying vec2 vUv; uniform float uPh,uOn,uFrost;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233)))*43758.5453); }
    void main(){
      float a=.06; vec3 c=vec3(.6,.7,.8);
      if(uOn>0.){ for(int l=0;l<2;l++){ float L=float(l)+1.; vec2 g=vUv*vec2(9.,4.)*L; vec2 id=floor(g); vec2 f=fract(g);
        float r=h(id+L*7.); float speed=floor(1.+r*2.);            // whole laps per loop: seamless
        float y=1.-fract(r*5.+uPh*speed); vec2 dp=vec2(.3+.4*h(id+3.), y);
        float drop=smoothstep(.07/L,.0,length((f-dp)*vec2(1.,.7)))*step(.35,h(id+11.));
        float trail=smoothstep(.02,.0,abs(f.x-dp.x))*step(dp.y,f.y)*(1.-f.y)*.5*step(.5,r);
        float still=smoothstep(.035,.0,length(f-vec2(h(id+9.),h(id+5.))))*step(.6,h(id+2.));
        a+= (drop*.55+trail*.18+still*.35)/L; } }
      if(uFrost>0.){ float e=min(min(vUv.x,1.-vUv.x),min(vUv.y,1.-vUv.y)); a+=smoothstep(.12,.0,e)*.45*(.6+.4*h(floor(vUv*300.))); c=vec3(.9); }
      gl_FragColor=vec4(c, min(a,.8));
    }`,
});
for (const [x0, x1] of [[-WX, 0], [0, WX]]) {
  const g = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, WY1 - WY0), glassMat);
  g.position.set((x0 + x1) / 2, (WY0 + WY1) / 2, -.04); scene.add(g);
}

// ---------- props ----------
const props = new Set(spec.props);
const flameMat = new THREE.ShaderMaterial({
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, uniforms: { uPh: { value: 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader: `varying vec2 vUv; uniform float uPh;
    void main(){ vec2 p=vUv-vec2(.5,.18); float sway=.04*sin(6.2831*(uPh*7.))+.02*sin(6.2831*(uPh*13.));
      p.x-=sway*p.y*2.; float body=length(p*vec2(3.2,1.25)); float f=smoothstep(.55,.0,body);
      vec3 c=mix(vec3(1.,.42,.08), vec3(1.,.93,.7), smoothstep(.25,.0,body)); c=mix(c, vec3(.25,.45,1.), smoothstep(.1,.0,length(p-vec2(0.,-.05)))*.5);
      gl_FragColor=vec4(c*f*1.6, f); }`,
});
let flame = null, FLAME = new THREE.Vector3();
const warm = new THREE.PointLight(0xffa560, 0, 7, 1.6); warm.castShadow = true; warm.shadow.mapSize.set(1024, 1024); warm.shadow.bias = -.002; scene.add(warm);
if (spec.light === 'candle') {
  const cx = .55 + rnd() * .25;
  const wax = new THREE.Mesh(new THREE.CylinderGeometry(.045, .05, .2, 32), new THREE.MeshStandardMaterial({ color: 0xf2e6d0, roughness: .5, emissive: 0x3a1a05 }));
  wax.position.set(cx, DESK + .135, .48); wax.castShadow = true; scene.add(wax);
  const dish = new THREE.Mesh(new THREE.CylinderGeometry(.11, .09, .02, 32), new THREE.MeshStandardMaterial({ color: 0x8a7a60, metalness: .6, roughness: .35 }));
  dish.position.set(cx, DESK + .045, .48); scene.add(dish);
  FLAME.set(cx, DESK + .29, .48);
  flame = new THREE.Mesh(new THREE.PlaneGeometry(.07, .16), flameMat); scene.add(flame);
} else if (spec.light === 'lamp') {
  const lx = .5 + rnd() * .2;
  const base = new THREE.Mesh(new THREE.CylinderGeometry(.03, .06, .24, 24), new THREE.MeshStandardMaterial({ color: 0x6a5030, metalness: .4, roughness: .4 }));
  base.position.set(lx, DESK + .155, .4); scene.add(base);
  const shade = new THREE.Mesh(new THREE.CylinderGeometry(.075, .14, .15, 32, 1, true),
    new THREE.MeshStandardMaterial({ color: 0xf0d8b0, emissive: 0xffb060, emissiveIntensity: .9, side: THREE.DoubleSide, roughness: .9 }));
  shade.position.set(lx, DESK + .32, .4); scene.add(shade);
  FLAME.set(lx, DESK + .29, .4);
}
if (props.has('books')) {
  let y = DESK + .035; const bx = -.85 + rnd() * .2;
  for (let i = 0; i < 4; i++) {
    const hgt = .04 + rnd() * .03, hue = new THREE.Color(spec.accent).offsetHSL((rnd() - .5) * .2, -.1, (rnd() - .5) * .25);
    const b = box(.34 - rnd() * .08, hgt, .24 - rnd() * .04, new THREE.MeshStandardMaterial({ color: hue, roughness: .8 }), bx + (rnd() - .5) * .05, y + hgt / 2, .45);
    b.rotation.y = (rnd() - .5) * .35; y += hgt;
  }
}
const steam = [];
if (props.has('mug')) {
  const mx = -.25 + rnd() * .2;
  const pts = []; for (let i = 0; i <= 12; i++) { const v = i / 12; pts.push(new THREE.Vector2(.055 + .005 * Math.sin(v * 3), v * .12)); }
  const mug = new THREE.Mesh(new THREE.LatheGeometry(pts, 40), new THREE.MeshStandardMaterial({ color: col(spec.accent).offsetHSL(0, -.2, .25), roughness: .45, side: THREE.DoubleSide }));
  mug.position.set(mx, DESK + .035, .55); mug.castShadow = true; scene.add(mug);
  const handle = new THREE.Mesh(new THREE.TorusGeometry(.035, .01, 12, 24), mug.material); handle.position.set(mx + .065, DESK + .1, .55); handle.rotation.y = Math.PI / 2; scene.add(handle);
  const tea = new THREE.Mesh(new THREE.CircleGeometry(.052, 32), new THREE.MeshStandardMaterial({ color: 0x3a1c0c, roughness: .2 }));
  tea.rotation.x = -Math.PI / 2; tea.position.set(mx, DESK + .14, .55); scene.add(tea);
  for (let i = 0; i < 18; i++) {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: softDot, color: 0xffffff, transparent: true, depthWrite: false, opacity: 0 }));
    sp.userData = { x: mx, z: .55, o: rnd(), k: 1 + (i % 2), w: rnd() }; scene.add(sp); steam.push(sp);
  }
}
if (props.has('plant')) {
  const px = 1.15 + rnd() * .05;
  const pot = new THREE.Mesh(new THREE.CylinderGeometry(.09, .07, .16, 24), new THREE.MeshStandardMaterial({ color: 0x9a5a3a, roughness: .9 }));
  pot.position.set(px, DESK + .115, .35); pot.castShadow = true; scene.add(pot);
  const leafMat = new THREE.MeshStandardMaterial({ color: 0x2f5a32, roughness: .7, side: THREE.DoubleSide });
  for (let i = 0; i < 14; i++) {
    const leaf = new THREE.Mesh(new THREE.SphereGeometry(.07, 12, 8), leafMat); leaf.scale.set(.35, 1, .12);
    const a = rnd() * TAU, r = .02 + rnd() * .05; leaf.position.set(px + Math.cos(a) * r, DESK + .26 + rnd() * .12, .35 + Math.sin(a) * r);
    leaf.rotation.set((rnd() - .5) * 1.2, a, (rnd() - .5) * 1.2); leaf.castShadow = true; scene.add(leaf);
  }
}
// dust motes drifting in the warm light (periodic paths)
const motes = []; const moteMat = new THREE.SpriteMaterial({ map: softDot, color: 0xffd9a8, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
for (let i = 0; i < 40; i++) { const m = new THREE.Sprite(moteMat.clone()); m.scale.setScalar(.008 + rnd() * .01);
  m.userData = { c: new THREE.Vector3(FLAME.x + (rnd() - .5) * 1.2, DESK + .2 + rnd() * .9, .4 + rnd() * .9), r: .03 + rnd() * .06, o: rnd() }; scene.add(m); motes.push(m); }

// ---------- clutter (30 Days to Cozy): boxes, laundry, takeaway, paper; fewer of them as mess falls ----------
if (spec.mess > 0) {
  const n = Math.round(spec.mess * 14);
  const card = new THREE.MeshStandardMaterial({ color: 0x8a6a42, roughness: .95 });
  const cloth = [0x3d4a5a, 0x5a3a3a, 0x6a6a6a, 0x2e3a2e].map(c => new THREE.MeshStandardMaterial({ color: c, roughness: 1 }));
  const paper = new THREE.MeshStandardMaterial({ color: 0xd8d4c8, roughness: .9 });
  const can = new THREE.MeshStandardMaterial({ color: 0xb03030, metalness: .7, roughness: .3 });
  for (let i = 0; i < n; i++) {
    const k = i % 4, x = (rnd() - .5) * 2.6, z = .9 + rnd() * 1.1;
    if (k === 0) { const b = box(.3 + rnd() * .25, .2 + rnd() * .2, .3 + rnd() * .2, card, x, 0, z); b.position.y = b.geometry.parameters.height / 2; b.rotation.y = rnd() * 1.5; }
    else if (k === 1) { const m = new THREE.Mesh(new THREE.SphereGeometry(.22, 20, 12), cloth[i % 4]); m.scale.set(1.2, .32, .9); m.position.set(x, .06, z); m.rotation.y = rnd() * 3; m.castShadow = m.receiveShadow = true; scene.add(m); }
    else if (k === 2) { const m = new THREE.Mesh(new THREE.IcosahedronGeometry(.045, 0), paper); m.position.set((rnd() - .5) * 2.4, DESK + .075, .3 + rnd() * .35); m.castShadow = true; scene.add(m); }
    else { const m = new THREE.Mesh(new THREE.CylinderGeometry(.033, .033, .12, 16), can); m.position.set((rnd() - .5) * 2.2, DESK + .095, .3 + rnd() * .3); if (rnd() < .5) { m.rotation.z = Math.PI / 2; m.position.y = DESK + .07; } m.castShadow = true; scene.add(m); }
  }
  if (spec.mess > .5) { const pz = box(.42, .05, .42, card, -.45, DESK + .06, .45); pz.rotation.y = .3; }   // takeaway box
}

// ---------- lights ----------
scene.add(new THREE.AmbientLight(0x1a1a2a, .35 + .5 * spec.mess));
const bulb = new THREE.PointLight(0xc8d6ff, 9 * spec.mess, 9, 1.2); bulb.position.set(.3, 2.6, 2.1); bulb.castShadow = spec.mess > 0; scene.add(bulb);   // bare cold ceiling bulb
const moon = new THREE.DirectionalLight(spec.time === 'night' ? 0x6070a0 : 0xd09070, spec.time === 'night' ? .35 : .6);
moon.position.set(.5, 3, -4); moon.target.position.set(0, .8, .8); moon.castShadow = true; moon.shadow.mapSize.set(1024, 1024);
scene.add(moon, moon.target);
const fire = new THREE.PointLight(0xff7a30, 0, 9, 1.2); fire.position.set(-2.4, .5, 1.6); scene.add(fire);

// ---------- post ----------
const composer = new EffectComposer(renderer); composer.setPixelRatio(1); composer.setSize(W, H);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new BokehPass(scene, camera, { focus: 2.15, aperture: .0035, maxblur: .006 }));
composer.addPass(new UnrealBloomPass(new THREE.Vector2(W, H), .5, .7, .78));
composer.addPass(new OutputPass());
const grade = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, uF: { value: 0 }, uFire: { value: 0 }, uMess: { value: spec.mess } },
  vertexShader: `varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uF, uFire, uMess; varying vec2 vUv;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233))+uF*.618)*43758.5453); }
    void main(){ vec3 c=texture2D(tDiffuse,vUv).rgb; c=pow(c, vec3(.96,.98,1.04)); c+=vec3(.012,.006,0.);
      float lum=dot(c, vec3(.2126,.7152,.0722)); c=mix(vec3(lum), c, .82-.45*uMess);
      c+=vec3(-.012,.0,.022)*(1.-smoothstep(.0,.35,lum)) + vec3(.02,.008,-.01)*smoothstep(.45,1.,lum);
      c=(c-.5)*1.06+.5;
      float v=smoothstep(1.05,.35,length((vUv-.5)*vec2(1.1,1.))); c*=mix(.62,1.,v);
      // fireplace just out of frame on the left: a warm, breathing spill across the lower left of the room
      c+=vec3(.55,.2,.04)*uFire*smoothstep(.75,.0,length((vUv-vec2(-.08,.18))*vec2(1.,1.3)))*.42;
      c+=(h(vUv*1000.)-.5)*.018;
      gl_FragColor=vec4(c,1.); }`,
});
composer.addPass(grade);

// ---------- frame ----------
const camBase = PORTRAIT ? new THREE.Vector3(-.05, 1.7, 2.45) : new THREE.Vector3(-.05, 1.32, 2.55),
  look = PORTRAIT ? new THREE.Vector3(0, 1.0, .2) : new THREE.Vector3(0, 1.25, 0);
function render(t) {
  const ph = ((t % LOOP) + LOOP) % LOOP / LOOP;
  camera.position.set(camBase.x + .11 * Math.sin(TAU * ph), camBase.y + .025 * Math.sin(TAU * 2 * ph), camBase.z - .06 * Math.cos(TAU * ph));
  outsideMat.uniforms.uCam.value = camera.position.x;
  camera.lookAt(look);
  outsideMat.uniforms.uPh.value = ph; glassMat.uniforms.uPh.value = ph; flameMat.uniforms.uPh.value = ph;
  const fl = flick(ph, 1);
  warm.position.copy(FLAME).add(new THREE.Vector3(.01 * fl, .03, .02));
  warm.intensity = spec.light === 'none' ? 0 : spec.light === 'candle' ? 2.2 + .35 * fl : 3.2 + .05 * fl;
  fire.intensity = spec.fire ? 6.5 + 2.2 * flick(ph, 5) : 0;
  grade.uniforms.uFire.value = spec.fire ? .75 + .25 * flick(ph, 7) : 0;
  if (flame) { flame.position.copy(FLAME); flame.quaternion.copy(camera.quaternion); flame.scale.set(1, 1 + .06 * fl, 1); }
  for (const sp of steam) { const u = sp.userData, life = (u.o + ph * u.k) % 1;
    sp.position.set(u.x + .02 * Math.sin(TAU * (ph * u.k + u.w)) + life * .03, DESK + .16 + life * .32, u.z);
    sp.scale.setScalar(.03 + life * .09); sp.material.opacity = .16 * Math.sin(Math.PI * life); }
  for (const m of motes) { const u = m.userData, a = TAU * (ph + u.o);
    m.position.set(u.c.x + u.r * Math.cos(a), u.c.y + u.r * Math.sin(2 * a) * .5, u.c.z + u.r * Math.sin(a));
    m.material.opacity = .5 + .3 * Math.sin(a * 3); }
  grade.uniforms.uF.value = Math.round(t * spec.fps) % Math.round(LOOP * spec.fps);
  composer.render();
}
const out = document.createElement('canvas'); out.width = W; out.height = H; const octx = out.getContext('2d');
window.frame = (t, qual = .92) => { render(t); octx.drawImage(renderer.domElement, 0, 0); return out.toDataURL('image/jpeg', qual); };
render(0);
window.READY = true;
