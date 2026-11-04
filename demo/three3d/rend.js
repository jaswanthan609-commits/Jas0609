// usage: node rend.js page.html out.mp4|stills fps [t1,t2..]
const {chromium}=require('playwright');const {spawn}=require('child_process');const fs=require('fs');
const [,,page,outp,fps='24',times]=process.argv;
(async()=>{
 const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
 const p=await b.newPage({viewport:{width:1920,height:1080}});
 p.on('console',m=>console.log('PAGE',m.text()));p.on('pageerror',e=>console.log('ERR',e.message));
 await p.goto('http://127.0.0.1:8765/'+page);await p.waitForFunction('window.READY',null,{timeout:120000});
 const dur=await p.evaluate('window.DUR');
 if(outp==='stills'){for(const t of times.split(',')){const t0=Date.now();const d=await p.evaluate(`window.frame(${t})`);fs.writeFileSync(`s_${t}.jpg`,Buffer.from(d.split(',')[1],'base64'));console.log(t,Date.now()-t0,'ms')}await b.close();return}
 const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-c:v','mjpeg','-r',fps,'-i','-','-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p',outp],{stdio:['pipe','inherit','inherit']});
 const N=Math.round(dur*fps);const [A,B]=(process.env.RANGE||`0,${N}`).split(',').map(Number);const t0=Date.now();
 for(let i=A;i<Math.min(B,N);i++){const d=await p.evaluate(`window.frame(${i/fps})`);const buf=Buffer.from(d.split(',')[1],'base64');if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));if(i%120==0)console.log(i,'/',N,((Date.now()-t0)/1000|0)+'s')}
 ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();
})();
