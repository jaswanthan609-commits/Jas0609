// Render the cozy loop: node capture.js '<spec json>' out.mp4 [stills t1,t2]
// Serves this folder on a local port, loads cozy.html in headless Chromium (software WebGL),
// and pipes LOOP*FPS JPEG frames into ffmpeg. Frames 0..N-1 tile seamlessly.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http'), fs = require('fs'), path = require('path');
const [, , specJson, outp, stills] = process.argv;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const f = path.join(__dirname, decodeURIComponent(req.url.split('?')[0]));
  if (!f.startsWith(__dirname) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});
server.listen(0, '127.0.0.1', async () => {
  const port = server.address().port;
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto(`http://127.0.0.1:${port}/cozy.html?spec=${encodeURIComponent(specJson)}`);
  await p.waitForFunction('window.READY', null, { timeout: 180000 });
  const [loop, fps] = await p.evaluate('[window.LOOP, window.FPS]');
  if (outp === 'stills') {
    for (const t of stills.split(',')) { const d = await p.evaluate(`window.frame(${t})`); fs.writeFileSync(`still_${t}.jpg`, Buffer.from(d.split(',')[1], 'base64')); }
  } else {
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-r', String(fps), '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '23', '-pix_fmt', 'yuv420p', '-g', String(fps * 2), outp], { stdio: ['pipe', 'inherit', 'inherit'] });
    const N = Math.round(loop * fps), t0 = Date.now();
    for (let i = 0; i < N; i++) {
      const d = await p.evaluate(`window.frame(${i / fps})`);
      if (!ff.stdin.write(Buffer.from(d.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 48 === 0) console.log(`frame ${i}/${N} ${((Date.now() - t0) / 1000) | 0}s`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await b.close(); server.close();
});
