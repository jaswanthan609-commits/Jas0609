# Demo clips

- `engraving/`: Slow History plate film. Engine from lemo-opuscar (MIT, see LICENSE-lemo-opuscar), with a new
  subject `subjects/lamp.js` (Roman oil lamp), `content_lamp.json`, and a `?slow=2` option in `main.js` for sleep pacing.
  Render with lemo-opuscar's `core/render/video.mjs` (the page imports `/core/lib.js`, so serve it from the lemo-opuscar root).
- `nri-motion/`: NRI Money HyperFrames composition. `gen.py` writes `index.html` from `scenes.json`
  (voice timings); add `assets/vo.wav` and run `npx hyperframes@0.9.11 render . -o out.mp4`.
- `build.py`, `engrave.py`, `cards.py`: the first, static demo (superseded).
