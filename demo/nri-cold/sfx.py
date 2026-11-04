import numpy as np, json, subprocess
sr=48000; W=json.load(open('words.json'))
def wt(w,n=0):
    k=0
    for x in W:
        if ''.join(c for c in x['w'].lower() if c.isalnum())==w:
            if k==n: return x['t']
            k+=1
END=W[-1]['t']+W[-1]['d']+0.9; N=int(END*sr)+sr
rng=np.random.default_rng(1)
mus=np.zeros(N); fx=np.zeros(N)
def add(buf,t,sig,g=1.0):
    i=int(t*sr); j=min(N,i+len(sig)); buf[i:j]+=sig[:j-i]*g
def env(n,a,d): t=np.arange(n)/sr; return np.minimum(1,t/a)*np.exp(-t/d)
def lp(x,k): # one-pole lowpass
    y=np.zeros_like(x); s=0
    for i in range(len(x)): s+=k*(x[i]-s); y[i]=s
    return y
# --- music: 96 bpm pulse in A minor
bpm=96; e8=60/bpm/2
roots=[55,55,43.65,49]  # A, A, F, G per bar
t=0.0; i=0
while t<END-0.6:
    bar=int(t/(e8*8)); f=roots[bar%4]
    n=int(e8*sr*0.95); tt=np.arange(n)/sr
    s=(np.sin(2*np.pi*f*tt)+0.35*np.sin(2*np.pi*2*f*tt))*env(n,.005,.12)
    gap = 6.86<=t<7.2   # drop before LEGAL
    if not gap: add(mus,t,s,0.5)
    if t>=2.37 and not gap:
        h=rng.standard_normal(int(.04*sr)); h=h-lp(h,.3); add(mus,t,h*env(len(h),.001,.012),0.18*(1 if i%2 else .6))
    if i%8==4 and t>=2.37 and not gap: # clap-ish snare on beat 3
        sn=rng.standard_normal(int(.15*sr)); add(mus,t,(sn-lp(sn,.15))*env(len(sn),.001,.05),0.25)
    t+=e8; i+=1
# pad
tt=np.arange(N)/sr
pad=sum(np.sin(2*np.pi*f*tt+ph) for f,ph in [(220,0),(220.9,1),(261.6,2),(329.6,3)])/4
pad*=0.06*np.clip((tt-0.2)/2,0,1)*np.clip((END-tt)/1.0,0,1)
mus+=pad
# --- sfx
def whoosh(dur=.35):
    n=int(dur*sr); x=rng.standard_normal(n); k=np.linspace(.02,.4,n)
    y=np.zeros(n); s=0
    for i in range(n): s+=k[i]*(x[i]-s); y[i]=s
    return y*np.sin(np.linspace(0,np.pi,n))**2
def thud(f0=90,dur=.5):
    n=int(dur*sr); tt=np.arange(n)/sr; f=f0*np.exp(-tt*6)+35
    return np.sin(2*np.pi*np.cumsum(f)/sr)*env(n,.002,.18)
def pop(f=900): n=int(.12*sr); tt=np.arange(n)/sr; return np.sin(2*np.pi*(f+2000*tt)*tt)*env(n,.001,.03)
def buzz(): n=int(.45*sr); tt=np.arange(n)/sr; return np.sign(np.sin(2*np.pi*150*tt))*0.3*(np.sin(2*np.pi*12*tt)>0)*env(n,.005,.4)
def click(): n=int(.03*sr); x=rng.standard_normal(n); return (x-lp(x,.2))*env(n,.0005,.006)
def riser(dur=1.2):
    n=int(dur*sr); tt=np.arange(n)/sr; x=rng.standard_normal(n); k=np.linspace(.01,.5,n); y=np.zeros(n); s=0
    for i in range(n): s+=k[i]*(x[i]-s); y[i]=s
    return (y*0.6+0.3*np.sin(2*np.pi*(200*tt+300*tt*tt/dur)))*(tt/dur)**2
cuts=[2.368,6.855,7.917,9.992,11.455,13.142,16.08,19.205,20.43]
for c in cuts: add(fx,c-.2,whoosh(),0.35)
add(fx,.4,buzz(),.35); add(fx,1.0,buzz()[:int(.2*sr)],.3)
add(fx,wt('thirtyone')+.03,thud(),0.9)
add(fx,wt('legal')-.02,thud(70,.7),1.0)
for k in range(14): add(fx,wt('happens')+k*.045,pop(700+k*40),0.12)
add(fx,wt('avoidable'),pop(1200),.35)
add(fx,wt('home')-.05,pop(900),.3)
add(fx,wt('put')-.15,pop(1500),.25)
add(fx,wt('did')-.05,click(),.8)
add(fx,wt('n')-1.25,riser(),.35); add(fx,wt('n')-.03,thud(60,.8),.9)
mus/=np.max(np.abs(mus))+1e-9; fx/=np.max(np.abs(fx))+1e-9
# load voice, duck music
vo=np.frombuffer(subprocess.run(['ffmpeg','-loglevel','error','-i','vo.wav','-f','f64le','-ac','1','-ar',str(sr),'-'],capture_output=True).stdout,np.float64).copy()
v=np.zeros(N); v[:min(N,len(vo))]=vo[:N]
envv=np.convolve(np.abs(v),np.ones(int(.15*sr))/int(.15*sr),'same'); m=np.clip(envv/ (np.max(envv)*.25),0,1)
mix=v*1.0 + mus*0.16*(1-0.45*m) + fx*0.32
mix=mix[:int(END*sr)]
mix/=np.max(np.abs(mix))*1.05
mix.astype(np.float32).tofile('mix.f32')
subprocess.run(['ffmpeg','-y','-loglevel','error','-f','f32le','-ar',str(sr),'-ac','1','-i','mix.f32','-af','loudnorm=I=-15:TP=-1.5','-ar','48000','mix.wav'])
print('ok',END)
