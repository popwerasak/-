// Build JCCPH-format research article (.docx)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
  AlignmentType, BorderStyle, VerticalAlign, TableLayoutType, HeightRule, LineRuleType,
} = require("docx");

const FONT = "TH SarabunPSK";
const FONTS = { ascii: FONT, hAnsi: FONT, cs: FONT, eastAsia: FONT };
const IND = 709; // 1.25 cm
const TEXT_W = 9026; // A4 width minus 2.54 cm margins (DXA)

// ---- inline markup: {b}..{/b} {i}..{/i} {sup}..{/sup} {hl}..{/hl}
function runs(text, base = {}) {
  const out = [];
  const st = { b: false, i: false, sup: false, hl: false, tnr: false };
  for (const part of text.split(/(\{\/?(?:b|i|sup|hl|tnr)\})/)) {
    const m = part.match(/^\{(\/?)(b|i|sup|hl|tnr)\}$/);
    if (m) { st[m[2]] = !m[1]; continue; }
    if (!part) continue;
    const size = base.size || 32;
    const bold = base.bold || st.b;
    const italics = base.italics || st.i;
    out.push(new TextRun({
      text: part, font: st.tnr ? { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "Times New Roman", eastAsia: "Times New Roman" } : FONTS, size: st.tnr ? size - 4 : size, sizeComplexScript: st.tnr ? size - 4 : size,
      bold, boldComplexScript: bold, italics, italicsComplexScript: italics,
      superScript: st.sup, highlight: st.hl ? "yellow" : undefined,
    }));
  }
  return out;
}

const SP = { before: 0, after: 0, line: 240, lineRule: LineRuleType.AUTO };
function para(text, o = {}) {
  return new Paragraph({
    alignment: o.align ?? AlignmentType.THAI_DISTRIBUTE,
    indent: o.indent ?? { firstLine: IND },
    spacing: SP, keepNext: o.keepNext, keepLines: o.keepLines,
    children: runs(text, { size: o.size, bold: o.bold, italics: o.italics }),
  });
}
const blank = (size = 32) => new Paragraph({ spacing: SP, children: [new TextRun({ text: "", font: FONTS, size, sizeComplexScript: size })] });
const heading = (t) => para(t, { bold: true, align: AlignmentType.LEFT, indent: { firstLine: 0 }, keepNext: true });
const center = (t, size, bold = true) => para(t, { size, bold, align: AlignmentType.CENTER, indent: { firstLine: 0 } });
// indented sub-heading followed by text on the same line
const sub = (h, t) => para(`{b}${h}{/b} ${t}`);
const item = (t) => para(t, { indent: { left: IND, hanging: 0 } });
const ref = (t) => para(t, { align: AlignmentType.LEFT, indent: { left: IND, hanging: IND } });

// ---- tables (APA-style: horizontal rules only)
const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const LINE = { style: BorderStyle.SINGLE, size: 8, color: "000000" };
function cell(text, w, o = {}) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    columnSpan: o.span, rowSpan: o.rowSpan,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 20, bottom: 20, left: 80, right: 80 },
    borders: { top: o.top ? LINE : NONE, bottom: o.bottom ? LINE : NONE, left: NONE, right: NONE },
    children: [new Paragraph({
      alignment: o.align ?? AlignmentType.CENTER, spacing: SP, keepNext: !o.lastRow,
      indent: o.indentLeft ? { left: o.indentLeft } : undefined,
      children: runs(text, { size: 28, bold: o.bold }),
    })],
  });
}
// rows: array of arrays of {t, span, rowSpan, align, bold, indentLeft}; hdrRows = number of header rows
function table(widths, rows, hdrRows) {
  const n = rows.length;
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    columnWidths: widths, layout: TableLayoutType.FIXED, alignment: AlignmentType.CENTER,
    rows: rows.map((r, ri) => {
      let col = 0;
      return new TableRow({
        tableHeader: ri < hdrRows, cantSplit: true,
        children: r.map((c) => {
          const span = c.span || 1;
          const w = widths.slice(col, col + span).reduce((a, b) => a + b, 0);
          col += span;
          const lastRowOfCell = ri + (c.rowSpan || 1) - 1;
          return cell(c.t, w, {
            ...c, lastRow: ri === n - 1,
            top: ri === 0,
            bottom: lastRowOfCell === n - 1 || lastRowOfCell === hdrRows - 1 || c.ruleBelow,
          });
        }),
      });
    }),
  });
}
const caption = (num, title) => para(`{b}ตารางที่ ${num}{/b} ${title}`, { align: AlignmentType.LEFT, indent: { left: 1080, hanging: 1080 }, keepNext: true });
const note = (t) => para(t, { size: 28, align: AlignmentType.LEFT, indent: { firstLine: 0 } });

const L = (t, o = {}) => ({ t, align: AlignmentType.LEFT, ...o });
const C = (t, o = {}) => ({ t, ...o });

// ---------------------------------------------------------------- content
const body = [];
const add = (...p) => body.push(...p);

// Title block
add(center("ผลของแบบแผนความเชื่อด้านสุขภาพและความรอบรู้ด้านสุขภาพ ภายใต้รูปแบบการยกระดับครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่ จังหวัดพิษณุโลก", 36));
add(center("Effects of the Health Belief Model and Health Literacy under a Family and Community Health Literacy Enhancement Model in the New Normal Lifestyle, Phitsanulok Province", 36));
add(blank(16));
add(center("วีรศักดิ์ พรหมมา{sup}1*{/sup}", 28));
add(center("{hl}Weerasak Promma{/hl}{sup}1*{/sup}", 28));
add(center("{sup}1{/sup}ศูนย์อนามัยที่ 2 พิษณุโลก กรมอนามัย กระทรวงสาธารณสุข", 24));
add(center("{sup}1{/sup}{hl}Regional Health Promotion Center 2 Phitsanulok, Department of Health, Ministry of Public Health{/hl}", 24));
add(blank(16));
add(center("(Received: ; Revised: ; Accepted: )", 24));
add(blank(16));

// Thai abstract
add(heading("บทคัดย่อ"));
add(para("ความรอบรู้ด้านสุขภาพของประชาชนในเขตสุขภาพที่ 2 ยังต่ำกว่าเกณฑ์และค่าเฉลี่ยประเทศ การวิจัยกึ่งทดลองแบบสองกลุ่มวัดก่อน-หลังนี้มีวัตถุประสงค์เพื่อศึกษาผลของแบบแผนความเชื่อด้านสุขภาพ (Health Belief Model) และความรอบรู้ด้านสุขภาพ (Health Literacy) ภายใต้รูปแบบการยกระดับครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่ จังหวัดพิษณุโลก และเปรียบเทียบคะแนนทั้งสองตัวแปรก่อนและหลังเข้าร่วมรูปแบบ กลุ่มตัวอย่างเป็นแกนนำครอบครัวในอำเภอเมืองพิษณุโลก จำนวน 80 คน ได้จากการสุ่มหลายขั้นตอน แบ่งเป็นกลุ่มทดลองและกลุ่มเปรียบเทียบ กลุ่มละ 40 คน กลุ่มทดลองได้รับรูปแบบเป็นเวลา 12 สัปดาห์ ส่วนกลุ่มเปรียบเทียบได้รับบริการสุขภาพตามปกติ เก็บข้อมูลด้วยแบบสอบถามแบบแผนความเชื่อด้านสุขภาพและความรอบรู้ด้านสุขภาพ วิเคราะห์ข้อมูลด้วยสถิติ Wilcoxon Signed Ranks Test และ Mann-Whitney U Test ผลการวิจัยพบว่า กลุ่มทดลองมีคะแนนแบบแผนความเชื่อด้านสุขภาพเพิ่มขึ้นอย่างมีนัยสำคัญทางสถิติหลังเข้าร่วมรูปแบบ (p = 0.029) ส่วนคะแนนความรอบรู้ด้านสุขภาพเพิ่มขึ้นแต่ไม่มีนัยสำคัญทางสถิติ (p = 0.323) และเมื่อเปรียบเทียบกับกลุ่มเปรียบเทียบหลังสิ้นสุดรูปแบบ กลุ่มทดลองมีคะแนนทั้งแบบแผนความเชื่อด้านสุขภาพ (p < 0.001) และความรอบรู้ด้านสุขภาพ (p = 0.023) สูงกว่าอย่างมีนัยสำคัญทางสถิติ แสดงว่ารูปแบบนี้ช่วยปรับเปลี่ยนความเชื่อและเสริมความรอบรู้ด้านสุขภาพของแกนนำครอบครัวได้ จึงควรขยายผลสู่พื้นที่อื่นในเขตสุขภาพที่ 2"));
add(blank(16));
add(para("{b}คำสำคัญ:{/b} ความเชื่อด้านสุขภาพ, ความรอบรู้ด้านสุขภาพ, การยกระดับครอบครัว, ชุมชนรอบรู้สุขภาพ, วิถีชีวิตปกติใหม่", { align: AlignmentType.LEFT, indent: { firstLine: 0 } }));
add(para("*ผู้ให้การติดต่อ (Corresponding e-mail: {hl}...........................{/hl})", { size: 24, align: AlignmentType.LEFT, indent: { firstLine: 0 } }));
add(blank());

// English abstract
add(heading("Abstract"));
add(para("Health literacy in Health Region 2 remains below the national standard and average. This two-group pretest-posttest quasi-experimental study aimed to examine the effects of the Health Belief Model (HBM) and Health Literacy under a Family and Community Health Literacy Enhancement Model in the New Normal Lifestyle, Phitsanulok Province, and to compare HBM and health literacy scores before and after participation in the model. The sample comprised 80 family health leaders in Mueang Phitsanulok District selected by multi-stage random sampling and divided equally into an experimental group and a comparison group (40 each). The experimental group received the model over a 12-week period, while the comparison group received usual health services. Data were collected using HBM and health literacy questionnaires and analyzed using the Wilcoxon Signed Ranks Test and the Mann-Whitney U Test. The results showed that, after participating in the model, the experimental group's HBM scores increased significantly (p = 0.029), while their health literacy scores increased but not significantly (p = 0.323). When compared with the comparison group after the intervention, the experimental group had significantly higher scores in both HBM (p < 0.001) and health literacy (p = 0.023). The model effectively shifted health beliefs and strengthened health literacy among family health leaders and should be scaled up to other areas within Health Region 2.", { align: AlignmentType.BOTH }));
add(blank(16));
add(para("{b}Keywords:{/b} Health Belief Model, Health Literacy, Family Enhancement, Health-Literate Community, New Normal Lifestyle", { align: AlignmentType.LEFT, indent: { firstLine: 0 } }));
add(blank());

// Introduction
add(heading("บทนำ"));
add(para("ความรอบรู้ด้านสุขภาพ (Health Literacy) เป็นทักษะสำคัญและจำเป็นในการสร้างพฤติกรรมสุขภาพ ส่งเสริมให้ประชาชนพัฒนาขีดความสามารถในระดับบุคคลเพื่อการดูแลสุขภาพของตนเองอย่างยั่งยืน กรมอนามัย กระทรวงสาธารณสุข ได้พัฒนากระบวนการส่งเสริมความรอบรู้ด้านสุขภาพ “วีเชฟ (V-shape)” 6 ขั้นตอน ได้แก่ การเข้าถึง การเข้าใจ การซักถามและแลกเปลี่ยน การตัดสินใจ การเปลี่ยนพฤติกรรม และการบอกต่อ (กรมอนามัย, 2560; วชิระ เพ็งจันทร์, 2560) ซึ่งมุ่งยกระดับจากการ “รู้แต่ไม่ทำ” ไปสู่การมีทักษะแสวงหา แยกแยะข้อมูลจริงและข้อมูลลวง และใช้ข้อมูลสุขภาพที่ถูกต้องสอดคล้องกับวิถีชีวิตของตนเองไปประกอบการตัดสินใจจนเกิดการเปลี่ยนแปลงพฤติกรรมอย่างเป็นรูปธรรม และสามารถบอกเล่าความสำเร็จให้ผู้อื่นได้ (สำนักส่งเสริมสุขภาพ, 2565)"));
add(para("แม้ประเทศไทยจะมีความก้าวหน้าในการขับเคลื่อนงานดังกล่าว แต่ผลการสำรวจความรอบรู้ด้านสุขภาพของประชาชนไทย อายุ 15 ปีขึ้นไป พ.ศ. 2566 (ครั้งที่ 2) พบว่า ประชาชนไทยโดยรวมมีความรอบรู้ด้านสุขภาพในระดับเพียงพอ ร้อยละ 80.9 แต่ในเขตสุขภาพที่ 2 มีเพียงร้อยละ 65.7 ซึ่งต่ำกว่าเกณฑ์มาตรฐานร้อยละ 66 และต่ำกว่าค่าเฉลี่ยประเทศ นอกจากนี้ทักษะ “การใช้ข้อมูลเพื่อตัดสินใจ” เป็นทักษะที่คนไทยมีคะแนนเฉลี่ยต่ำที่สุด และเขตสุขภาพที่ 2 มีคะแนนเฉลี่ยต่ำที่สุดในทักษะ “การเข้าถึงข้อมูลที่น่าเชื่อถือ” และ “การซักถามข้อสงสัย” เมื่อเทียบกับทุกเขตสุขภาพ (สถาบันวิจัยระบบสาธารณสุข, 2567) สะท้อนว่าประชาชนในพื้นที่ยังขาดทักษะในการประเมินความถูกต้องของข้อมูลสุขภาพที่เผยแพร่ผ่านสื่อออนไลน์ โดยเฉพาะภายหลังสถานการณ์โรคโควิด-19 ที่การดำรงชีวิตแบบ “วิถีชีวิตปกติใหม่ (New Normal)” ทำให้การใช้เทคโนโลยีดิจิทัลเพื่อเข้าถึงข้อมูลสุขภาพกลายเป็นสิ่งจำเป็น"));
add(para("สถานการณ์ดังกล่าวสะท้อนความจำเป็นในการพัฒนารูปแบบการเสริมสร้างความรอบรู้ด้านสุขภาพที่ตอบโจทย์บริบทของพื้นที่ ซึ่งต้องคำนึงถึงทั้ง “ความเชื่อด้านสุขภาพของบุคคล” และ “ทักษะการจัดการข้อมูลสุขภาพ” โดยทฤษฎีแบบแผนความเชื่อด้านสุขภาพ (Health Belief Model: HBM) อธิบายว่าพฤติกรรมสุขภาพเกิดจากการรับรู้โอกาสเสี่ยง (Perceived Susceptibility) การรับรู้ความรุนแรงของโรค (Perceived Severity) การรับรู้ประโยชน์ของการปฏิบัติ (Perceived Benefits) และการรับรู้อุปสรรค (Perceived Barriers) (Rosenstock, 1974; Becker, 1974) ผู้วิจัยจึงศึกษาผลของรูปแบบการยกระดับครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่ ที่บูรณาการแนวคิดดังกล่าวเข้ากับกรอบ V-shape เพื่อให้แกนนำครอบครัวมีทักษะในการเข้าถึง เข้าใจ ซักถาม ตัดสินใจ และปรับเปลี่ยนพฤติกรรมสุขภาพอย่างเหมาะสม และเป็นต้นแบบในการขยายผลไปยังชุมชนอื่นในเขตสุขภาพที่ 2 ต่อไป"));
add(blank());

add(heading("วัตถุประสงค์การวิจัย"));
add(para("1) เพื่อศึกษาผลของแบบแผนความเชื่อด้านสุขภาพและความรอบรู้ด้านสุขภาพ ภายใต้รูปแบบการยกระดับครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่ จังหวัดพิษณุโลก"));
add(para("2) เพื่อเปรียบเทียบคะแนนแบบแผนความเชื่อด้านสุขภาพและความรอบรู้ด้านสุขภาพของแกนนำครอบครัว ก่อนและหลังเข้าร่วมรูปแบบการยกระดับครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่ จังหวัดพิษณุโลก"));
add(blank());

add(heading("สมมติฐานการวิจัย"));
add(para("1) แกนนำครอบครัวที่เข้าร่วมรูปแบบการยกระดับครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่ มีคะแนนแบบแผนความเชื่อด้านสุขภาพและคะแนนความรอบรู้ด้านสุขภาพหลังเข้าร่วมรูปแบบสูงกว่าก่อนเข้าร่วมรูปแบบอย่างมีนัยสำคัญทางสถิติ"));
add(para("2) แกนนำครอบครัวที่เข้าร่วมรูปแบบการยกระดับครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่ มีคะแนนแบบแผนความเชื่อด้านสุขภาพและคะแนนความรอบรู้ด้านสุขภาพสูงกว่ากลุ่มที่ไม่ได้เข้าร่วมรูปแบบอย่างมีนัยสำคัญทางสถิติ"));
add(blank());

// Conceptual framework (built as a table so it never shifts between computers)
add(heading("กรอบแนวคิดการวิจัย"));
add(para("การวิจัยครั้งนี้บูรณาการทฤษฎีแบบแผนความเชื่อด้านสุขภาพ (Rosenstock, 1974; Becker, 1974) เข้ากับกรอบ V-shape ของกรมอนามัย (สำนักส่งเสริมสุขภาพ, 2565) โดยมีรูปแบบการยกระดับครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่ เป็นตัวแปรต้น และแบบแผนความเชื่อด้านสุขภาพและความรอบรู้ด้านสุขภาพเป็นตัวแปรตาม ดังภาพที่ 1"));
add(blank(16));
{
  const BOX = { style: BorderStyle.SINGLE, size: 8, color: "000000" };
  const fp = (t, o = {}) => new Paragraph({ spacing: SP, alignment: o.align ?? AlignmentType.LEFT, indent: o.ind ? { left: o.ind } : undefined, children: runs(t, { size: 28, bold: o.bold }) });
  const box = (w, paras) => new TableCell({ width: { size: w, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER, margins: { top: 80, bottom: 80, left: 120, right: 120 }, borders: { top: BOX, bottom: BOX, left: BOX, right: BOX }, children: paras });
  const gap = (w, paras) => new TableCell({ width: { size: w, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER, borders: { top: NONE, bottom: NONE, left: NONE, right: NONE }, children: paras });
  const W = [5226, 600, 3200];
  add(new Table({
    width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: W, layout: TableLayoutType.FIXED,
    rows: [
      new TableRow({ cantSplit: true, children: [
        gap(W[0], [fp("ตัวแปรต้น", { bold: true, align: AlignmentType.CENTER })]),
        gap(W[1], [fp("")]),
        gap(W[2], [fp("ตัวแปรตาม", { bold: true, align: AlignmentType.CENTER })]),
      ] }),
      new TableRow({ cantSplit: true, children: [
        box(W[0], [
          fp("รูปแบบการยกระดับครอบครัว ชุมชนรอบรู้สุขภาพ ภายใต้วิถีชีวิตปกติใหม่", { bold: true, align: AlignmentType.CENTER }),
          fp("1) ด้านเนื้อหา", { bold: true }),
          fp("ชุดความรู้การยกระดับครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่", { ind: 284 }),
          fp("2) ด้านกิจกรรม (12 สัปดาห์)", { bold: true }),
          fp("2.1 กิจกรรมแบบแผนความเชื่อด้านสุขภาพ: การรับรู้โอกาสเสี่ยงและความรุนแรง การรับรู้ประโยชน์และอุปสรรค", { ind: 284 }),
          fp("2.2 กิจกรรมสร้างความรอบรู้ด้านสุขภาพตามกรอบ V-shape: การเข้าถึง เข้าใจ ซักถาม ตัดสินใจ ปรับพฤติกรรม และบอกต่อ", { ind: 284 }),
          fp("2.3 แผนส่งเสริมสุขภาพดีรายครัวเรือน และแพลตฟอร์มดิจิทัล (Thai Save Family, ก้าวท้าใจ)", { ind: 284 }),
        ]),
        gap(W[1], [fp("{tnr}→{/tnr}", { align: AlignmentType.CENTER, bold: true })]),
        box(W[2], [
          fp("1) แบบแผนความเชื่อด้านสุขภาพ", { bold: true }),
          fp("การรับรู้โอกาสเสี่ยง ความรุนแรงของโรค ประโยชน์ และอุปสรรค", { ind: 284 }),
          fp("2) ความรอบรู้ด้านสุขภาพ", { bold: true }),
          fp("ความรู้ความเข้าใจ การเข้าถึงข้อมูล การสื่อสาร การจัดการตนเอง การตัดสินใจเลือกปฏิบัติ และการบอกต่อ", { ind: 284 }),
        ]),
      ] }),
    ],
  }));
}
add(blank(16));
add(center("{b}ภาพที่ 1{/b} กรอบแนวคิดการวิจัย", 32, false));
add(blank());

// Methods
add(heading("ระเบียบวิธีวิจัย"));
add(para("การวิจัยครั้งนี้เป็นการวิจัยกึ่งทดลอง (Quasi-Experimental Research) แบบสองกลุ่มวัดก่อนและหลังการทดลอง (Two Groups Pretest-Posttest Design) ดำเนินการระหว่างเดือนกุมภาพันธ์ ถึงเดือนมิถุนายน พ.ศ. 2566"));
add(sub("ประชากรและกลุ่มตัวอย่าง", "ประชากร คือ แกนนำซึ่งเป็นอาสาสมัครจากครอบครัวที่อาศัยอยู่ในชุมชนตลอดระยะเวลาที่ดำเนินการวิจัยในจังหวัดพิษณุโลก ขนาดกลุ่มตัวอย่างคำนวณด้วยโปรแกรม G*Power 3 (Faul et al., 2007, 2009; นงลักษณ์ วิรัชชัย, 2555) กำหนดขนาดอิทธิพลเท่ากับ 0.80 ระดับนัยสำคัญ ({tnr}α{/tnr}) เท่ากับ 0.05 อำนาจการทดสอบเท่ากับ 0.95 และอัตราส่วนขนาดตัวอย่างสองกลุ่มเท่ากับ 1 ได้กลุ่มตัวอย่างกลุ่มละ 35 คน และเพิ่มเพื่อชดเชยการสูญหายร้อยละ 15 เป็นกลุ่มละ 40 คน รวม 80 คน"));
add(para("การเลือกกลุ่มตัวอย่างใช้การสุ่มหลายขั้นตอน (Multi-stage Random Sampling) ร่วมกับการสุ่มแบบกลุ่ม (Cluster Sampling) ระดับตำบล ดังนี้ ขั้นที่ 1 สุ่มจังหวัดภาคละ 2 จังหวัดด้วยการจับฉลาก (Simple Random Sampling) ภาคเหนือได้จังหวัดเชียงรายและจังหวัดพิษณุโลก โดยจังหวัดพิษณุโลกเป็นพื้นที่ศึกษาของงานวิจัยนี้ ขั้นที่ 2 สุ่มอำเภอด้วยการจับฉลากแบบไม่ใส่คืน ได้อำเภอเมืองพิษณุโลก ขั้นที่ 3 สุ่มตำบลในอำเภอเมือง 2 ตำบล แล้วสุ่มจัดสรร (Random Allocation) ด้วยโปรแกรมสุ่มตัวเลขเป็นกลุ่มทดลองและกลุ่มเปรียบเทียบ และขั้นที่ 4 จัดทำบัญชีรายชื่อแกนนำครอบครัวที่มีคุณสมบัติครบร่วมกับ รพ.สต. อปท. และ อสม. ในแต่ละตำบล แล้วคัดเลือกผู้ที่ยินดีเข้าร่วมโครงการ ตำบลละ 40 คน"));
add(para("เกณฑ์การคัดเข้า ได้แก่ 1) อายุ 18 ปีขึ้นไป 2) เป็นแกนนำครอบครัว/ชุมชน หรือผู้ดูแลกลุ่มเปราะบางในครอบครัว และอาศัยในพื้นที่ไม่น้อยกว่า 6 เดือน 3) อ่านและเขียนหนังสือได้ 4) มีโทรศัพท์มือถือที่สามารถดาวน์โหลดแอปพลิเคชัน Thai Save Family และก้าวท้าใจ ได้ 5) สามารถเข้าร่วมกิจกรรมได้ตลอดโปรแกรม และ 6) สมัครใจเข้าร่วมโครงการ เกณฑ์การคัดออก คือ ขาดคุณสมบัติข้อใดข้อหนึ่งตามเกณฑ์การคัดเข้า และเกณฑ์การให้เลิกจากการศึกษา คือ อาสาสมัครปฏิเสธการเข้าร่วมกิจกรรม ผู้วิจัยควบคุมความเอนเอียงโดยเก็บข้อมูลทั้งสองกลุ่มในช่วงเวลาใกล้เคียงกันด้วยแบบสอบถามและผู้เก็บข้อมูลที่ผ่านการฝึกมาตรฐานเดียวกัน"));
add(sub("เครื่องมือที่ใช้ในการวิจัย", "ประกอบด้วย 2 ส่วน ดังนี้"));
add(para("1) เครื่องมือที่ใช้ในการทดลอง คือ รูปแบบการยกระดับครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่ ซึ่งใช้ชุดความรู้ของสำนักส่งเสริมสุขภาพ กรมอนามัย (สำนักส่งเสริมสุขภาพ, 2565) เนื้อหาประกอบด้วย การพัฒนาสุขภาพและการสร้างพลังชุมชน การวางแผนพัฒนาสุขภาพตนเองและครอบครัว การส่งเสริมสุขภาพตามหลัก 3อ 2ส การป้องกันโรคโควิด-19 แผนส่งเสริมสุขภาพดีรายครัวเรือน (Wellness Family Plan) และ Health Literacy Family Platform"));
add(para("2) เครื่องมือที่ใช้ในการเก็บรวบรวมข้อมูล คือ แบบสอบถาม 2 ส่วน ได้แก่ ส่วนที่ 1 แบบแผนความเชื่อด้านสุขภาพ 4 ด้าน คือ การรับรู้โอกาสเสี่ยง การรับรู้ความรุนแรงของโรค การรับรู้ประโยชน์ของการรักษาป้องกันโรค และการรับรู้อุปสรรค (ด้านละ 3 คะแนน) แปลผลคะแนนเฉลี่ยเป็น 3 ระดับ ได้แก่ น้อย (0.00–1.00) ปานกลาง (1.01–2.00) และมาก (2.01–3.00) และส่วนที่ 2 ความรอบรู้ด้านสุขภาพตามชุดความรู้ 6 ด้าน คือ ความรู้ความเข้าใจ (1 คะแนน) การเข้าถึงข้อมูลสุขภาพ (3 คะแนน) การสื่อสารสุขภาพ (3 คะแนน) การจัดการตนเอง (3 คะแนน) การตัดสินใจและเลือกปฏิบัติที่ถูกต้อง (1 คะแนน) และการบอกต่อในครอบครัว ชุมชน (1 คะแนน) โดยแปลงคะแนนเฉลี่ยแต่ละด้านเป็นสัดส่วน (คะแนนเฉลี่ย/คะแนนเต็ม) และแปลผลเป็น 3 ระดับ ได้แก่ น้อย (0.00–0.49) ปานกลาง (0.50–0.74) และมาก (0.75–1.00)"));
add(sub("การตรวจสอบคุณภาพเครื่องมือ", "แบบสอบถามเป็นเครื่องมือมาตรฐานของโครงการวิจัยรูปแบบการพัฒนาครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่ สำนักส่งเสริมสุขภาพ กรมอนามัย {hl}[โปรดระบุผลการตรวจสอบความตรงเชิงเนื้อหา (IOC) โดยผู้เชี่ยวชาญ และค่าความเชื่อมั่น (Cronbach’s alpha) ของแบบสอบถามแต่ละส่วน]{/hl}"));
add(sub("การเก็บรวบรวมข้อมูล", "ผู้วิจัยดำเนินการเป็น 2 ขั้นตอน ดังนี้"));
add(para("1) ขั้นเตรียมการ ผู้วิจัยทำหนังสือจากศูนย์อนามัยที่ 2 พิษณุโลก ถึงผู้อำนวยการ รพ.สต. ทั้ง 2 แห่ง เพื่อขอความร่วมมือและชี้แจงวัตถุประสงค์ คัดเลือกและชี้แจงผู้ช่วยวิจัยแห่งละ 1 คน และให้กลุ่มตัวอย่างลงนามยินยอมเข้าร่วมการวิจัย"));
add(para("2) ขั้นดำเนินการทดลอง กลุ่มทดลองเข้าร่วมรูปแบบ 12 สัปดาห์ แบ่งเป็น 3 ช่วง ช่วงที่ 1 (สัปดาห์ที่ 1–4) การเตรียมความพร้อมและการติดตามตนเอง อบรม 6 ชั่วโมง ทดสอบก่อนการทดลอง และฝึกใช้แผนส่งเสริมสุขภาพดีรายครัวเรือนเพื่อตั้งเป้าหมายและวางแผนปรับพฤติกรรม แล้วติดตามผ่านกลุ่มย่อยสัปดาห์ละ 1 ชั่วโมง ช่วงที่ 2 (สัปดาห์ที่ 5–8) การเสริมสร้างความเชื่อและทักษะความรอบรู้ด้านสุขภาพ ได้แก่ กิจกรรม “ตระหนักรู้ความเสี่ยงและผลกระทบของโรค” ด้วยกรณีศึกษา (สัปดาห์ที่ 5) การระดมสมองวิเคราะห์ประโยชน์และอุปสรรคของการปฏิบัติ (สัปดาห์ที่ 6–7) และกิจกรรม “เข้าถึงและเข้าใจข้อมูลสุขภาพ” ฝึกใช้แพลตฟอร์ม Thai Save Family และก้าวท้าใจ (สัปดาห์ที่ 8) และช่วงที่ 3 (สัปดาห์ที่ 9–12) การประยุกต์ใช้ การถ่ายทอด และการประเมินผล ได้แก่ กิจกรรมวิเคราะห์ “ข่าวจริง–ข่าวลวง” และการใช้ข้อมูลเพื่อการตัดสินใจ (สัปดาห์ที่ 9–10) เวทีแลกเปลี่ยนเรียนรู้ (KM) เพื่อสร้างแรงเสริมและกระตุ้นการบอกต่อในชุมชน (สัปดาห์ที่ 11) และทดสอบหลังการทดลอง (สัปดาห์ที่ 12)"));
add(para("สำหรับกลุ่มเปรียบเทียบได้รับบริการสุขภาพตามปกติของ รพ.สต. และการบรรยายสุขภาพทั่วไป 1 ครั้ง (60 นาที) ตามสื่อมาตรฐานของกรมอนามัย โดยไม่ใช้กรอบ V-shape ไม่มีกิจกรรมฝึกทักษะ การตั้งเป้าหมาย หรือแผนรายครัวเรือน มีการติดตามสั้น ๆ รายสัปดาห์ (ไม่เกิน 5 นาที) และทำแบบสอบถามหลังการทดลองด้วยเครื่องมือเดียวกับกลุ่มทดลอง"));
add(sub("การวิเคราะห์ข้อมูล", "วิเคราะห์ด้วยโปรแกรมสำเร็จรูปทางสถิติ โดยใช้สถิติเชิงพรรณนา ได้แก่ ค่าเฉลี่ย ({i}M{/i}) และส่วนเบี่ยงเบนมาตรฐาน ({i}SD.{/i}) และตรวจสอบการแจกแจงของข้อมูลด้วยสถิติ Kolmogorov-Smirnov และ Shapiro-Wilk Test พบว่าข้อมูลมีการแจกแจงไม่ปกติ จึงใช้สถิติ Wilcoxon Signed Ranks Test เปรียบเทียบภายในกลุ่มก่อนและหลังการทดลอง และ Mann-Whitney U Test เปรียบเทียบระหว่างกลุ่มทดลองและกลุ่มเปรียบเทียบ กำหนดระดับนัยสำคัญทางสถิติที่ 0.05"));
add(blank());

add(heading("จริยธรรมการวิจัย"));
add(para("การวิจัยครั้งนี้ได้รับการรับรองจากคณะกรรมการจริยธรรมการวิจัยในมนุษย์ กรมอนามัย รหัสโครงการวิจัย 598/2565 ใบรับรองเลขที่ RF09-04-598 เมื่อวันที่ 23 มกราคม 2566 (รับรองถึงวันที่ 22 มกราคม 2567) ผู้วิจัยชี้แจงวัตถุประสงค์ ขั้นตอน และประโยชน์ของการวิจัย กลุ่มตัวอย่างลงนามยินยอมเป็นลายลักษณ์อักษรและสามารถถอนตัวได้ตลอดเวลา การบันทึกข้อมูลไม่ระบุชื่อ-นามสกุล นำเสนอผลในภาพรวม และกลุ่มเปรียบเทียบได้รับโปรแกรมเต็มรูปแบบภายหลังสิ้นสุดการเก็บข้อมูลเพื่อความเป็นธรรมทางจริยธรรม"));
add(blank());

// Results
add(heading("ผลการวิจัย"));
add(para("{b}1. แบบแผนความเชื่อด้านสุขภาพ{/b} ก่อนการทดลอง กลุ่มทดลองและกลุ่มเปรียบเทียบมีแบบแผนความเชื่อด้านสุขภาพภาพรวมอยู่ในระดับมาก ({i}M{/i} = 2.85, {i}SD.{/i} = 0.17 และ {i}M{/i} = 2.77, {i}SD.{/i} = 0.27 ตามลำดับ) หลังการทดลอง กลุ่มทดลองมีคะแนนเพิ่มขึ้นเป็น {i}M{/i} = 2.90 ({i}SD.{/i} = 0.18) โดยด้านการรับรู้โอกาสเสี่ยงสูงสุด ({i}M{/i} = 2.94) ส่วนกลุ่มเปรียบเทียบมีคะแนน {i}M{/i} = 2.76 ({i}SD.{/i} = 0.19) ดังตารางที่ 1"));
add(blank());
{
  const W = [2706, 790, 790, 790, 790, 790, 790, 790, 790];
  const H = (t) => C(t, { bold: true });
  const row = (lab, v, o = {}) => [L(lab, { indentLeft: o.ind, bold: o.bold }), ...v.map((x) => C(x, { bold: o.bold }))];
  add(caption(1, "ค่าเฉลี่ยและส่วนเบี่ยงเบนมาตรฐานของคะแนนแบบแผนความเชื่อด้านสุขภาพ ก่อนและหลังการทดลอง จำแนกตามกลุ่ม"));
  add(table(W, [
    [L("รายด้าน", { bold: true, rowSpan: 3 }), { t: "กลุ่มทดลอง (n = 40)", span: 4, bold: true, ruleBelow: true }, { t: "กลุ่มเปรียบเทียบ (n = 40)", span: 4, bold: true, ruleBelow: true }],
    [{ t: "ก่อน", span: 2, bold: true }, { t: "หลัง", span: 2, bold: true }, { t: "ก่อน", span: 2, bold: true }, { t: "หลัง", span: 2, bold: true }],
    ["{i}M{/i}", "{i}SD.{/i}", "{i}M{/i}", "{i}SD.{/i}", "{i}M{/i}", "{i}SD.{/i}", "{i}M{/i}", "{i}SD.{/i}"].map(H),
    row("1. การรับรู้โอกาสเสี่ยง", ["2.85", "0.25", "2.94", "0.16", "2.84", "0.27", "2.84", "0.21"]),
    row("2. การรับรู้ความรุนแรงของโรค", ["2.81", "0.26", "2.85", "0.33", "2.69", "0.32", "2.55", "0.35"]),
    row("3. การรับรู้ประโยชน์ของการรักษาป้องกันโรค", ["2.86", "0.24", "2.92", "0.21", "2.85", "0.28", "2.92", "0.22"]),
    row("4. การรับรู้อุปสรรค", ["2.90", "0.23", "2.91", "0.19", "2.71", "0.53", "2.73", "0.34"]),
    row("ภาพรวม", ["2.85", "0.17", "2.90", "0.18", "2.77", "0.27", "2.76", "0.19"], { bold: true }),
  ], 3));
  add(note("หมายเหตุ: ทุกด้านอยู่ในระดับมาก (2.01–3.00)"));
}
add(blank());
add(para("{b}2. ความรอบรู้ด้านสุขภาพ{/b} ก่อนการทดลอง กลุ่มทดลองและกลุ่มเปรียบเทียบมีความรอบรู้ด้านสุขภาพภาพรวมอยู่ในระดับมาก ({i}M{/i} = 0.93, {i}SD.{/i} = 0.07 และ {i}M{/i} = 0.92, {i}SD.{/i} = 0.08 ตามลำดับ) โดยทั้งสองกลุ่มมีด้านการตัดสินใจและเลือกปฏิบัติที่ถูกต้องสูงสุด ({i}M{/i} = 0.99 และ 0.96) หลังการทดลอง กลุ่มทดลองมีคะแนนภาพรวมเพิ่มขึ้นเป็น {i}M{/i} = 0.95 ({i}SD.{/i} = 0.05) โดยด้านการบอกต่อในครอบครัว ชุมชน มีค่าเฉลี่ยสูงสุด ({i}M{/i} = 0.99, {i}SD.{/i} = 0.04) ส่วนกลุ่มเปรียบเทียบมีคะแนนภาพรวมเท่าเดิม ({i}M{/i} = 0.92, {i}SD.{/i} = 0.06) ดังตารางที่ 2"));
add(blank());
{
  const W = [2706, 790, 790, 790, 790, 790, 790, 790, 790];
  const H = (t) => C(t, { bold: true });
  const row = (lab, v, o = {}) => [L(lab, { bold: o.bold }), ...v.map((x) => C(x, { bold: o.bold }))];
  add(caption(2, "ค่าเฉลี่ยและส่วนเบี่ยงเบนมาตรฐานของคะแนนความรอบรู้ด้านสุขภาพตามชุดความรู้การยกระดับครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่ ก่อนและหลังการทดลอง จำแนกตามกลุ่ม"));
  add(table(W, [
    [L("รายด้าน", { bold: true, rowSpan: 3 }), { t: "กลุ่มทดลอง (n = 40)", span: 4, bold: true, ruleBelow: true }, { t: "กลุ่มเปรียบเทียบ (n = 40)", span: 4, bold: true, ruleBelow: true }],
    [{ t: "ก่อน", span: 2, bold: true }, { t: "หลัง", span: 2, bold: true }, { t: "ก่อน", span: 2, bold: true }, { t: "หลัง", span: 2, bold: true }],
    ["{i}M{/i}", "{i}SD.{/i}", "{i}M{/i}", "{i}SD.{/i}", "{i}M{/i}", "{i}SD.{/i}", "{i}M{/i}", "{i}SD.{/i}"].map(H),
    row("1. ความรู้ความเข้าใจ", ["0.91", "0.10", "0.92", "0.10", "0.88", "0.15", "0.88", "0.11"]),
    row("2. การเข้าถึงข้อมูลสุขภาพ", ["0.93", "0.10", "0.94", "0.09", "0.92", "0.10", "0.90", "0.09"]),
    row("3. การสื่อสารสุขภาพ", ["0.89", "0.13", "0.91", "0.11", "0.89", "0.14", "0.90", "0.10"]),
    row("4. การจัดการตนเอง", ["0.89", "0.11", "0.94", "0.08", "0.91", "0.13", "0.87", "0.08"]),
    row("5. การตัดสินใจและเลือกปฏิบัติที่ถูกต้อง", ["0.99", "0.07", "0.98", "0.06", "0.96", "0.09", "0.99", "0.05"]),
    row("6. การบอกต่อในครอบครัว ชุมชน", ["0.96", "0.11", "0.99", "0.04", "0.94", "0.10", "0.97", "0.11"]),
    row("ภาพรวม", ["0.93", "0.07", "0.95", "0.05", "0.92", "0.08", "0.92", "0.06"], { bold: true }),
  ], 3));
  add(note("หมายเหตุ: คะแนนเป็นสัดส่วนของคะแนนเฉลี่ยต่อคะแนนเต็ม ทุกด้านอยู่ในระดับมาก (0.75–1.00)"));
}
add(blank());
add(para("{b}3. การเปรียบเทียบภายในกลุ่มก่อนและหลังการทดลอง{/b} กลุ่มทดลองมีคะแนนแบบแผนความเชื่อด้านสุขภาพหลังการทดลองแตกต่างจากก่อนการทดลองอย่างมีนัยสำคัญทางสถิติ (Z = -2.19, p = 0.029) ส่วนคะแนนความรอบรู้ด้านสุขภาพไม่แตกต่างกันอย่างมีนัยสำคัญทางสถิติ (Z = -0.99, p = 0.323) สำหรับกลุ่มเปรียบเทียบ คะแนนทั้งสองตัวแปรก่อนและหลังการทดลองไม่แตกต่างกันอย่างมีนัยสำคัญทางสถิติ (p = 0.640 และ p = 0.672 ตามลำดับ) ดังตารางที่ 3"));
add(blank());
{
  const W = [3026, 1000, 1000, 1000, 1000, 1000, 1000];
  const H = (t, o = {}) => C(t, { bold: true, ...o });
  const row = (lab, v) => [L(lab, { indentLeft: 227 }), ...v.map((x) => C(x))];
  add(caption(3, "การเปรียบเทียบคะแนนแบบแผนความเชื่อด้านสุขภาพและความรอบรู้ด้านสุขภาพ ก่อนและหลังการทดลอง ภายในกลุ่มทดลองและกลุ่มเปรียบเทียบ (Wilcoxon Signed Ranks Test)"));
  add(table(W, [
    [L("ตัวแปร", { bold: true, rowSpan: 2 }), H("ก่อนการทดลอง", { span: 2, ruleBelow: true }), H("หลังการทดลอง", { span: 2, ruleBelow: true }), H("Z", { rowSpan: 2 }), H("p-value", { rowSpan: 2 })],
    [H("Mean Rank"), H("Sum of Ranks"), H("Mean Rank"), H("Sum of Ranks")],
    [L("กลุ่มทดลอง (n = 40)", { bold: true, span: 7 })],
    row("แบบแผนความเชื่อด้านสุขภาพ", ["15.93", "318.50", "12.94", "116.50", "-2.19", "0.029*"]),
    row("ความรอบรู้ด้านสุขภาพ", ["21.98", "483.50", "18.69", "336.50", "-0.99", "0.323"]),
    [L("กลุ่มเปรียบเทียบ (n = 40)", { bold: true, span: 7 })],
    row("แบบแผนความเชื่อด้านสุขภาพ", ["18.76", "356.50", "21.18", "423.50", "-0.47", "0.640"]),
    row("ความรอบรู้ด้านสุขภาพ", ["25.23", "378.50", "17.66", "441.50", "-0.42", "0.672"]),
  ], 2));
  add(note("* p-value < 0.05"));
}
add(blank());
add(para("{b}4. การเปรียบเทียบระหว่างกลุ่มทดลองและกลุ่มเปรียบเทียบ{/b} ก่อนการทดลอง คะแนนแบบแผนความเชื่อด้านสุขภาพ (Z = -1.45, p = 0.146) และความรอบรู้ด้านสุขภาพ (Z = -0.88, p = 0.378) ของทั้งสองกลุ่มไม่แตกต่างกันอย่างมีนัยสำคัญทางสถิติ หลังการทดลอง กลุ่มทดลองมีคะแนนแบบแผนความเชื่อด้านสุขภาพ (Z = -4.54, p < 0.001) และความรอบรู้ด้านสุขภาพ (Z = -2.28, p = 0.023) สูงกว่ากลุ่มเปรียบเทียบอย่างมีนัยสำคัญทางสถิติ ดังตารางที่ 4"));
add(blank());
{
  const W = [3026, 1200, 1200, 1300, 1150, 1150];
  const H = (t, o = {}) => C(t, { bold: true, ...o });
  const pair = (varName, e, c, u, z, p) => [
    [L(varName, { indentLeft: 227, span: 6 })],
    [L("กลุ่มทดลอง", { indentLeft: 454 }), C(e[0]), C(e[1]), C(u, { rowSpan: 2 }), C(z, { rowSpan: 2 }), C(p, { rowSpan: 2 })],
    [L("กลุ่มเปรียบเทียบ", { indentLeft: 454 }), C(c[0]), C(c[1])],
  ];
  add(caption(4, "การเปรียบเทียบคะแนนแบบแผนความเชื่อด้านสุขภาพและความรอบรู้ด้านสุขภาพ ระหว่างกลุ่มทดลองและกลุ่มเปรียบเทียบ ก่อนและหลังการทดลอง (Mann-Whitney U Test)"));
  add(table(W, [
    [H("ตัวแปร", { align: AlignmentType.LEFT }), H("Mean Rank"), H("Sum of Ranks"), H("Mann-Whitney U"), H("Z"), H("p-value")],
    [L("ก่อนการทดลอง", { bold: true, span: 6 })],
    ...pair("แบบแผนความเชื่อด้านสุขภาพ", ["44.20", "1768.00"], ["36.80", "1472.00"], "652.00", "-1.45", "0.146"),
    ...pair("ความรอบรู้ด้านสุขภาพ", ["42.79", "1711.50"], ["38.21", "1528.50"], "708.50", "-0.88", "0.378"),
    [L("หลังการทดลอง", { bold: true, span: 6 })],
    ...pair("แบบแผนความเชื่อด้านสุขภาพ", ["52.09", "2083.50"], ["28.91", "1156.50"], "336.50", "-4.54", "< 0.001***"),
    ...pair("ความรอบรู้ด้านสุขภาพ", ["46.40", "1856.00"], ["34.60", "1384.00"], "564.00", "-2.28", "0.023*"),
  ], 1));
  add(note("* p-value < 0.05, *** p-value < 0.001"));
}
add(blank());

// Discussion
add(heading("อภิปรายผล"));
add(para("ผลการวิจัยพบว่า กลุ่มทดลองมีคะแนนแบบแผนความเชื่อด้านสุขภาพหลังเข้าร่วมรูปแบบสูงกว่าก่อนเข้าร่วมอย่างมีนัยสำคัญทางสถิติ (p = 0.029) แสดงว่ากิจกรรมการตระหนักรู้ความเสี่ยง การวิเคราะห์ประโยชน์และอุปสรรค การตั้งเป้าหมายสุขภาพรายครัวเรือน และการติดตามรายสัปดาห์ ช่วยให้แกนนำครอบครัวปรับความเชื่อด้านสุขภาพได้จริง สอดคล้องกับแนวคิดของ Rosenstock (1974) ที่อธิบายว่า เมื่อบุคคลรับรู้โอกาสเสี่ยงและความรุนแรงของโรค ตระหนักถึงประโยชน์ของการปฏิบัติ และมองเห็นหนทางลดอุปสรรค จะเกิดแรงจูงใจภายในที่ผลักดันให้ปรับเปลี่ยนพฤติกรรมสุขภาพ และแนวคิดของ Becker (1974) ที่ระบุว่าการให้ข้อมูลย้อนกลับ การสร้างแรงสนับสนุนทางสังคม และการมีส่วนร่วมในการกำหนดเป้าหมาย ช่วยลดอุปสรรคและเพิ่มแรงจูงใจให้บุคคลเปลี่ยนพฤติกรรมสุขภาพได้ง่ายขึ้น"));
add(para("เมื่อเปรียบเทียบระหว่างกลุ่มหลังสิ้นสุดรูปแบบ พบว่ากลุ่มทดลองมีคะแนนแบบแผนความเชื่อด้านสุขภาพ (p < 0.001) และความรอบรู้ด้านสุขภาพ (p = 0.023) สูงกว่ากลุ่มเปรียบเทียบอย่างมีนัยสำคัญทางสถิติ สะท้อนว่ารูปแบบที่บูรณาการทฤษฎีแบบแผนความเชื่อด้านสุขภาพเข้ากับกรอบ V-shape ของกรมอนามัย (สำนักส่งเสริมสุขภาพ, 2565) มีประสิทธิผลในการเสริมทักษะการแสวงหา ประเมิน และใช้ข้อมูลสุขภาพของแกนนำครอบครัว ผ่านการฝึกเข้าถึงแหล่งข้อมูลที่น่าเชื่อถือ การวิเคราะห์ข่าวจริง–ข่าวลวง และการบอกต่อในชุมชน สอดคล้องกับการศึกษาของ Wongkongdech et al. (2024) และ Patchasuwan et al. (2022) ที่พบว่าการส่งเสริมความรอบรู้ด้านสุขภาพแบบมีส่วนร่วมช่วยพัฒนาความรอบรู้และพฤติกรรมสุขภาพของกลุ่มเป้าหมายได้ และการทบทวนวรรณกรรมของ Marshall et al. (2025) ที่พบว่าโปรแกรมที่มุ่งพัฒนาทักษะรายบุคคลสัมพันธ์กับความสามารถในการเข้าใจและใช้ข้อมูลสุขภาพที่ดีขึ้น เช่นเดียวกับแนวคิดของ Nutbeam (2008) ที่อธิบายว่าการพัฒนาความรอบรู้ด้านสุขภาพเป็นกระบวนการเรียนรู้เชิงปฏิบัติที่ต้องอาศัยการมีส่วนร่วมและการเสริมแรงทางสังคม"));
add(para("อย่างไรก็ตาม คะแนนความรอบรู้ด้านสุขภาพภายในกลุ่มทดลองเพิ่มขึ้นแต่ไม่ถึงระดับนัยสำคัญทางสถิติ (p = 0.323) อาจเนื่องจากระยะเวลาการทดลองเพียง 12 สัปดาห์ยังไม่เพียงพอต่อการพัฒนาทักษะในระดับลึก โดยเฉพาะขั้นการประเมินและการประยุกต์ใช้ที่ต้องอาศัยการฝึกฝนต่อเนื่องในชีวิตประจำวัน ประกอบกับแกนนำครอบครัวมีความรอบรู้ด้านสุขภาพในระดับมากอยู่แล้วก่อนเริ่มโปรแกรม ({i}M{/i} = 0.93) ทำให้คะแนนเพิ่มขึ้นได้ไม่มาก สอดคล้องกับ World Health Organization (2021) ที่ระบุว่าการพัฒนาความรอบรู้ด้านสุขภาพต้องอาศัยการเรียนรู้แบบมีส่วนร่วมและการติดตามอย่างต่อเนื่องในชุมชน"));
add(blank());

add(heading("ข้อเสนอแนะในการนำผลการวิจัยไปใช้"));
add(para("1) หน่วยงานสาธารณสุขในเขตสุขภาพที่ 2 ควรนำรูปแบบการยกระดับครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่ ไปขยายผลในการพัฒนาศักยภาพแกนนำสุขภาพชุมชนโดยอิงกรอบความรอบรู้ด้านสุขภาพ และสนับสนุนกองทุนสุขภาพชุมชนระดับตำบลเพื่อให้เกิดกิจกรรมอย่างต่อเนื่อง"));
add(para("2) ควรพัฒนาโมดูลฝึกอบรมที่เน้นการสร้างการรับรู้ความสามารถของตนเอง (Self-efficacy) ผ่านกิจกรรมเชิงปฏิบัติ ร่วมกับระบบเพื่อนช่วยเพื่อน (Peer Support System) ให้แกนนำแลกเปลี่ยนเรียนรู้ระหว่างกันได้ต่อเนื่อง"));
add(para("3) ควรปรับปรุงแพลตฟอร์มสุขภาพดิจิทัลให้ใช้งานง่ายเหมาะกับทุกกลุ่มวัย และจัดทำคู่มือการใช้งานแบบเป็นขั้นตอนสำหรับผู้ที่มีทักษะดิจิทัลน้อย"));
add(blank());

add(heading("ข้อเสนอแนะในการวิจัยครั้งต่อไป"));
add(para("1) ควรติดตามผลในระยะยาว 6 เดือนถึง 1 ปี เพื่อประเมินความคงอยู่ของความเชื่อ ความรอบรู้ และพฤติกรรมสุขภาพ"));
add(para("2) ควรขยายกลุ่มตัวอย่างไปยังพื้นที่ชนบทและเขตเมือง เพื่อเปรียบเทียบผลลัพธ์ตามบริบททางสังคม"));
add(para("3) ควรศึกษารูปแบบการพัฒนาแบบแผนความเชื่อด้านสุขภาพ ความรอบรู้ด้านสุขภาพ และการเสริมสร้างพลังอำนาจทางสุขภาพ (Health Empowerment) ต่อพฤติกรรมการส่งเสริมสุขภาพและพฤติกรรมการป้องกันโรคของแกนนำครอบครัว"));
add(blank());

// References (APA 7th) — Thai ก–ฮ first, then English A–Z
add(heading("รายการอ้างอิง"));
[
  "กรมอนามัย. (2560). {i}การขับเคลื่อนความรอบรู้ด้านสุขภาพและการสื่อสารสุขภาพ{/i}. https://doh.hpc.go.th/data/HL/HL_DOH_drive.pdf",
  "นงลักษณ์ วิรัชชัย. (2555). {i}การกำหนดขนาดตัวอย่างในการทดสอบสมมุติฐานวิจัย{/i} [เอกสารประกอบการบรรยาย]. โครงการ Research Zone ศูนย์การเรียนรู้ทางการวิจัย สำนักงานคณะกรรมการวิจัยแห่งชาติ. https://lllskill.com/web/files/GPower.pdf",
  "วชิระ เพ็งจันทร์. (2560). {i}ความรอบรู้ด้านสุขภาพ{/i}. เอกสารประกอบการประชุมเชิงปฏิบัติการพัฒนาศักยภาพบุคลากรกรมอนามัย เรื่อง ความรอบรู้สุขภาพมุ่งสู่ประเทศไทย. กรมอนามัย กระทรวงสาธารณสุข.",
  "สถาบันวิจัยระบบสาธารณสุข. (2567). {i}การสำรวจความรอบรู้ด้านสุขภาพของประชาชนไทย อายุ 15 ปีขึ้นไป พ.ศ. 2566 (ครั้งที่ 2): การส่งเสริมความรอบรู้ด้านสุขภาพในประเทศไทย การประเมินสถานการณ์ปัจจุบัน ปัจจัยกำหนด และข้อเสนอเชิงนโยบาย{/i}. https://kb.hsri.or.th/dspace/handle/11228/6197",
  "สำนักส่งเสริมสุขภาพ. (2565). {i}ชุดความรู้แนวทางการสร้างพลังครอบครัว ชุมชนรอบรู้สุขภาพภายใต้วิถีชีวิตปกติใหม่{/i}. กรมอนามัย กระทรวงสาธารณสุข.",
  "Becker, M. H. (1974). The health belief model and personal health behavior. {i}Health Education Monographs, 2{/i}(4), 324–473.",
  "Faul, F., Erdfelder, E., Buchner, A., & Lang, A.-G. (2009). Statistical power analyses using G*Power 3.1: Tests for correlation and regression analyses. {i}Behavior Research Methods, 41{/i}(4), 1149–1160. https://doi.org/10.3758/BRM.41.4.1149",
  "Faul, F., Erdfelder, E., Lang, A.-G., & Buchner, A. (2007). G*Power 3: A flexible statistical power analysis program for the social, behavioral, and biomedical sciences. {i}Behavior Research Methods, 39{/i}(2), 175–191. https://doi.org/10.3758/BF03193146",
  "Marshall, N., Butler, M., Lambert, V., Timon, C. M., Joyce, D., & Warters, A. (2025). Health literacy interventions and health literacy-related outcomes for older adults: A systematic review. {i}BMC Health Services Research, 25{/i}, 319. https://doi.org/10.1186/s12913-025-12457-7",
  "Nutbeam, D. (2008). The evolving concept of health literacy. {i}Social Science & Medicine, 67{/i}(12), 2072–2078. https://doi.org/10.1016/j.socscimed.2008.09.050",
  "Patchasuwan, N. H., Banchonhattakit, P., Rattanapitoon, N. K., Nilnate, N., Srithumsuk, W., Heebkaew, S., & Phimha, S. (2022). Development of a school-based health literacy model for liver fluke prevention and control using participatory action research. {i}Asian Pacific Journal of Cancer Prevention, 23{/i}(4), 1177–1183. https://doi.org/10.31557/APJCP.2022.23.4.1177",
  "Rosenstock, I. M. (1974). The health belief model and preventive health behavior. {i}Health Education Monographs, 2{/i}(4), 354–386. https://doi.org/10.1177/109019817400200405",
  "Wongkongdech, A., Kumchan, J., Namyota, C., Chanthamath, S., & Wongkongdech, R. (2024). The effectiveness of participatory health literacy promoting programs among diabetes risk groups in community, Thailand. {i}Asian Journal of Social Health and Behavior, 7{/i}(4), 172–179. https://doi.org/10.4103/shb.shb_166_24",
  "World Health Organization. (2021). {i}Health literacy{/i}. https://www.who.int/news-room/fact-sheets/detail/health-literacy",
].forEach((r) => add(ref(r)));

// ---------------------------------------------------------------- document
const doc = new Document({
  creator: "วีรศักดิ์ พรหมมา",
  title: "ผลของแบบแผนความเชื่อด้านสุขภาพและความรอบรู้ด้านสุขภาพ",
  styles: {
    default: {
      document: {
        run: { font: FONTS, size: 32, sizeComplexScript: 32, language: { value: "en-US", bidirectional: "th-TH", eastAsia: "th-TH" } },
        paragraph: { spacing: SP },
      },
    },
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440, header: 709, footer: 709 } } },
    children: body,
  }],
});
Packer.toBuffer(doc).then(async (b) => {
  // drop w:highlightCs (not in the OOXML schema) so Word never flags the file
  const JSZip = require(require.resolve("jszip", { paths: [require.resolve("docx")] })); const z = await JSZip.loadAsync(b);
  const x = (await z.file("word/document.xml").async("string")).replace(/<w:highlightCs [^>]*\/>/g, "");
  z.file("word/document.xml", x); b = await z.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
  fs.writeFileSync(process.argv[2], b); console.log("written", process.argv[2]); });
