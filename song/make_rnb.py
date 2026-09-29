import numpy as np, wave, json
from scipy.signal import lfilter
SR=44100; BPM=72; BEAT=60/BPM; BAR=4*BEAT; S16=BEAT/4; SWING=.14
rng=np.random.default_rng(11)
def hz(m): return 440*2**((m-69)/12)
def tt(d): return np.arange(int(d*SR))/SR
def at(bar,pos): return bar*BAR+(pos+(SWING if int(pos)%2 else 0))*S16   # pos in 16ths, swung
# ---------- lyrics: syllables separated by '|' , one line = one bar ----------
SECS=[("Intro",2,None),
("Verse 1",8,["ฉัน|เจอ|เธอ|วัน|ที่|มา|ทำ|งาน","เธอ|คือ|คน|ที่|ใจ|ดี|กว่า|ใคร","ตั้ง|มั่น|สัด|จะ|ไว้|ใน|ใจ|ฉัน","จะ|ดู|แล|เธอ|ไป|ตะ|หลอด|ไป",
 "แอบ|มอง|รูป|เธอ|ใน|ห้อง|นั้น","ยิ้ม|ที่|ปน|ทุกข์|ช่าง|น่า|รัก|จัง","ไม่|ได้|สวย|เลิศ|เหมือน|ใคร|ใคร","แต่|ใจ|เธอ|มั่น|รัก|นิ|รัน"]),
("Chorus",8,["จำ|ไว้|นะ|ต่อ|ให้|มี|อะ|ไร|มา|กั้น","ภู|เขา|ทะ|เล|ดวง|ดาว|จัก|กะ|วาน","ฉัน|ไม่|ไป|ไหน|ไม่|มี|วัน|จาก|ไกล","รัก|เธอ|และ|ลูก|ตะ|หลอด|ไป|ตะ|หลอด|กาน",
 "ไม่|เคย|คิด|ไป|หา|ใคร|ที่|ไหน","ถึง|ฉัน|จะ|เฉย|ไป|บ้าง|บาง|ที","แต่|ใน|ใจ|ใน|สะ|หมอง|คิด|ถึง|สะ|เหมอ","ว่า|เรา|ต้อง|สะ|บาย|มี|สุข|ตะ|หลอด|ไป"]),
("Verse 2",8,["อีก|ใจ|ฉัน|วิ่ง|ขะ|หนาน|ทุก|วัน","นอน|ดึก|บ่อย|เพราะ|หัว|ไม่|หยุด|คิด","คิด|สร้าง|ฐา|นะ|ให้|ครอบ|ครัว|เรา","ให้|มี|อยู่|มี|กิน|สะ|บาย|ทุก|วัน",
 "ยัง|ไม่|ถึง|ฝั่ง|ฝัน|แต่|ฉัน|มั่น|ใจ","วัน|ที่|มี|บ้าน|เป็น|ของ|เรา|เอง","วัน|ที่|ลูก|อยาก|เรียน|อะ|ไร|ก็|ได้|เรียน","เรา|จะ|ไป|ถึง|ไม่|ช้า|ก็|เร็ว"]),
("Bridge",4,["ติด|อยู่|ใน|กรอบ|เม|ทริกซ์|ที่|ไม่|ได้|สร้าง","คน|ส่วน|ใหญ่|วน|อยู่|ใน|ลูป|เดิม","ฉัน|จะ|ดึง|เธอ|ดึง|ลูก|ออก|มา","ไม่|ปล่อย|มือ|ไม่|ปล่อย|ใคร|ไม่|ปล่อย|เธอ"]),
("Chorus",8,None),  # repeat
("Outro",2,["ตอน|จบ|เรา|จะ|ได้|สัม|ผัส|สุข|แท้","รัก|ที่|มี|ให้|เธอ|และ|ลูก|ตะ|หลอด|กาน"])]
SECS[5]=("Chorus",8,SECS[2][2])
TPL={6:[1,3,5,8,10,12],7:[0,2,4,6,8,10,12],8:[0,2,4,6,8,10,12,14],9:[0,2,3,4,6,8,10,12,14],10:[0,2,3,4,6,8,10,11,12,14]}
# ---------- harmony: Am9 Fmaj7 Dm9 E7 ----------
CH=[([57,60,64,67,71],33,[69,72,76]),([53,57,60,64,67],29,[69,72,77]),([50,57,60,65,69],26,[69,74,77]),([52,56,59,62,66],28,[71,68,76])]
CONT=[[76,74,72,74,76,77,76,74,72,71],[77,76,74,72,74,76,74,72,71,69],[74,76,77,76,74,72,74,72,70,69],[76,74,71,72,74,76,74,71,72,71]]
total_bars=sum(s[1] for s in SECS); total=total_bars*BAR
N=int(total*SR)+SR*3
def mixer():
    return np.zeros(N),np.zeros(N)
def put(buf,sig,t):
    i=int(t*SR); e=min(N,i+len(sig)); buf[i:e]+=sig[:e-i]
def kick(v):
    t=tt(.4); ph=2*np.pi*np.cumsum(42+100*np.exp(-t*35))/SR; return v*np.sin(ph)*np.exp(-t*7)
def clap(v):
    t=tt(.3); n=rng.standard_normal(len(t)); env=np.exp(-t*20)+.6*np.exp(-((t-.012)*300)**2)+.5*np.exp(-((t-.024)*300)**2)
    return v*np.diff(n,prepend=0)*.35*env
def snap(v):
    t=tt(.09); return v*np.diff(rng.standard_normal(len(t)),prepend=0)*.3*np.exp(-t*60)+v*.3*np.sin(2*np.pi*1900*t)*np.exp(-t*90)
def hat(v,o=False):
    t=tt(.22 if o else .04); n=np.diff(rng.standard_normal(len(t)),prepend=0); return v*.3*n*np.exp(-t*(16 if o else 90))
def rhodes(m,d,v):
    t=tt(d); f=hz(m); s=np.sin(2*np.pi*f*t)+.4*np.sin(2*np.pi*2*f*t)*np.exp(-t*4)+.12*np.sin(2*np.pi*4*f*t)*np.exp(-t*12)
    return v*s*np.minimum(t/.012,1)*np.exp(-t*1.4)*(1+.12*np.sin(2*np.pi*5*t))
def pad(m,d,v):
    t=tt(d); f=hz(m); s=sum(np.sin(2*np.pi*f*(1+dt)*t) for dt in(-.004,0,.004))
    return v*s*np.minimum(t/.6,1)*np.minimum((d-t)/.6,1)
def s808(m,d):
    t=tt(d); f=hz(m)*(1+.5*np.exp(-t*40)); ph=2*np.pi*np.cumsum(f)/SR
    return np.tanh(1.8*np.sin(ph))*np.minimum(t/.005,1)*np.exp(-t*1.6)*.9
def voice(m,d,v=1.):
    t=tt(d); f=hz(m)*(1+.006*np.sin(2*np.pi*5.5*t)*np.minimum(t/.25,1)); ph=2*np.pi*np.cumsum(f)/SR
    s=sum(np.sin(k*ph)/k**1.3*(1.5 if k in(3,4,6) else 1) for k in range(1,14))
    return v*s*np.minimum(t/.015,1)*np.minimum(np.maximum(d-t,0)/.05,1)
inst=mixer(); vox=mixer()
def add(m,sig,t,pan=0.): put(m[0],sig*(1-pan),t); put(m[1],sig*(1+pan),t)
lrc=[]; timing=[]
bar=0
for name,nb,lines in SECS:
    lrc.append(f"[{int(bar*BAR//60):02d}:{bar*BAR%60:05.2f}]— {name} —")
    for b in range(nb):
        B=bar+b; T0=B*BAR; c=CH[B%4]; sec_hasdrums = name not in("Intro","Bridge") or b>=2 and name=="Bridge" and False
        # harmony
        for k,m in enumerate(c[0]): add(inst,pad(m-12 if k else m,BAR*1.02,.05),T0,(k-2)*.2)
        for i,pos in enumerate([0,3,6,8,11,14]):        # rhodes comp
            for k,m in enumerate(c[0][1:] if i%2 else c[0][:4]): add(inst,rhodes(m,BEAT*1.2,.11),at(B,pos)+k*.008,(k-2)*.12)
        drums = name not in("Intro","Bridge") and not (name=="Outro" and b==1)
        if name!="Intro":
            add(inst,s808(c[1],BEAT*2.6),T0); add(inst,s808(c[1],BEAT*.9),at(B,10)); 
            if b%2: add(inst,s808(c[1]+7,BEAT*.7),at(B,14))
        if drums:
            for pos,v in [(0,1),(7,.6),(10,.8)]: add(inst,kick(v*.9),at(B,pos))
            for pos in (4,12): add(inst,clap(.75),at(B,pos)); add(inst,snap(.5),at(B,pos)+.02,.3)
            for i in range(16):
                if i%2==0 or rng.random()<.35: add(inst,hat(1 if i%4==2 else .5 if i%2==0 else .25,o=(i==14)),at(B,i),.3*(-1)**(i//2))
        # vocal guide
        if lines and b<len(lines):
            syl=lines[b].split("|"); n=len(syl); on=TPL[n]; cont=CONT[B%4][:n]; cont[-1]=c[2][0]
            ts=[]
            for i,(s,p) in enumerate(zip(syl,on)):
                t0=at(B,p); nxt=at(B,on[i+1]) if i+1<n else at(B,15)+S16*1.2
                d=max(.09,nxt-t0-.02)
                if i==n-1: d=min(d+BEAT*.5,BEAT*2)
                add(vox,voice(cont[i],d,.13),t0)
                ts.append((s,round(t0,2)))
            lrc.append(f"[{int(T0//60):02d}:{T0%60:05.2f}]"+"".join(f"<{int(t//60):02d}:{t%60:05.2f}>{s}" for s,t in ts))
            timing.append({"section":name,"bar":B+1,"start":round(T0,2),"beats16":on,"syllables":syl,"notes":cont})
    bar+=nb
cr=(rng.random(N)<.0004)*rng.standard_normal(N)*.15
def fin(m,cr,sh):
    L,R=m; out=[]
    for x,c in ((L,cr),(R,np.roll(cr,sh))):
        x=x+c; x=lfilter([.5],[1,-.5],x) if False else x; out.append(np.tanh(x*1.2))
    return out
def echo(x,dly,fb,g):
    y=x.copy(); k=int(dly*SR)
    for i in range(1,4): y[i*k:]+=x[:len(x)-i*k]*g*fb**(i-1)
    return y
e=int(total*SR); fade=np.ones(N); fade[e-SR*2:e]=np.linspace(1,0,SR*2); fade[e:]=0
def save(fn,chs):
    st=np.stack([c*fade for c in chs],1)[:e]; st/=np.abs(st).max()*1.05
    with wave.open(fn,"wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st*32767).astype('<i2').tobytes())
iL,iR=fin(inst,cr,23)
vL=echo(vox[0],BEAT*.75,.5,.3); vR=echo(vox[1],BEAT*.75,.5,.3)
save("rnb_instrumental.wav",[iL,iR]); save("rnb_guide_melody_mix.wav",[iL+vL,iR+vR])
open("rnb_lyrics_timing.lrc","w",encoding="utf-8").write("\n".join(lrc))
json.dump(timing,open("rnb_timing.json","w"),ensure_ascii=False,indent=1)
print("ok",round(total,1),"s bars",total_bars)
