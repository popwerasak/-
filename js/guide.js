// คู่มือคำแนะนำสุขภาพ ปรับตามผลวัดของแต่ละคน
// อ้างอิงหลักจากกรมอนามัย กระทรวงสาธารณสุข (ดูรายการ GUIDE_REFS ด้านล่าง)
// ใช้ has() / fmt() / esc() จากสคริปต์หลักใน index.html

const GUIDE_REFS = [
  ["กรมอนามัย กระทรวงสาธารณสุข", "https://www.anamai.moph.go.th/"],
  ["กองโภชนาการ กรมอนามัย – ธงโภชนาการ, ปริมาณสารอาหารอ้างอิงที่ควรได้รับประจำวันสำหรับคนไทย พ.ศ. 2563 (Thai DRI)", "https://nutrition2.anamai.moph.go.th/"],
  ["กองกิจกรรมทางกายเพื่อสุขภาพ กรมอนามัย – คำแนะนำการมีกิจกรรมทางกายสำหรับคนไทย", "https://dopah.anamai.moph.go.th/"],
  ["กรมอนามัย แนะควบคุมน้ำหนักด้วยสูตร 2:1:1 (The Bangkok Insight)", "https://www.thebangkokinsight.com/news/lifestyle/81955/"],
  ["อธิบดีกรมอนามัย แนะลดหวาน มัน เค็ม 6:6:1 (ฐานเศรษฐกิจ)", "https://www.thansettakij.com/health/wellbeing/558391"],
  ["กรมอนามัย: กิจกรรมทางกาย 150 นาที/สัปดาห์ ลดเสี่ยงโรคหัวใจ (มติชน)", "https://www.matichon.co.th/local/news_2705652"],
];

// ปริมาณโปรตีน / แคลเซียมเป็นค่าโดยประมาณจากตารางคุณค่าทางโภชนาการอาหารไทย
const PROTEIN_FOODS = [
  ["ไข่ไก่ 1 ฟอง", 7],
  ["อกไก่ต้ม/ย่าง 1 ฝ่ามือ (~100 ก.)", 25],
  ["ปลาทู / ปลานิล นึ่ง 1 ชิ้นกลาง (~100 ก.)", 20],
  ["หมูเนื้อแดง 6 ช้อนกินข้าว (~90 ก.)", 18],
  ["กุ้ง 6–7 ตัวกลาง (~100 ก.)", 20],
  ["เต้าหู้แข็ง ½ แผ่น (~100 ก.)", 12],
  ["นมจืดพร่องมันเนย 1 กล่อง (200 มล.)", 7],
  ["นมถั่วเหลืองไม่หวาน 1 กล่อง (250 มล.)", 7],
  ["ถั่วเขียว/ถั่วแดงต้ม ½ ถ้วย", 7],
  ["โยเกิร์ตไขมันต่ำ 1 ถ้วย (150 ก.)", 6],
];

const CALCIUM_FOODS = [
  ["นมจืด 1 กล่อง (200 มล.)", "~220"],
  ["โยเกิร์ต 1 ถ้วย (150 ก.)", "~180"],
  ["ปลาเล็กปลาน้อยทอด/คั่ว 2 ช้อนโต๊ะ", "~200"],
  ["เต้าหู้แข็ง ½ แผ่น (~100 ก.)", "~150–250"],
  ["กุ้งแห้ง / กุ้งฝอย 1 ช้อนโต๊ะ", "~100–150"],
  ["ผักใบเขียวเข้ม (คะน้า ผักกาดเขียว ใบยอ ผักโขม) สุก 1 ทัพพี", "~80–150"],
  ["งาดำคั่ว 1 ช้อนโต๊ะ", "~90"],
  ["ปลากระป๋อง (กินทั้งก้าง) ½ กระป๋อง", "~150–200"],
];

function guideTable(rows, h1, h2){
  return `<table><thead><tr><th>${h1}</th><th>${h2}</th></tr></thead><tbody>${rows.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join("")}</tbody></table>`;
}

// หัวข้อคู่มือแสดงเป็นปุ่มการ์ด กดแล้วเปิดรายละเอียดในหน้าต่าง (dialog)
const GUIDE_META = {
  "⚖️": { c: "#6366f1", sub: "เป้าหมายน้ำหนัก BMI และรอบเอว" },
  "🥗": { c: "#16a34a", sub: "จาน 2:1:1 · หวาน มัน เค็ม 6:6:1" },
  "🍳": { c: "#ea580c", sub: "ควรกินวันละกี่กรัม กินอะไรดี" },
  "🦴": { c: "#0891b2", sub: "แคลเซียม วิตามินดี อาหารบำรุงกระดูก" },
  "🏃": { c: "#dc2626", sub: "เพิ่มกล้ามเนื้อ ลดไขมัน ตาราง 7 วัน" },
  "🏋️": { c: "#0d9488", sub: "ภาพท่าทาง จำนวนเซต ครั้ง และเวลาพัก" },
  "🍱": { c: "#ca8a04", sub: "ตัวอย่างอาหาร เช้า กลางวัน เย็น" },
  "💡": { c: "#7c3aed", sub: "นอน ดื่มน้ำ ความเครียด เมื่อไรควรพบแพทย์" },
};
let guideCards = [];
const guideBodies = {};

function guideSection(title, body, important){
  const icon = [...title][0] === "⚖" ? "⚖️" : Object.keys(GUIDE_META).find(k => title.startsWith(k)) || "💡";
  const meta = GUIDE_META[icon] || GUIDE_META["💡"];
  const id = "g" + guideCards.length;
  const name = title.replace(icon, "").trim();
  guideBodies[id] = { icon, name, color: meta.c, body };
  guideCards.push(`<button type="button" class="gcard" data-guide="${id}" style="--gc:${meta.c}">
    <span class="gicon" aria-hidden="true">${icon}</span>
    <span class="gtext"><span class="gtitle">${name}</span><span class="gsub">${meta.sub}</span></span>
    ${important ? `<span class="gbadge">สำคัญสำหรับคุณ</span>` : ""}<span class="garrow" aria-hidden="true">›</span></button>`);
  return "";
}

// ---------- ภาพประกอบ ----------
function bmiGauge(bmi){
  if (!has(bmi)) return "";
  const lo = 15, hi = 35, X = v => 10 + (Math.min(Math.max(v, lo), hi) - lo) / (hi - lo) * 300;
  const zones = [[lo, 18.5, "#60a5fa", "ผอม"], [18.5, 23, "#22c55e", "ปกติ"], [23, 25, "#facc15", "เกิน"], [25, 30, "#fb923c", "อ้วน 1"], [30, hi, "#ef4444", "อ้วน 2"]];
  return `<figure class="gfig"><svg viewBox="0 0 320 92" role="img" aria-label="มาตรวัด BMI ${fmt(bmi)}">
    ${zones.map(([a, b, c, t]) => `<rect x="${X(a)}" y="38" width="${X(b) - X(a)}" height="18" fill="${c}"/><text x="${(X(a) + X(b)) / 2}" y="74" font-size="11" text-anchor="middle">${t}</text>`).join("")}
    ${[18.5, 23, 25, 30].map(v => `<text x="${X(v)}" y="88" font-size="9" text-anchor="middle">${v}</text>`).join("")}
    <polygon points="${X(bmi) - 8},14 ${X(bmi) + 8},14 ${X(bmi)},34" style="fill:var(--text)"/>
    <text x="${X(bmi)}" y="10" font-size="12" font-weight="700" text-anchor="middle" style="fill:var(--text)">BMI ของคุณ ${fmt(bmi)}</text>
  </svg><figcaption>เกณฑ์ BMI สำหรับคนเอเชีย ช่วงสีเขียวคือเป้าหมาย</figcaption></figure>`;
}

function waistFig(waist, h){
  if (!has(waist) || !h) return "";
  const lim = h * 50, max = Math.max(waist, lim) * 1.1, W = v => v / max * 100;
  const over = waist > lim;
  return `<figure class="gfig"><div class="hbar"><span>รอบเอวของคุณ</span><div><i style="width:${W(waist)}%;background:${over ? "var(--bad)" : "var(--good)"}"></i></div><b>${fmt(waist)} ซม.</b></div>
    <div class="hbar"><span>ส่วนสูง ÷ 2</span><div><i style="width:${W(lim)}%;background:var(--accent)"></i></div><b>${fmt(lim)} ซม.</b></div>
    <figcaption>📏 รอบเอวไม่ควรเกินส่วนสูงหาร 2 ${over ? `(ตอนนี้เกิน ${fmt(waist - lim)} ซม.)` : "(อยู่ในเกณฑ์)"}</figcaption></figure>`;
}

function plateFig(){
  // จาน 2:1:1 : ผักครึ่งจาน (ซ้าย) ข้าว ¼ (ขวาบน) โปรตีน ¼ (ขวาล่าง)
  return `<figure class="gfig"><svg viewBox="0 0 320 210" role="img" aria-label="จานอาหารสูตร 2:1:1">
    <circle cx="120" cy="105" r="98" fill="#e5e7eb"/><circle cx="120" cy="105" r="86" fill="#fff" stroke="#d1d5db"/>
    <path d="M120 105 L120 19 A86 86 0 0 0 120 191 Z" fill="#4ade80"/>
    <path d="M120 105 L120 19 A86 86 0 0 1 206 105 Z" fill="#fde68a"/>
    <path d="M120 105 L206 105 A86 86 0 0 1 120 191 Z" fill="#fca5a5"/>
    <text x="72" y="100" font-size="30" text-anchor="middle">🥦🥬</text><text x="72" y="128" font-size="13" font-weight="700" text-anchor="middle" fill="#14532d">ผัก 2 ส่วน</text>
    <text x="158" y="68" font-size="24" text-anchor="middle">🍚</text><text x="158" y="88" font-size="11" font-weight="700" text-anchor="middle" fill="#713f12">ข้าว/แป้ง 1</text>
    <text x="158" y="140" font-size="24" text-anchor="middle">🐟</text><text x="158" y="160" font-size="11" font-weight="700" text-anchor="middle" fill="#7f1d1d">โปรตีน 1</text>
    <circle cx="270" cy="70" r="34" fill="#fed7aa"/><text x="270" y="78" font-size="26" text-anchor="middle">🍊</text><text x="270" y="122" font-size="11" text-anchor="middle">+ ผลไม้</text>
    <circle cx="270" cy="160" r="22" fill="#dbeafe"/><text x="270" y="167" font-size="20" text-anchor="middle">💧</text><text x="270" y="198" font-size="11" text-anchor="middle">น้ำเปล่า</text>
  </svg><figcaption>จาน 9 นิ้ว แบ่ง 4 ส่วน: ผักครึ่งจาน ข้าว ¼ โปรตีน ¼</figcaption></figure>`;
}

function spoonsFig(){
  const row = (label, n, emoji, color, note) => `<div class="spoons"><span class="sl" style="color:${color}"><b>${label}</b><br><small>${note}</small></span><span class="si">${Array.from({ length: n }, () => `<span style="background:${color}">${emoji}</span>`).join("")}</span><b class="sn" style="color:${color}">${n}</b></div>`;
  return `<figure class="gfig">${row("หวาน", 6, "🍬", "#db2777", "น้ำตาล")}${row("มัน", 6, "🫒", "#ca8a04", "น้ำมัน")}${row("เค็ม", 1, "🧂", "#2563eb", "เกลือ")}
    <figcaption>ไม่เกินกี่ <b>ช้อนชา</b> ต่อวัน (สูตร 6 : 6 : 1)</figcaption></figure>`;
}

function foodBars(rows, unit, max){
  return `<figure class="gfig">${rows.map(([n, v]) => {
    const num = typeof v === "number" ? v : Number(String(v).replace(/[^\d–-]/g, "").split(/[–-]/).pop());
    return `<div class="hbar"><span>${n}</span><div><i style="width:${Math.min(num / max * 100, 100)}%"></i></div><b>${v} ${unit}</b></div>`;
  }).join("")}</figure>`;
}

function goalFig(items, target, unit, label){
  const total = items.reduce((s, [, v]) => s + v, 0);
  const colors = ["#f97316", "#22c55e", "#3b82f6", "#a855f7", "#eab308"];
  return `<figure class="gfig"><div class="goal">${items.map(([n, v], i) => `<i style="width:${v / Math.max(total, target) * 100}%;background:${colors[i % 5]}" title="${n}">${n}</i>`).join("")}</div>
    <div class="goal-axis"><span>0</span><span>${label} ${fmt(target, 0)} ${unit}</span></div>
    <figcaption>${items.map(([n, v]) => `${n} ${v}`).join(" + ")} = <b>${fmt(total, 0)} ${unit}</b></figcaption></figure>`;
}

function weekFig(){
  const days = [["จ", "💪", "เวท", "#ef4444"], ["อ", "🚶", "เดินเร็ว", "#22c55e"], ["พ", "💪", "เวท", "#ef4444"], ["พฤ", "🏊", "แอโรบิก", "#22c55e"], ["ศ", "💪", "เวท+เดิน", "#ef4444"], ["ส", "🏸", "กลางแจ้ง", "#22c55e"], ["อา", "🧘", "พัก", "#94a3b8"]];
  return `<figure class="gfig"><div class="week">${days.map(([d, e, t, c]) => `<div style="--dc:${c}"><b>${d}</b><span>${e}</span><small>${t}</small></div>`).join("")}</div>
    <figcaption><span style="color:#ef4444">■</span> ฝึกกล้ามเนื้อ ≥ 2 วัน · <span style="color:#22c55e">■</span> แอโรบิกรวม 150–300 นาที · <span style="color:#94a3b8">■</span> พัก</figcaption></figure>`;
}

function talkFig(){
  return `<figure class="gfig"><div class="talk">
    <div><span>😌</span><b>เบา</b><small>ร้องเพลงได้</small></div>
    <div class="on"><span>🙂</span><b>ปานกลาง ✓</b><small>พูดเป็นประโยคได้ แต่ร้องเพลงไม่ได้</small></div>
    <div><span>😮‍💨</span><b>หนัก</b><small>พูดได้แค่ 2–3 คำ</small></div>
  </div><figcaption>ทดสอบความหนักด้วยการพูด (Talk test)</figcaption></figure>`;
}

function iconRow(items){
  return `<figure class="gfig"><div class="irow">${items.map(([e, t]) => `<div><span>${e}</span><small>${t}</small></div>`).join("")}</div></figure>`;
}

function healthGuide(d, a){
  guideCards = [];
  const female = a.sex === "female";
  const age = has(d.age) ? d.age : 30;
  const overweight = has(a.bmi) && a.bmi >= 23;
  const underweight = has(a.bmi) && a.bmi < 18.5;
  const pbfHigh = has(a.pbf) && a.pbf > (female ? 28 : 20);
  const vflHigh = has(d.vfl) && d.vfl >= 10;
  const waistLim = a.h ? Math.min(a.h * 50, female ? 80 : 90) : (female ? 80 : 90);
  const waistHigh = has(d.waist) && d.waist > waistLim;
  const smmLow = has(d.smm) && has(d.weight) && (has(d.smmMin) ? d.smm < d.smmMin : d.smm / d.weight < (female ? 0.36 : 0.40));
  const mineralLow = has(d.mineral) && has(d.mineralMin) && d.mineral < d.mineralMin;
  const needLoss = overweight || pbfHigh || vflHigh || waistHigh || (has(d.fatControl) && d.fatControl < 0);

  // น้ำหนักที่ใช้คำนวณโปรตีน: ถ้าน้ำหนักเกินใช้น้ำหนักเป้าหมาย/มาตรฐาน
  const refW = needLoss ? (has(d.targetWeight) ? d.targetWeight : (a.stdWeight || d.weight)) : d.weight;
  const proteinBase = has(refW) ? refW * 1.0 : null;
  const calcium = age >= 51 ? 1000 : 800;
  const tdee = has(d.tdee) ? d.tdee : null;
  const kcalTarget = tdee ? (needLoss ? Math.max(tdee - 500, has(d.bmr) ? d.bmr : (female ? 1200 : 1500)) : tdee) : (female ? 1600 : 2000);

  // --- สิ่งที่ควรโฟกัส
  const focus = [];
  if (overweight) focus.push(`BMI ${fmt(a.bmi)} เกินเกณฑ์คนเอเชีย (18.5–22.9) → ลดน้ำหนักแบบค่อยเป็นค่อยไป`);
  if (underweight) focus.push(`BMI ${fmt(a.bmi)} ต่ำกว่าเกณฑ์ → เพิ่มพลังงานและโปรตีน ไม่ควรอดอาหาร`);
  if (pbfHigh) focus.push(`% ไขมัน ${fmt(a.pbf)}% สูง → ลดไขมัน โดยรักษากล้ามเนื้อไว้`);
  if (vflHigh) focus.push(`ไขมันในช่องท้องระดับ ${d.vfl} สูง → ลดหวาน ลดแอลกอฮอล์ เพิ่มการเคลื่อนไหว`);
  if (waistHigh) focus.push(`รอบเอว ${fmt(d.waist)} ซม. เกินเกณฑ์ (ไม่ควรเกิน ${fmt(waistLim)} ซม.)`);
  if (smmLow) focus.push(`กล้ามเนื้อลาย ${fmt(d.smm)} กก. ค่อนข้างน้อย → ฝึกแรงต้าน + โปรตีนให้พอ`);
  if (mineralLow) focus.push(`แร่ธาตุ/กระดูก ${fmt(d.mineral, 2)} กก. ต่ำกว่าเกณฑ์ → เพิ่มแคลเซียม วิตามินดี และออกกำลังกายแบบลงน้ำหนัก`);
  if (!focus.length) focus.push("ผลโดยรวมอยู่ในเกณฑ์ดี → รักษาพฤติกรรมการกินและการออกกำลังกายตามคำแนะนำด้านล่าง");

  const parts = [];

  parts.push(`<div class="tile bg-info" style="margin-bottom:8px"><div class="k">สิ่งที่ควรโฟกัสจากผลของคุณ</div>
    <ul class="recs">${focus.map(f => `<li>${f}</li>`).join("")}</ul></div>`);

  // 1. ลด BMI / น้ำหนัก
  const wAt229 = a.h ? 22.9 * a.h * a.h : null;
  parts.push(guideSection("⚖️ BMI เกิน ทำอย่างไรให้ลดลง", `
    ${bmiGauge(a.bmi)}${waistFig(d.waist, a.h)}
    ${iconRow([["🍽️", "อาหาร"], ["🏃", "ออกกำลังกาย"], ["😊", "อารมณ์"], ["🚭", "ไม่สูบบุหรี่"], ["🚫🍺", "ไม่ดื่มสุรา"]])}
    <ul class="recs">
      <li><b>เป้าหมาย BMI สำหรับคนไทย 18.5–22.9</b>${wAt229 && has(d.weight) && d.weight > wAt229 ? ` – สำหรับส่วนสูง ${d.height} ซม. น้ำหนักไม่ควรเกิน <b>${fmt(wAt229)} กก.</b> (ต้องลดอีกประมาณ ${fmt(d.weight - wAt229)} กก.)` : ""}</li>
      <li><b>ลดช้า ๆ สัปดาห์ละ 0.5–1 กก.</b> ด้วยการกินให้น้อยกว่าที่ร่างกายใช้ประมาณ <b>500 kcal/วัน</b>${tdee ? ` → สำหรับคุณคือกินวันละประมาณ <b>${fmt(kcalTarget, 0)} kcal</b>` : ""} ลดเร็วกว่านี้มักเสียกล้ามเนื้อและกลับมาอ้วนง่าย (โยโย่)</li>
      <li>ไม่ควรกินต่ำกว่า ${has(d.bmr) ? `BMR (${fmt(d.bmr, 0)} kcal)` : (female ? "1,200 kcal/วัน" : "1,500 kcal/วัน")} หากไม่ได้อยู่ในการดูแลของแพทย์ ไม่อดมื้อเช้า และไม่ใช้ยาลดความอ้วนเอง</li>
      <li><b>รอบเอวไม่ควรเกินส่วนสูง ÷ 2</b> (กรมอนามัย) ${a.h ? `= ${fmt(a.h * 50)} ซม.` : ""} วัดรอบเอวทุกสัปดาห์ เพราะบอกการลดไขมันหน้าท้องได้ดีกว่าน้ำหนักอย่างเดียว</li>
      <li>เป้าหมายแรกที่ทำได้จริง: <b>ลด 5–10% ของน้ำหนักตัว</b>${has(d.weight) ? ` (${fmt(d.weight * 0.05)}–${fmt(d.weight * 0.1)} กก.)` : ""} ภายใน 3–6 เดือน ช่วยลดความเสี่ยงเบาหวาน ความดัน ไขมันในเลือดได้ชัดเจน</li>
      <li>ใช้ 3 อ. ของกรมอนามัย: <b>อาหาร</b> (กินพอดี ลดหวาน มัน เค็ม) · <b>ออกกำลังกาย</b> (ขยับให้มากขึ้น) · <b>อารมณ์</b> (นอนพอ จัดการความเครียด ไม่กินเพราะเครียด) และ 2 ส.: <b>ไม่สูบบุหรี่ ไม่ดื่มสุรา</b></li>
    </ul>`, overweight || pbfHigh));

  // 2. อาหารลดน้ำหนัก
  parts.push(guideSection("🥗 การกินอาหารเพื่อลดน้ำหนัก", `
    <h3>สูตรจานอาหาร 2 : 1 : 1 (กรมอนามัย)</h3>${plateFig()}
    <p class="mmsg">แบ่งจานขนาด 9 นิ้วเป็น 4 ส่วน: <b>ผัก 2 ส่วน</b> (ครึ่งจาน) · <b>ข้าว/แป้ง 1 ส่วน</b> (เลือกข้าวกล้อง ข้าวไม่ขัดสี) · <b>เนื้อสัตว์ไขมันต่ำ/โปรตีน 1 ส่วน</b> แล้วเสริมผลไม้รสไม่หวานจัดหลังอาหาร</p>
    <h3>หวาน มัน เค็ม 6 : 6 : 1 ต่อวัน</h3>${spoonsFig()}
    <ul class="recs">
      <li><b>น้ำตาลไม่เกิน 6 ช้อนชา</b> (24 กรัม) – ชานมไข่มุก 1 แก้วมีน้ำตาลได้ถึง 10–15 ช้อนชา สั่ง "หวานน้อย" หรือ "ไม่หวาน" ดื่มน้ำเปล่าแทนน้ำหวาน/น้ำอัดลม</li>
      <li><b>น้ำมันไม่เกิน 6 ช้อนชา</b> – เลือกต้ม นึ่ง ย่าง อบ ยำ แทนทอด ผัดน้ำมันน้อย ลดกะทิ หนังสัตว์ และของทอด</li>
      <li><b>เกลือไม่เกิน 1 ช้อนชา</b> (โซเดียมไม่เกิน 2,000 มก.) – ชิมก่อนปรุง ลดน้ำปลา ซีอิ๊ว ผงชูรส น้ำจิ้ม อาหารแปรรูป บะหมี่กึ่งสำเร็จรูป ไม่ซดน้ำแกง/น้ำซุปจนหมด</li>
    </ul>
    <h3>ธงโภชนาการ (ปริมาณต่อวันสำหรับผู้ใหญ่ ${female ? "≈1,600" : "≈2,000"} kcal)</h3>
    <table><tbody>
      <tr><td>ข้าว แป้ง</td><td>${female ? "8" : "10"} ทัพพี (เลือกข้าวกล้อง/ไม่ขัดสี)</td></tr>
      <tr><td>ผัก</td><td>${female ? "4" : "5"} ทัพพีขึ้นไป</td></tr>
      <tr><td>ผลไม้</td><td>${female ? "4" : "5"} ส่วน (1 ส่วน ≈ กล้วยน้ำว้า 1 ผล, ส้ม 1 ผล, มะละกอ/แตงโม 6–8 ชิ้นคำ)</td></tr>
      <tr><td>เนื้อสัตว์</td><td>${female ? "6" : "9"} ช้อนกินข้าว</td></tr>
      <tr><td>นม</td><td>1 แก้ว (เลือกพร่องมันเนย/ขาดมันเนย รสจืด)</td></tr>
      <tr><td>น้ำมัน น้ำตาล เกลือ</td><td>ใช้แต่น้อยเท่าที่จำเป็น</td></tr>
    </tbody></table>
    <h3>เทคนิคที่ช่วยได้</h3>
    <ul class="recs">
      <li>กินครบ 3 มื้อ ตรงเวลา ไม่กินจุบจิบ งดของกินหลัง 2 ทุ่ม</li>
      <li>กินผักก่อน ตามด้วยโปรตีน แล้วค่อยกินข้าว – ช่วยให้อิ่มเร็วและน้ำตาลในเลือดไม่ขึ้นเร็ว</li>
      <li>ใช้จานเล็กลง เคี้ยวช้า ๆ วางช้อนระหว่างคำ ใช้เวลากิน 15–20 นาที</li>
      <li>งดหรือลดเครื่องดื่มแอลกอฮอล์ (เบียร์ 1 กระป๋อง ≈ 150 kcal และเพิ่มไขมันหน้าท้อง)</li>
      <li>ดูฉลากโภชนาการ / ฉลากหวาน มัน เค็ม (GDA) และเลือกอาหารที่มีสัญลักษณ์ <b>"ทางเลือกสุขภาพ"</b></li>
    </ul>`, needLoss));

  // 3. โปรตีน
  parts.push(guideSection("🍳 กินโปรตีนอย่างไรให้พอ", `
    <ul class="recs">
      <li><b>ปริมาณอ้างอิงสำหรับคนไทย (Thai DRI 2563) ≈ 1 กรัม ต่อน้ำหนักตัว 1 กก. ต่อวัน</b>${proteinBase ? ` → คุณควรได้อย่างน้อย <b>${fmt(proteinBase, 0)} กรัม/วัน</b>` : ""}</li>
      <li>ช่วงที่ลดน้ำหนักร่วมกับฝึกเวท หรือต้องการเพิ่มกล้ามเนื้อ ตามแนวทางโภชนาการการกีฬาอาจเพิ่มเป็น <b>1.2–1.6 ก./กก./วัน</b>${has(refW) ? ` (${fmt(refW * 1.2, 0)}–${fmt(refW * 1.6, 0)} กรัม)` : ""} เพื่อรักษากล้ามเนื้อ</li>
      <li><b>แบ่งกินทุกมื้อ</b> มื้อละประมาณ 20–30 กรัม ดีกว่ากินมื้อเดียวเยอะ ๆ และควรมีโปรตีนภายใน 1–2 ชม. หลังออกกำลังกาย</li>
      <li>เลือก <b>เนื้อสัตว์ไขมันต่ำ</b>: ปลา อกไก่ ไข่ขาว เต้าหู้ ถั่ว – ลดหมูสามชั้น ไส้กรอก หมูยอ เบคอน (โซเดียมและไขมันสูง)</li>
      <li>ผู้ที่เป็น<b>โรคไต</b> หรือมีโรคประจำตัว ควรปรึกษาแพทย์/นักกำหนดอาหารก่อนเพิ่มโปรตีน</li>
    </ul>
    <h3>ตัวอย่างอาหารและปริมาณโปรตีน (โดยประมาณ)</h3>
    ${foodBars(PROTEIN_FOODS, "ก.", 25)}
    ${proteinBase ? `<h3>ตัวอย่าง 1 วันให้ถึงเป้า</h3>${goalFig([["🥚 ไข่ 2 ฟอง", 14], ["🍗 อกไก่", 25], ["🐟 ปลา", 20], ["🥛 นม", 7]].concat(proteinBase > 66 ? [["⬜ เต้าหู้", 12]] : []), proteinBase, "กรัม", "เป้าหมาย")}` : ""}`, smmLow));

  // 4. กระดูก
  parts.push(guideSection("🦴 กินอย่างไรเพิ่มมวลกระดูก", `
    ${iconRow([["🥛", "แคลเซียม"], ["☀️", "วิตามินดี"], ["🚶", "ออกกำลังลงน้ำหนัก"], ["🚫☕", "ลดกาแฟ/น้ำอัดลม"], ["🧂↓", "ลดเค็ม"]])}
    <ul class="recs">
      <li><b>แคลเซียม</b>: ผู้ใหญ่อายุ 19–50 ปี ควรได้ <b>800 มก./วัน</b> อายุ 51 ปีขึ้นไป <b>1,000 มก./วัน</b> (Thai DRI 2563) → คุณควรได้ประมาณ <b>${fmt(calcium, 0)} มก./วัน</b></li>
      <li><b>วิตามินดี</b> ช่วยดูดซึมแคลเซียม – รับแดดอ่อนช่วงเช้าหรือเย็น 15–20 นาที กินปลา ไข่แดง นมเสริมวิตามินดี</li>
      <li><b>ออกกำลังกายแบบลงน้ำหนัก</b> เช่น เดินเร็ว เต้นแอโรบิก ขึ้นบันได และฝึกแรงต้าน ช่วยกระตุ้นการสร้างกระดูก</li>
      <li>ลดสิ่งที่ทำให้เสียแคลเซียม: <b>เค็มจัด กาแฟเกินวันละ 2–3 แก้ว น้ำอัดลม แอลกอฮอล์ และบุหรี่</b></li>
      <li>กินโปรตีนให้พอ เพราะโปรตีนเป็นโครงสร้างของกระดูก</li>
      <li>ไม่ควรกินแคลเซียมเสริมเองในปริมาณสูง ควรได้จากอาหารเป็นหลัก หรือปรึกษาแพทย์/เภสัชกร</li>
    </ul>
    <h3>อาหารแคลเซียมสูง (โดยประมาณ)</h3>
    ${foodBars(CALCIUM_FOODS, "มก.", 250)}
    <h3>ตัวอย่าง 1 วันให้ถึงเป้า</h3>
    ${goalFig([["🥛 นม 2 กล่อง", 440], ["⬜ เต้าหู้", 200], ["🥬 ผักใบเขียว", 100]].concat(calcium > 800 ? [["🐟 ปลาเล็กปลาน้อย", 200]] : [["⚫ งาดำ", 90]]), calcium, "มก.", "เป้าหมาย")}`, mineralLow));

  // 5. ออกกำลังกาย
  parts.push(guideSection("🏃 ออกกำลังกายอย่างไร เพิ่มกล้ามเนื้อ ลดไขมัน", `
    ${weekFig()}${talkFig()}
    <ul class="recs">
      <li><b>แอโรบิกระดับปานกลาง 150–300 นาที/สัปดาห์</b> (เช่น วันละ 30–60 นาที 5 วัน) หรือระดับหนัก 75–150 นาที/สัปดาห์ – ระดับปานกลางคือ "พูดเป็นประโยคได้ แต่ร้องเพลงไม่ได้"</li>
      <li><b>ฝึกกล้ามเนื้อ (แรงต้าน) อย่างน้อย 2 วัน/สัปดาห์</b> ให้ครบกล้ามเนื้อมัดใหญ่ ทั้งขา สะโพก หลัง อก ไหล่ แขน ท้อง</li>
      <li><b>ลดการนั่งนาน</b>: ลุกขยับทุก 1 ชั่วโมง เดินให้ได้วันละ 7,000–10,000 ก้าว</li>
      <li>เพิ่มความหนักทีละน้อย (ทำซ้ำให้ได้ 8–12 ครั้ง/เซต 2–3 เซต เมื่อทำได้ง่ายแล้วค่อยเพิ่มน้ำหนัก) และพักกล้ามเนื้อส่วนเดิม 48 ชม.</li>
      <li>อบอุ่นร่างกาย 5–10 นาทีก่อน และยืดเหยียดหลังออกกำลังกาย</li>
      ${has(a.bmi) && a.bmi >= 25 ? `<li>BMI ≥ 25: เลือกกิจกรรมที่ลดแรงกระแทกข้อเข่า เช่น ว่ายน้ำ เดินในน้ำ ปั่นจักรยาน</li>` : ""}
      <li>ผู้ที่มีโรคหัวใจ ความดันสูง เบาหวาน หรืออายุมาก ควรปรึกษาแพทย์ก่อนเริ่มออกกำลังกายหนัก</li>
    </ul>
    <h3>ตัวอย่างตาราง 1 สัปดาห์</h3>
    <table><tbody>
      <tr><td>จันทร์</td><td>ฝึกกล้ามเนื้อทั้งตัว 40 นาที (สควอท, ลันจ์, วิดพื้น/วิดพื้นบนเข่า, ดึงยางยืด, แพลงก์)</td></tr>
      <tr><td>อังคาร</td><td>เดินเร็ว / ปั่นจักรยาน 30–45 นาที</td></tr>
      <tr><td>พุธ</td><td>ฝึกกล้ามเนื้อทั้งตัว 40 นาที</td></tr>
      <tr><td>พฤหัสบดี</td><td>แอโรบิก / ว่ายน้ำ / เต้น 30–45 นาที</td></tr>
      <tr><td>ศุกร์</td><td>ฝึกกล้ามเนื้อ 30–40 นาที + เดิน 20 นาที</td></tr>
      <tr><td>เสาร์</td><td>กิจกรรมกลางแจ้ง 45–60 นาที (เดินป่า แบดมินตัน ฟุตบอล)</td></tr>
      <tr><td>อาทิตย์</td><td>พัก / ยืดเหยียด / โยคะเบา ๆ</td></tr>
    </tbody></table>
    <p class="hint">เริ่มต้นใหม่: ทำเพียง 2–3 วัน วันละ 10–15 นาทีก่อน แล้วค่อยเพิ่ม กล้ามเนื้อจะเพิ่มได้ต้องอาศัยทั้ง <b>การฝึก + โปรตีนพอ + นอนพอ</b></p>`, smmLow || needLoss));

  parts.push(guideSection("🏋️ ท่าออกกำลังกาย พร้อมเซตและเวลา", exerciseGuide(d, a), smmLow || needLoss));

  // 6. ตัวอย่างเมนู
  const lowCal = kcalTarget < 1700;
  parts.push(guideSection(`🍱 ตัวอย่างเมนู 1 วัน (ประมาณ ${fmt(Math.round(kcalTarget / 100) * 100, 0)} kcal)`, `
    <table><tbody>
      <tr><td><span class="meal">🌅</span><b>เช้า</b></td><td>ข้าวกล้อง ${lowCal ? "1" : "1½"} ทัพพี + ไข่ต้ม 2 ฟอง + ผัดผักรวมน้ำมันน้อย + นมจืดพร่องมันเนย 1 กล่อง<br><span class="hint">หรือ โจ๊กข้าวกล้องใส่ไข่ + ผัก / ขนมปังโฮลวีต 2 แผ่น + ไข่ + นม</span></td></tr>
      <tr><td><span class="meal">🍎</span><b>ว่างเช้า</b></td><td>ผลไม้ 1 ส่วน (ฝรั่ง ½ ผล / ส้ม 1 ผล / แอปเปิล 1 ผล)</td></tr>
      <tr><td><span class="meal">☀️</span><b>กลางวัน</b></td><td>ข้าวกล้อง ${lowCal ? "1½" : "2"} ทัพพี + แกงจืดเต้าหู้หมูสับ + ปลานึ่งมะนาว / ยำอกไก่ + ผักสด<br><span class="hint">อาหารจานเดียว: ก๋วยเตี๋ยวน้ำใส ไก่/ปลา เพิ่มผัก ไม่เติมน้ำตาล · ข้าวกะเพราไก่ไข่ต้ม (ไม่ทอดไข่) + ผักแนม</span></td></tr>
      <tr><td><span class="meal">🥛</span><b>ว่างบ่าย</b></td><td>โยเกิร์ตไขมันต่ำ 1 ถ้วย / นมถั่วเหลืองไม่หวาน / ถั่วอบ 1 กำมือเล็ก</td></tr>
      <tr><td><span class="meal">🌙</span><b>เย็น</b></td><td>ข้าวกล้อง ${lowCal ? "1" : "1½"} ทัพพี + ต้มยำปลา/กุ้ง (น้ำใส) + ผักลวกน้ำพริก + ไก่ย่าง (ไม่กินหนัง)<br><span class="hint">หรือ สุกี้น้ำ (น้ำจิ้มน้อย) · แกงส้มผักรวมกับปลา · ส้มตำไม่ใส่ปูปลาร้า + ไก่ย่าง + ข้าวเหนียว 1 ทัพพีเล็ก</span></td></tr>
    </tbody></table>
    <p class="hint">ดื่มน้ำเปล่าระหว่างวัน งดชาไข่มุก น้ำหวาน น้ำอัดลม ขนมกรุบกรอบ ของทอด ถ้าหิวระหว่างมื้อ เลือกผักสด ไข่ต้ม หรือนมจืด</p>`, false));

  // 7. อื่น ๆ
  const doctor = [];
  if (has(a.bmi) && a.bmi >= 30) doctor.push("BMI ≥ 30");
  if (has(d.vfl) && d.vfl >= 15) doctor.push("ไขมันในช่องท้องระดับ ≥ 15");
  if (has(d.edema) && d.edema > 0.40) doctor.push("ค่าบวมน้ำ (ECW/TBW) > 0.40");
  if (has(d.waist) && d.waist > waistLim + 10) doctor.push("รอบเอวเกินเกณฑ์มากกว่า 10 ซม.");
  parts.push(guideSection("💡 เรื่องอื่น ๆ ที่เกี่ยวข้อง", `
    ${iconRow([["😴", "นอน 7–9 ชม."], ["💧×8", "น้ำ 8–10 แก้ว"], ["🧘", "จัดการความเครียด"], ["🩺", "ตรวจสุขภาพประจำปี"], ["📊", "วัดซ้ำ 4–8 สัปดาห์"]])}
    <ul class="recs">
      <li><b>นอนหลับ 7–9 ชั่วโมง</b> – นอนน้อยทำให้ฮอร์โมนความหิวเพิ่ม อยากของหวาน และกล้ามเนื้อฟื้นตัวช้า</li>
      <li><b>ดื่มน้ำสะอาดวันละ 8–10 แก้ว</b>${has(d.weight) ? ` (ประมาณ ${fmt(d.weight * 0.033, 1)} ลิตรสำหรับน้ำหนักของคุณ)` : ""} – ค่าน้ำในร่างกายของ InBody จะแม่นขึ้นเมื่อร่างกายได้น้ำพอ</li>
      <li><b>จัดการความเครียด</b> – ความเครียดเรื้อรังทำให้กินมากขึ้นและสะสมไขมันหน้าท้อง</li>
      <li><b>ตรวจสุขภาพประจำปี</b> – ระดับน้ำตาล ไขมันในเลือด ความดันโลหิต โดยเฉพาะผู้ที่รอบเอวเกินหรือไขมันช่องท้องสูง</li>
      <li><b>วัด InBody ซ้ำทุก 4–8 สัปดาห์</b> เวลาเดิม ตอนเช้าก่อนอาหาร หลังเข้าห้องน้ำ ไม่ออกกำลังกายหรือดื่มน้ำมากก่อนวัด เพื่อเทียบผลได้ถูกต้อง</li>
      <li>ดูความเปลี่ยนแปลงของ <b>มวลไขมัน</b> และ <b>กล้ามเนื้อลาย</b> มากกว่าน้ำหนักอย่างเดียว น้ำหนักเท่าเดิมแต่ไขมันลด กล้ามเนื้อเพิ่ม ถือว่าดีขึ้น</li>
    </ul>
    ${doctor.length ? `<p class="mmsg bad"><b>ควรพบแพทย์</b> เนื่องจาก: ${doctor.join(", ")}</p>` : `<p class="hint">ควรพบแพทย์หากมีโรคประจำตัว ตั้งครรภ์ น้ำหนักลด/เพิ่มเร็วผิดปกติ หรือมีอาการบวม เหนื่อยง่าย</p>`}`, false));

  parts.push(`<div class="ggrid">${guideCards.join("")}</div>`);
  parts.push(`<details style="margin-top:14px"><summary>แหล่งอ้างอิง</summary><ul class="recs refs">${GUIDE_REFS.map(([t, u]) => `<li><a href="${u}" target="_blank" rel="noopener">${t}</a></li>`).join("")}</ul>
    <p class="hint">ปริมาณโปรตีนและแคลเซียมในอาหารเป็นค่าโดยประมาณจากตารางคุณค่าทางโภชนาการอาหารไทย ค่าจริงขึ้นกับยี่ห้อและวิธีปรุง คำแนะนำนี้ใช้สำหรับผู้ใหญ่สุขภาพทั่วไป ไม่ใช้แทนคำแนะนำจากแพทย์หรือนักกำหนดอาหาร</p></details>`);

  return `<section class="card"><h2>คู่มือสุขภาพสำหรับผลของคุณ</h2>
    <p class="hint">อ้างอิงคำแนะนำของกรมอนามัย กระทรวงสาธารณสุข ตัวเลขด้านล่างคำนวณจากผลวัดของคุณ กดที่ปุ่มเพื่อดูรายละเอียดและภาพประกอบ</p>
    ${parts.join("")}
    <div class="print-only">${Object.values(guideBodies).slice(-guideCards.length).map(g => `<h3>${g.icon} ${g.name}</h3>${g.body}`).join("")}</div></section>`;
}

// ---------- หน้าต่างรายละเอียด ----------
function openGuide(id){
  const g = guideBodies[id];
  const dlg = document.getElementById("guideDlg");
  if (!g || !dlg) return;
  dlg.style.setProperty("--gc", g.color);
  dlg.querySelector(".dlg-title").innerHTML = `<span class="gicon">${g.icon}</span>${g.name}`;
  dlg.querySelector(".dlg-body").innerHTML = g.body;
  dlg.querySelector(".dlg-body").scrollTop = 0;
  if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");
}

document.addEventListener("click", e => {
  const card = e.target.closest("[data-guide]");
  if (card) return openGuide(card.dataset.guide);
  const dlg = document.getElementById("guideDlg");
  if (dlg && (e.target.closest(".dlg-close") || e.target === dlg)) dlg.close ? dlg.close() : dlg.removeAttribute("open");
});
