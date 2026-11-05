// Render one glow-up episode: node capture.js <episode.json> <out.mp4> [stills t1,t2,...]
// Serves this folder, loads episode.html in headless Chromium and pipes 30 fps screenshots into ffmpeg.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http'), fs = require('fs'), path = require('path');
const [, , epFile, outp, stills] = process.argv;
const ep = fs.readFileSync(epFile, 'utf8');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.woff2': 'font/woff2', '.css': 'text/css' };
const server = http.createServer((req, res) => {
  const f = path.join(__dirname, decodeURIComponent(req.url.split('?')[0]));
  if (!f.startsWith(__dirname) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});
server.listen(0, '127.0.0.1', async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto(`http://127.0.0.1:${server.address().port}/episode.html?ep=${encodeURIComponent(ep)}`);
  await p.waitForFunction('window.READY', null, { timeout: 60000 });
  const dur = await p.evaluate('window.DURATION');
  const shot = async t => { await p.evaluate(`window.frame(${t})`); return p.screenshot({ type: 'jpeg', quality: 92 }); };
  if (outp === 'stills') {
    for (const t of stills.split(',')) fs.writeFileSync(`still_${t}.jpg`, await shot(+t));
  } else {
    const fps = 30, N = Math.round(dur * fps);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-r', String(fps), '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', outp], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let i = 0; i < N; i++) {
      if (!ff.stdin.write(await shot(i / fps))) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 150 === 0) console.log(`frame ${i}/${N}`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await b.close(); server.close();
});
