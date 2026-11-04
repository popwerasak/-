/* ส่วนกลางที่ใช้ร่วมกันระหว่างหน้าครู (host.html) และหน้านักเรียน (index.html)
 * - การรับส่งข้อมูลแบบเรียลไทม์ผ่าน MQTT (WebSocket) บน public broker
 *   เชื่อมต่อหลาย broker พร้อมกัน เพื่อให้ยังเล่นได้ถ้าเครือข่ายโรงเรียนบล็อกบางตัว
 * - ข้อความทุกชิ้นเข้ารหัส AES-GCM ด้วยกุญแจที่สร้างจาก PIN ของห้อง
 * - ดนตรีประกอบและเสียงเอฟเฟกต์สังเคราะห์ด้วย Web Audio (ไม่ใช้ไฟล์เพลง)
 */
(function () {
  const QZ = (window.QZ = {});
  const params = new URLSearchParams(location.search);

  QZ.PREFIX = "bcquiz-th-v1";
  // ใส่ ?broker=wss://your-broker/mqtt เพื่อใช้ broker ของตัวเอง (คั่นหลายตัวด้วย ,)
  QZ.BROKERS = params.get("broker")
    ? params.get("broker").split(",")
    : [
        "wss://broker.emqx.io:8084/mqtt",
        "wss://broker.hivemq.com:8884/mqtt",
        "wss://test.mosquitto.org:8081/mqtt",
      ];
  QZ.brokerParam = params.get("broker");

  QZ.AVATARS = ["🐶","🐱","🐼","🦊","🐨","🐯","🦁","🐸","🐵","🐧","🐰","🐻","🐹","🦄","🐙","🦋",
                "🐢","🐬","🦖","🐳","🦉","🐝","🐞","🦀","🐮","🐷","🐥","🦩","🐲","🌸","🍓","⭐"];
  QZ.AV_COLORS = ["#ff8fab","#ffb703","#8ecae6","#90be6d","#c77dff","#f9844a","#4cc9f0","#f15bb5"];
  QZ.avatarHTML = (i, size = 56) => {
    i = Math.max(0, Math.min(QZ.AVATARS.length - 1, i | 0));
    return `<span class="av" style="--s:${size}px;background:${QZ.AV_COLORS[i % QZ.AV_COLORS.length]}">${QZ.AVATARS[i]}</span>`;
  };

  QZ.esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  QZ.rid = (n = 10) => {
    const a = new Uint8Array(n);
    crypto.getRandomValues(a);
    return Array.from(a, (b) => "abcdefghijkmnpqrstuvwxyz23456789"[b % 32]).join("");
  };
  QZ.store = {
    get(k, d = null) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
    del(k) { try { localStorage.removeItem(k); } catch {} },
  };

  /* ---------- การเข้ารหัส ---------- */
  const te = new TextEncoder(), td = new TextDecoder();
  const b64 = (u8) => { let s = ""; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };
  const unb64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
  async function deriveKey(pin) {
    const base = await crypto.subtle.importKey("raw", te.encode(pin), "PBKDF2", false, ["deriveKey"]);
    return crypto.subtle.deriveKey(
      { name: "PBKDF2", salt: te.encode(QZ.PREFIX), iterations: 60000, hash: "SHA-256" },
      base, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
  }

  /* ---------- การเชื่อมต่อ ---------- */
  class Net {
    constructor(pin, onMsg) {
      this.pin = pin;
      this.onMsg = onMsg;
      this.subs = new Set();
      this.seen = new Map();
      this.clients = [];
      this.onStatus = () => {};
    }
    topic(sub) { return `${QZ.PREFIX}/${this.pin}/${sub}`; }
    async start() {
      this.key = await deriveKey(this.pin);
      this.clients = QZ.BROKERS.map((url) => {
        const c = mqtt.connect(url, {
          clientId: "q" + QZ.rid(12), clean: true, keepalive: 30,
          reconnectPeriod: 2500, connectTimeout: 10000, resubscribe: true,
        });
        c.on("connect", () => {
          if (this.subs.size) c.subscribe([...this.subs].map((s) => this.topic(s)), { qos: 1 });
          this._status();
        });
        c.on("close", () => this._status());
        c.on("offline", () => this._status());
        c.on("error", () => {});
        c.on("message", (t, buf, pkt) => this._in(t, buf, !!(pkt && pkt.retain)));
        return c;
      });
    }
    connected() { return this.clients.filter((c) => c.connected).length; }
    _status() { this.onStatus(this.connected(), this.clients.length); }
    waitConnected(ms = 15000) {
      return new Promise((res) => {
        const t0 = Date.now();
        const tick = () => (this.connected() ? res(true) : Date.now() - t0 > ms ? res(false) : setTimeout(tick, 150));
        tick();
      });
    }
    subscribe(sub) {
      this.subs.add(sub);
      for (const c of this.clients) if (c.connected) c.subscribe(this.topic(sub), { qos: 1 });
    }
    unsubscribe(sub) {
      this.subs.delete(sub);
      for (const c of this.clients) if (c.connected) c.unsubscribe(this.topic(sub));
    }
    async publish(sub, obj, retain = false) {
      obj = Object.assign({ mid: QZ.rid(10) }, obj);
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, this.key, te.encode(JSON.stringify(obj))));
      const out = new Uint8Array(12 + ct.length);
      out.set(iv); out.set(ct, 12);
      const payload = b64(out);
      for (const c of this.clients) c.publish(this.topic(sub), payload, { qos: 1, retain });
    }
    clear(sub) { for (const c of this.clients) c.publish(this.topic(sub), "", { qos: 1, retain: true }); }
    async _in(topic, buf, retained) {
      const sub = topic.slice(this.topic("").length);
      if (!buf || !buf.length) return this.onMsg(sub, null, retained);
      let obj;
      try {
        const raw = unb64(td.decode(buf));
        const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: raw.subarray(0, 12) }, this.key, raw.subarray(12));
        obj = JSON.parse(td.decode(pt));
      } catch { return; }
      if (this.seen.has(obj.mid)) return;
      this.seen.set(obj.mid, 1);
      if (this.seen.size > 3000) this.seen.delete(this.seen.keys().next().value);
      this.onMsg(sub, obj, retained);
    }
    stop() { for (const c of this.clients) c.end(true); }
  }
  QZ.Net = Net;

  /* ---------- คะแนน ---------- */
  QZ.points = (ms, durMs, streak) => {
    const r = Math.min(1, Math.max(0, ms / durMs));
    return Math.round(1000 * (1 - r / 2)) + Math.min(Math.max(streak - 1, 0), 5) * 100;
  };

  /* ---------- เสียง ---------- */
  const A = (QZ.audio = { muted: false, volume: 0.7, track: null });
  let ctx, master, musicBus, noiseBuf, timer, nextT, step;
  function ensure() {
    if (ctx) { if (ctx.state === "suspended") ctx.resume(); return true; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return false;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = A.muted ? 0 : A.volume;
    const comp = ctx.createDynamicsCompressor();
    master.connect(comp).connect(ctx.destination);
    musicBus = ctx.createGain();
    musicBus.gain.value = 0.55;
    musicBus.connect(master);
    noiseBuf = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
    const d = noiseBuf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    return true;
  }
  A.unlock = ensure;
  A.setMuted = (m) => { A.muted = m; if (master) master.gain.setTargetAtTime(m ? 0 : A.volume, ctx.currentTime, 0.05); };
  const mtof = (m) => 440 * Math.pow(2, (m - 69) / 12);
  function tone(m, t, dur, { type = "triangle", gain = 0.2, out, attack = 0.005, slide } = {}) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type;
    o.frequency.setValueAtTime(mtof(m), t);
    if (slide) o.frequency.exponentialRampToValueAtTime(mtof(m + slide), t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(gain, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(out || master);
    o.start(t); o.stop(t + dur + 0.05);
  }
  function noise(t, dur, { gain = 0.15, hp = 6000, out } = {}) {
    const s = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
    s.buffer = noiseBuf; f.type = "highpass"; f.frequency.value = hp;
    g.gain.setValueAtTime(gain, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f).connect(g).connect(out || master);
    s.start(t); s.stop(t + dur + 0.05);
  }
  function kick(t, out) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.setValueAtTime(150, t);
    o.frequency.exponentialRampToValueAtTime(45, t + 0.12);
    g.gain.setValueAtTime(0.7, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.25);
    o.connect(g).connect(out);
    o.start(t); o.stop(t + 0.3);
  }

  // เพลงประกอบที่แต่งขึ้นเอง: เก็บเป็นคอร์ด + รูปแบบจังหวะ เล่นวนต่อเนื่อง
  const TRACKS = {
    lobby: { bpm: 116, chords: [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]],
      mel: [72, -1, 74, 76, -1, 76, 74, 72, 69, -1, 72, -1, 67, -1, -1, -1, 69, -1, 72, 74, -1, 72, 69, 67, 65, -1, 67, 69, 67, -1, -1, -1],
      kick: [0, 8], snare: [4, 12], hat: 2, bass: [0, 3, 8, 11, 14], arp: 2 },
    question: { bpm: 148, chords: [[57, 60, 64], [57, 60, 64], [53, 57, 60], [52, 56, 59]],
      kick: [0, 4, 8, 12], snare: [4, 12], hat: 1, bass: [0, 2, 4, 6, 8, 10, 12, 14], arp: 1 },
    board: { bpm: 104, chords: [[53, 57, 60], [55, 59, 62], [52, 55, 60], [57, 60, 64]],
      kick: [0, 10], snare: [4, 12], hat: 2, bass: [0, 6, 8], arp: 4 },
    end: { bpm: 124, chords: [[60, 64, 67], [65, 69, 72], [67, 71, 74], [60, 64, 67]],
      mel: [72, -1, 72, 76, -1, 79, -1, 76, 77, -1, 77, 81, -1, 79, -1, -1, 79, -1, 77, 76, -1, 74, -1, 76, 72, -1, -1, -1, -1, -1, -1, -1],
      kick: [0, 8], snare: [4, 12], hat: 2, bass: [0, 4, 8, 12], arp: 2 },
  };
  function playStep(tr, s, t) {
    const pos = s % 16, bar = Math.floor(s / 16) % tr.chords.length, ch = tr.chords[bar];
    const sixteenth = 60 / tr.bpm / 4;
    if (tr.kick.includes(pos)) kick(t, musicBus);
    if (tr.snare.includes(pos)) { noise(t, 0.14, { gain: 0.22, hp: 1800, out: musicBus }); tone(ch[0] + 12, t, 0.06, { type: "square", gain: 0.03, out: musicBus }); }
    if (pos % tr.hat === 0) noise(t, 0.03, { gain: pos % 4 === 2 ? 0.08 : 0.04, out: musicBus });
    if (tr.bass.includes(pos)) tone(ch[0] - 24, t, sixteenth * 1.8, { type: "sawtooth", gain: 0.11, out: musicBus });
    if (pos % tr.arp === 0) {
      const n = ch[(pos / tr.arp) % 3] + 12;
      tone(n, t, sixteenth * 1.5, { type: "square", gain: 0.035, out: musicBus });
    }
    if (pos === 0) for (const n of ch) tone(n, t, sixteenth * 15, { type: "sine", gain: 0.035, attack: 0.15, out: musicBus });
    if (tr.mel) {
      const m = tr.mel[(s * 1) % (tr.mel.length * 2) >> 1];
      if (s % 2 === 0 && m > 0) tone(m, t, sixteenth * 2.6, { type: "triangle", gain: 0.09, out: musicBus });
    }
  }
  A.music = (name) => {
    if (!ensure()) return;
    if (A.track === name) return;
    A.stopMusic();
    const tr = TRACKS[name];
    if (!tr) return;
    A.track = name;
    step = 0;
    nextT = ctx.currentTime + 0.08;
    musicBus.gain.cancelScheduledValues(ctx.currentTime);
    musicBus.gain.setValueAtTime(0.55, ctx.currentTime);
    timer = setInterval(() => {
      const st = 60 / tr.bpm / 4;
      while (nextT < ctx.currentTime + 0.15) { playStep(tr, step++, nextT); nextT += st; }
    }, 25);
  };
  A.stopMusic = () => {
    if (timer) clearInterval(timer);
    timer = null;
    A.track = null;
  };
  A.sfx = (name) => {
    if (!ensure()) return;
    const t = ctx.currentTime + 0.01;
    switch (name) {
      case "join": tone(79, t, 0.08, { type: "sine", gain: 0.2 }); tone(86, t + 0.07, 0.12, { type: "sine", gain: 0.2 }); break;
      case "tap": tone(84, t, 0.06, { type: "sine", gain: 0.2 }); break;
      case "tick": tone(96, t, 0.05, { type: "square", gain: 0.06 }); break;
      case "correct": [72, 76, 79, 84].forEach((n, i) => tone(n, t + i * 0.08, 0.25, { type: "triangle", gain: 0.22 })); break;
      case "wrong": tone(55, t, 0.25, { type: "sawtooth", gain: 0.15, slide: -3 }); tone(51, t + 0.22, 0.4, { type: "sawtooth", gain: 0.15, slide: -4 }); break;
      case "timeup": tone(48, t, 0.7, { type: "square", gain: 0.12 }); tone(55, t, 0.7, { type: "square", gain: 0.08 }); noise(t, 0.5, { gain: 0.2, hp: 400 }); break;
      case "reveal": noise(t, 0.35, { gain: 0.15, hp: 2500 }); [67, 72, 76, 79].forEach((n, i) => tone(n, t + 0.1 + i * 0.06, 0.4, { type: "sine", gain: 0.12 })); break;
      case "start": [60, 64, 67, 72, 76, 79, 84].forEach((n, i) => tone(n, t + i * 0.06, 0.3, { type: "square", gain: 0.06 })); break;
      case "drumroll":
        for (let i = 0; i < 26; i++) noise(t + i * 0.05, 0.05, { gain: 0.06 + i * 0.006, hp: 1500 });
        tone(60, t + 1.35, 0.6, { type: "square", gain: 0.1 }); noise(t + 1.35, 0.6, { gain: 0.25, hp: 3000 });
        break;
      case "fanfare":
        [[60, 0], [64, 0.15], [67, 0.3], [72, 0.45], [67, 0.75], [72, 0.9]].forEach(([n, d]) => tone(n, t + d, d === 0.9 ? 1.2 : 0.18, { type: "sawtooth", gain: 0.09 }));
        [64, 67, 72].forEach((n) => tone(n, t + 0.9, 1.2, { type: "triangle", gain: 0.08 }));
        break;
    }
  };

  /* ---------- พลุกระดาษ ---------- */
  QZ.confetti = (n = 120) => {
    const box = document.createElement("div");
    box.className = "confetti";
    const cols = ["#ff4d8d", "#ffd166", "#06d6a0", "#4cc9f0", "#c77dff", "#ffffff"];
    for (let i = 0; i < n; i++) {
      const p = document.createElement("i");
      p.style.left = Math.random() * 100 + "%";
      p.style.background = cols[i % cols.length];
      p.style.animationDelay = Math.random() * 1.2 + "s";
      p.style.animationDuration = 2.4 + Math.random() * 2 + "s";
      p.style.transform = `rotate(${Math.random() * 360}deg)`;
      box.appendChild(p);
    }
    document.body.appendChild(box);
    setTimeout(() => box.remove(), 5500);
  };
})();
