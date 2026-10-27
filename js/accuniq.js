// ถอดรหัสข้อมูลจาก QR บนใบผล ACCUNIQ (BC380)
// รูปแบบ: https://QR.ACCUNIQ.COM/accuniq?bcadata=MgTH02<วันที่><เวลา><รหัส>*****<ข้อมูลความยาวคงที่>
// ตำแหน่งของแต่ละค่าได้จากการเทียบกับใบผลที่พิมพ์ออกมา ค่าที่ยังไม่ทราบความหมายจะข้ามไป
(function (root) {
  function extractData(text) {
    text = String(text || "").trim();
    const m = text.match(/bcadata=([^&\s]+)/i);
    let s = m ? m[1] : text;
    try { s = decodeURIComponent(s); } catch (e) {}
    return s;
  }

  function parseAccuniq(text) {
    const s = extractData(text);
    if (!/^Mg/.test(s)) throw new Error("ไม่ใช่ข้อมูล QR ของ ACCUNIQ");
    const star = s.lastIndexOf("*");
    if (star < 0) throw new Error("รูปแบบข้อมูลไม่ถูกต้อง");
    const head = s.slice(0, s.indexOf("*"));
    const body = s.slice(star + 1);
    if (body.length < 420) throw new Error("ข้อมูลใน QR ไม่ครบ");

    let p = 0;
    const take = n => { const v = body.slice(p, p + n); p += n; return v; };
    const num = (n, div = 10) => { const v = take(n); return /^[+-]?\d+$/.test(v) ? Number(v) / div : null; };
    const skip = n => { p += n; };

    const d = {};
    const date = head.slice(8, 14), time = head.slice(14, 18); // yymmdd, hhmm
    if (/^\d{6}$/.test(date)) d.date = `${date.slice(4, 6)}-${date.slice(2, 4)}-20${date.slice(0, 2)}`;
    if (/^\d{4}$/.test(time)) d.time = `${time.slice(0, 2)}:${time.slice(2)}`;

    d.sex = take(1) === "2" ? "female" : "male";
    d.age = num(3, 1);
    d.height = num(4);
    // น้ำหนัก: ค่า, สเกลต่ำ, ต่ำสุด, มาตรฐาน, สูงสุด, สเกลสูง
    d.weight = num(4); skip(4); d.weightMin = num(4); skip(4); d.weightMax = num(4); skip(4);
    d.targetWeight = num(4);
    d.ffm = num(4); d.ffmMin = num(4); d.ffmMax = num(4);
    d.slm = num(4); skip(4); d.slmMin = num(4); skip(4); d.slmMax = num(4); skip(4);
    d.tbw = num(4); skip(4); d.tbwMin = num(4); d.tbwMax = num(4);
    skip(4);
    d.protein = num(4); d.proteinMin = num(4); d.proteinMax = num(4);
    d.mineral = num(4); d.mineralMin = num(4); d.mineralMax = num(4);
    d.fat = num(4); skip(4); d.fatMin = num(4); skip(4); d.fatMax = num(4);
    skip(4);
    d.smm = num(4); skip(4); d.smmMin = num(4); d.smmMax = num(4); skip(4);
    d.bmi = num(4); skip(20);
    d.pbf = num(4); skip(20);
    d.whr = num(3, 100); skip(12);
    skip(16);
    d.vfl = num(2, 1); d.vfa = num(3, 1); skip(9); skip(3);
    d.vfm = num(4);
    skip(8);
    d.icw = num(4); d.ecw = num(4); d.edema = num(3, 1000);
    skip(17);
    d.bodyAge = num(3, 1); d.bmr = num(4, 1); d.tdee = num(4, 1); d.bcm = num(5);
    d.weightControl = num(5); d.muscleControl = num(5); d.fatControl = num(5);
    skip(10); skip(4);
    d.obesity = num(5); skip(9);
    d.waist = num(4);
    skip(4 + 45 + 4);
    d.score = num(3, 1);

    for (const k of Object.keys(d)) if (d[k] === null || Number.isNaN(d[k])) delete d[k];
    return d;
  }

  root.parseAccuniq = parseAccuniq;
  if (typeof module !== "undefined") module.exports = { parseAccuniq };
})(typeof window !== "undefined" ? window : globalThis);
