// node frames.js page outdir offset t0 t1 fps   -> writes outdir/%05d.jpg for cold times t0..t1 (page time = t + offset)
const {chromium}=require('playwright');const fs=require('fs');
const [,,page,outdir,off,t0,t1,fps]=process.argv;
(async()=>{const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const p=await b.newPage({viewport:{width:1920,height:1080}});p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('http://127.0.0.1:8765/'+page);await p.waitForFunction('window.READY',null,{timeout:120000});
fs.mkdirSync(outdir,{recursive:true});
const a=Math.round(+t0*fps),z=Math.round(+t1*fps);
for(let i=a;i<z;i++){const d=await p.evaluate(`window.frame(${i/fps + +off})`);fs.writeFileSync(`${outdir}/${String(i).padStart(5,'0')}.jpg`,Buffer.from(d.split(',')[1],'base64'))}
await b.close();console.log('done',outdir)})();
