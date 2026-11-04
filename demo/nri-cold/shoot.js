// node shoot.js stills t1,t2 | node shoot.js video out.mp4
const {chromium}=require('playwright');const {spawn}=require('child_process');const fs=require('fs');
const [,,mode,arg]=process.argv;
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1920,height:1080}});
p.on('pageerror',e=>console.log('ERR',e.message));p.on('console',m=>console.log('PAGE',m.text()));
await p.goto('http://127.0.0.1:8766/cold.html');await p.waitForFunction('window.READY',null,{timeout:60000});
console.log('cuts',await p.evaluate('JSON.stringify(window.CUTS)'),'dur',await p.evaluate('window.DUR'));
if(mode==='stills'){for(const t of arg.split(',')){await p.evaluate(`window.renderAt(${t})`);await p.screenshot({path:`c_${t}.jpg`,type:'jpeg',quality:80});}await b.close();return}
const dur=await p.evaluate('window.DUR');const N=Math.ceil(dur*30);
const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-c:v','mjpeg','-r','30','-i','-','-c:v','libx264','-crf','19','-preset','medium','-pix_fmt','yuv420p',arg],{stdio:['pipe','inherit','inherit']});
for(let i=0;i<N;i++){await p.evaluate(`window.renderAt(${i/30})`);const buf=await p.screenshot({type:'jpeg',quality:92});if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));}
ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();console.log('frames',N)})();
