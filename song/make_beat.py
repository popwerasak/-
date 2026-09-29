import numpy as np, wave
SR=44100; BPM=88; BEAT=60/BPM; BAR=4*BEAT
rng=np.random.default_rng(7)
# sections: (name, bars, drums, chords, melody, bass)
SECS=[("intro",4,0,1,0,0),("verse1",16,1,1,0,1),("chorus",8,1,1,1,1),
      ("verse2",16,1,1,0,1),("bridge",8,0,1,1,0),("chorus2",8,1,1,1,1),("outro",4,0,1,0,0)]
total=sum(s[1] for s in SECS)*BAR
N=int(total*SR)+SR*2
def mix(buf,sig,t):
    i=int(t*SR); e=min(len(buf),i+len(sig))
    if i<len(buf): buf[i:e]+=sig[:e-i]
def hz(m): return 440*2**((m-69)/12)
def tt(d): return np.arange(int(d*SR))/SR
def kick(v=1):
    t=tt(.35); f=45+90*np.exp(-t*30); ph=2*np.pi*np.cumsum(f)/SR
    return v*np.sin(ph)*np.exp(-t*9)
def snare(v=1):
    t=tt(.25); n=rng.standard_normal(len(t))*np.exp(-t*22)
    return v*(0.6*n+0.5*np.sin(2*np.pi*190*t)*np.exp(-t*30))
def hat(v=1,o=False):
    d=.25 if o else .05; t=tt(d); n=rng.standard_normal(len(t)); n=np.diff(n,prepend=0)
    return v*.35*n*np.exp(-t*(14 if o else 70))
def rhodes(m,d,v=1):
    t=tt(d); f=hz(m)
    s=np.sin(2*np.pi*f*t)+.4*np.sin(2*np.pi*2*f*t)*np.exp(-t*4)+.15*np.sin(2*np.pi*4*f*t)*np.exp(-t*10)
    a=np.minimum(t/.01,1)*np.exp(-t*1.6)*(1+.15*np.sin(2*np.pi*4.5*t))
    return v*s*a
def bass(m,d):
    t=tt(d); f=hz(m); return np.sin(2*np.pi*f*t)*np.minimum(t/.01,1)*np.exp(-t*2.2)*1.1
def pluck(m,d):
    t=tt(d); f=hz(m)
    s=np.sin(2*np.pi*f*t)+.3*np.sin(2*np.pi*2*f*t)+.1*np.sin(2*np.pi*3*f*t)
    return s*np.minimum(t/.005,1)*np.exp(-t*5)
# Am9 Fmaj7 Dm9 E7 (MIDI)
CH=[([57,60,64,67,71],33),([53,57,60,64,67],29),([50,57,60,65,69],26),([52,56,59,62,66],28)]
# hook melody per bar (beat offset, midi, len in beats) A minor pentatonic
HOOK=[[(0,76,1),(1.5,74,.5),(2,72,1),(3.5,69,.5)],
      [(0,72,1),(1,74,1),(2,72,1.5)],
      [(0,74,1),(1.5,72,.5),(2,69,1),(3,72,1)],
      [(0,71,1.5),(2,69,.5),(2.5,71,.5),(3,74,1)]]
L=np.zeros(N); R=np.zeros(N)
def add(sig,t,pan=0.):
    mix(L,sig*(1-pan),t); mix(R,sig*(1+pan),t)
bar=0
for name,nb,dr,ch,me,ba in SECS:
    for b in range(nb):
        T0=(bar+b)*BAR; c=CH[b%4]
        if ch:
            for k,m in enumerate(c[0]):
                add(rhodes(m,BAR*1.05,.16),T0+k*.012,(k-2)*.15)
        if ba:
            r=c[1]
            add(bass(r,BEAT*1.4),T0); add(bass(r,BEAT*.9),T0+2.5*BEAT)
            add(bass(r+12 if b%2 else r,BEAT*.5),T0+3.5*BEAT)
        if dr:
            for bt,v in [(0,1),(1.75,.7),(2.5,.9),(3.75,.5) if b%2 else (3.25,.5)]:
                add(kick(v*.9),T0+bt*BEAT)
            for bt in (1,3): add(snare(.7),T0+bt*BEAT)
            for i in range(8):
                sw=BEAT*.5*.12 if i%2 else 0
                add(hat((.9 if i%2==0 else .5)*(1 if i%4 else 1.1),o=(i==7)),T0+i*.5*BEAT+sw,.3*(-1)**i)
        if me:
            for bt,m,ln in HOOK[b%4]:
                add(pluck(m,ln*BEAT+.2)*.22,T0+bt*BEAT,.25)
                add(pluck(m,ln*BEAT+.2)*.10,T0+bt*BEAT+.19,-.25)
    bar+=nb
# vinyl crackle
cr=(rng.random(N)<.0008)*rng.standard_normal(N)*.25
L+=cr; R+=np.roll(cr,17)
# lo-fi lowpass (one-pole) + tape saturation
def lp(x,a): 
    y=np.empty_like(x); s=0.
    for i in range(len(x)): s+=a*(x[i]-s); y[i]=s
    return y
try:
    from scipy.signal import lfilter
    lp=lambda x,a: lfilter([a],[1,a-1],x)
except Exception: pass
L=np.tanh(lp(L,.35)*1.3); R=np.tanh(lp(R,.35)*1.3)
# fade out
f=np.ones(N); e=int(total*SR); f[e-SR*2:e]=np.linspace(1,0,SR*2); f[e:]=0
L*=f; R*=f
st=np.stack([L,R],1)[:e]; st/=np.abs(st).max()*1.05
pcm=(st*32767).astype('<i2')
with wave.open("illslick_beat.wav","wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("done",round(total,1),"sec")
