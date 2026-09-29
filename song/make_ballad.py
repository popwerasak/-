import numpy as np, wave, json
from scipy.signal import lfilter
SR=44100; BPM=68; BEAT=60/BPM; BAR=4*BEAT; S16=BEAT/4; SWING=.08
rng=np.random.default_rng(5)
def hz(m): return 440*2**((m-69)/12)
def tt(d): return np.arange(int(d*SR))/SR
def at(bar,pos): return bar*BAR+(pos+(SWING if int(pos)%2 else 0))*S16
# (name, family, bars, lines[2 bars each], drums level 0-2)
V1=["เจอ|เธอ|วัน|ที่|ฉัน|เดิน|มา|ทำ|งาน","เห็น|ยิ้ม|ที่|ปน|ทุกข์|ช่าง|อ่อน|หวาน","ไม่|สวย|เลิศ|เหมือน|ใคร|แต่|ใจ|งด|งาม","ฉัน|ตั้ง|ใจ|ไว้|จะ|รัก|เธอ|ตะ|หลอด|ไป"]
P1=["ตอน|นั้น|เรา|ต่าง|มี|ใคร|อยู่|แล้ว","แต่|ใจ|เรา|ตรง|กัน|จน|ได้|แต่ง|งาน"]
CH=["ต่อ|ให้|มี|ภู|เขา|ทะ|เล|มา|กั้น","ต่อ|ให้|มี|ดวง|ดาว|จัก|กะ|วาน|ไกล","ฉัน|จะ|ไม่|จาก|เธอ|ไป|ไหน|เลย","รัก|เธอ|และ|ลูก|ตะ|หลอด|ไป|ตะ|หลอด|กาน"]
V2=["แม้|บาง|ที|ฉัน|เฉย|ชา|ไป|บ้าง","ใน|ใจ|ห่วง|เธอ|ทุก|ครั้ง|ไม่|ห่าง","คืน|ที่|ฉัน|นอน|ดึก|คิด|ไกล","เพื่อ|สร้าง|ฐา|นะ|ให้|เรา|สอง|คน|กับ|ลูก"]
P2=["วัน|นี้|เรา|มี|ลูก|น้อย|น่า|รัก","เป็น|ของ|ขวัญ|ที่|ดี|ที่|สุด|ใน|ชี|วิต"]
BR=["วัน|ที่|เรา|มี|บ้าน|ของ|เรา|เอง","ลูก|อยาก|เรียน|อะ|ไร|ก็|ได้|เรียน","ไม่|ต้อง|ติด|อยู่|ใน|วง|จอน|เดิม","ฉัน|จะ|พา|เรา|ออก|ไป|ด้วย|กัน"]
OU=["ให้|เธอ|และ|ลูก|ไป|ตะ|หลอด|กาน"]
SECS=[("Intro","I",2,None,0),("Verse 1","V",8,V1,1),("Pre-Chorus","P",4,P1,1),("Chorus","C",8,CH,2),("Verse 2","V",8,V2,1),
("Pre-Chorus 2","P2",4,P2,1),("Chorus","C",8,CH,2),("Bridge","B",8,BR,0),("Final Chorus","C",8,CH,2),("Outro","O",2,OU,0)]
CHD=[([57,60,64,67,71],33,[69,72,76]),([53,57,60,64,67],29,[69,72,77]),([50,57,60,65,69],26,[69,74,77]),([52,56,59,62,66],28,[71,68,76])]
SC=[64,65,67,69,71,72,74,76,77,79,81]   # A minor
RANGE={"V":(2,7),"P":(3,8),"P2":(3,8),"C":(5,10),"B":(3,8),"O":(4,8)}
def durations(n):
    base=[4,2,2,4,2,2,4,2,2,3]; d=[base[i%10] for i in range(n-1)]; s=sum(d)
    if s<22: d=[max(2,round(x*22/s)) for x in d]
    return d
melcache={}
def melody(fam,li,n,chord_tone_pool):
    key=(fam if fam not in("V",) else "V",li)
    if key in melcache and len(melcache[key])==n: return melcache[key]
    r=np.random.default_rng(sum(map(ord,key[0]))*31+key[1]+3); lo,hi=RANGE[fam]; idx=(lo+hi)//2; out=[]
    for i in range(n):
        prog=i/max(n-1,1); tgt=hi-1 if prog<.5 else lo+1   # arch
        step=int(r.choice([-1,0,1,1,-1,2,-2]))
        if (tgt-idx)*step<0 and r.random()<.6: step=-step
        idx=int(np.clip(idx+step,lo,hi)); out.append(idx)
    ct=[i for i,m in enumerate(SC) if m%12 in {p%12 for p in chord_tone_pool} and lo<=i<=hi]
    out[-1]=min(ct,key=lambda i:abs(i-out[-2])) if ct else out[-1]
    melcache[key]=[SC[i] for i in out]; return melcache[key]
total_bars=sum(s[2] for s in SECS); total=total_bars*BAR; N=int(total*SR)+SR*3
def put(buf,sig,t):
    i=int(t*SR); e=min(N,i+len(sig)); buf[i:e]+=sig[:e-i]
def kick(v):
    t=tt(.4); ph=2*np.pi*np.cumsum(42+90*np.exp(-t*35))/SR; return v*np.sin(ph)*np.exp(-t*8)
def clap(v):
    t=tt(.3); n=np.diff(rng.standard_normal(len(t)),prepend=0); env=np.exp(-t*18)+.5*np.exp(-((t-.014)*280)**2); return v*.3*n*env
def snap(v):
    t=tt(.09); return v*np.diff(rng.standard_normal(len(t)),prepend=0)*.25*np.exp(-t*60)+v*.25*np.sin(2*np.pi*1900*t)*np.exp(-t*90)
def hat(v,o=False):
    t=tt(.2 if o else .04); return v*.25*np.diff(rng.standard_normal(len(t)),prepend=0)*np.exp(-t*(16 if o else 90))
def rhodes(m,d,v):
    t=tt(d); f=hz(m); s=np.sin(2*np.pi*f*t)+.35*np.sin(2*np.pi*2*f*t)*np.exp(-t*4)+.1*np.sin(2*np.pi*4*f*t)*np.exp(-t*12)
    return v*s*np.minimum(t/.012,1)*np.exp(-t*1.5)*(1+.1*np.sin(2*np.pi*5*t))
def pad(m,d,v):
    t=tt(d); f=hz(m); s=sum(np.sin(2*np.pi*f*(1+x)*t) for x in(-.004,0,.004)); return v*s*np.minimum(t/.7,1)*np.minimum((d-t)/.7,1)
def s808(m,d):
    t=tt(d); ph=2*np.pi*np.cumsum(hz(m)*(1+.4*np.exp(-t*40)))/SR; return np.tanh(1.5*np.sin(ph))*np.minimum(t/.006,1)*np.exp(-t*1.4)*.8
def voice(m,d,v):
    t=tt(d); f=hz(m)*(1+.007*np.sin(2*np.pi*5.2*t)*np.minimum(t/.3,1)); ph=2*np.pi*np.cumsum(f)/SR
    s=sum(np.sin(k*ph)/k**1.4*(1.5 if k in(3,4,6) else 1) for k in range(1,13))
    return v*s*np.minimum(t/.03,1)*np.minimum(np.maximum(d-t,0)/.08,1)
def mixer(): return np.zeros(N),np.zeros(N)
def add(m,sig,t,pan=0.): put(m[0],sig*(1-pan),t); put(m[1],sig*(1+pan),t)
inst=mixer(); vox=mixer(); lrc=[]; timing=[]; bar=0
for name,fam,nb,lines,dl in SECS:
    lrc.append(f"[{int(bar*BAR//60):02d}:{bar*BAR%60:05.2f}]— {name} —")
    for b in range(nb):
        B=bar+b; T0=B*BAR; c=CHD[B%4]
        for k,m in enumerate(c[0]): add(inst,pad(m-12 if k else m,BAR*1.03,.045),T0,(k-2)*.2)
        if fam in("C",):   # chorus: fuller comping
            for i,pos in enumerate([0,3,6,8,11,14]):
                for k,m in enumerate(c[0][1:] if i%2 else c[0][:4]): add(inst,rhodes(m,BEAT*1.2,.1),at(B,pos)+k*.01,(k-2)*.12)
        else:              # soft arpeggio
            for i in range(8):
                m=c[0][[0,2,3,4,3,2,1,2][i]]; add(inst,rhodes(m,BEAT*1.1,.12),at(B,i*2),(i%4-1.5)*.15)
        if fam!="I":
            add(inst,s808(c[1],BEAT*3),T0)
            if dl>=1 and b%2: add(inst,s808(c[1],BEAT*.9),at(B,10))
        if dl>=1:
            add(inst,kick(.7),at(B,0))
            if dl==2: add(inst,kick(.6),at(B,10))
            for pos in (4,12):
                add(inst,snap(.5),at(B,pos),.3)
                if dl==2: add(inst,clap(.6),at(B,pos))
            for i in range(0,16,2 if dl==1 else 1):
                add(inst,hat(.6 if i%4==0 else .3,o=(i==14 and dl==2)),at(B,i),.3*(-1)**(i//2))
        # vocal: line spans two bars
        if lines and b%2==0 and b//2<len(lines):
            li=b//2; syl=lines[li].split("|"); n=len(syl)
            ct=CHD[(B+1)%4][2]; notes=melody(fam,li,n,ct)
            dur=durations(n); pos=0 if fam!="O" else 0; ts=[]; p=0
            for i,s in enumerate(syl):
                t0=at(B,p)
                if i<n-1: d=dur[i]*S16
                else: d=min(BEAT*3.5,T0+2*BAR-t0-.05)
                add(vox,voice(notes[i],max(d*.97,.1),.15),t0); ts.append((s,round(t0,2)))
                if i<n-1: p+=dur[i]
            lrc.append(f"[{int(T0//60):02d}:{T0%60:05.2f}]"+"".join(f"<{int(t//60):02d}:{t%60:05.2f}>{s}" for s,t in ts))
            timing.append({"section":name,"bar":B+1,"start":round(T0,2),"syllables":syl,"notes_midi":notes})
    bar+=nb
cr=(rng.random(N)<.0003)*rng.standard_normal(N)*.12
def echo(x,dly,fb,g):
    y=x.copy(); k=int(dly*SR)
    for i in range(1,4): y[i*k:]+=x[:len(x)-i*k]*g*fb**(i-1)
    return y
e=int(total*SR); fade=np.ones(N); fade[e-SR*3:e]=np.linspace(1,0,SR*3); fade[e:]=0
def save(fn,chs):
    st=np.stack([c*fade for c in chs],1)[:e]; st/=np.abs(st).max()*1.05
    with wave.open(fn,"wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st*32767).astype('<i2').tobytes())
iL=np.tanh((inst[0]+cr)*1.2); iR=np.tanh((inst[1]+np.roll(cr,23))*1.2)
vL=echo(vox[0],BEAT*.75,.5,.3); vR=echo(vox[1],BEAT*1.0,.5,.3)
save("ballad_instrumental.wav",[iL,iR]); save("ballad_guide_melody_mix.wav",[iL+vL,iR+vR])
open("ballad_lyrics_timing.lrc","w",encoding="utf-8").write("\n".join(lrc))
json.dump(timing,open("ballad_timing.json","w"),ensure_ascii=False,indent=1)
# lyrics sheet
NAMES=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
o=["# ให้เธอไปตลอดกาล — R&B Ballad (68 BPM, Am9–Fmaj7–Dm9–E7)\n","เพลงร้องหวานๆ 1 บรรทัด = 2 บาร์ พยางค์คั่นด้วย · และมีโน้ตทำนองกำกับ\n"]
cur=None
for x in timing:
    if x["section"]!=cur: cur=x["section"]; o.append(f"\n## {cur}\n")
    nn=[NAMES[m%12]+str(m//12-1) for m in x["notes_midi"]]
    o.append(f"{' '.join(x['syllables']).replace(' ','')}  \n`{' · '.join(x['syllables'])}`  \n`{' '.join(nn)}` (เริ่ม {x['start']}s)\n")
open("lyrics_ballad.md","w",encoding="utf-8").write("\n".join(o))
print("ok",round(total,1),"s")
