/**
 * Electricity Bill - sidebar panel for Home Assistant (vanilla web component, no build step).
 * Status overview, photo scan via AI Task, editable form, bill history with expandable details.
 * All dynamic text is inserted with textContent / createElement (never innerHTML with data).
 */

const WARNING_MESSAGES = {
  rate_unusual: "อัตราค่าไฟต่อหน่วยดูผิดปกติ (นอกช่วง 1.5 – 12 บาท) ตรวจตัวเลขอีกครั้ง",
  date_in_future: "วันที่สิ้นสุดรอบบิลเป็นวันในอนาคต กรุณาตรวจวันที่",
  invalid_period: "วันเริ่มต้นรอบบิลต้องไม่เกินวันสิ้นสุดรอบบิล",
  kwh_out_of_range: "จำนวนหน่วยอยู่นอกช่วงปกติ (1 – 5,000 kWh)",
  amount_out_of_range: "ยอดเงินอยู่นอกช่วงปกติ (1 – 100,000 บาท)",
};

const ERROR_MESSAGES = {
  no_ai_task:
    "ยังไม่ได้ตั้งค่า AI — ไปที่ Settings → Devices & services → Add integration → Anthropic แล้วใส่ API key ระหว่างนี้พิมพ์ตัวเลขเองได้",
  file_too_large: "ไฟล์รูปใหญ่เกิน 8 MB",
  unsupported_media_type: "รองรับเฉพาะไฟล์ JPEG, PNG หรือ WebP",
  ai_task_failed: "AI อ่านรูปไม่สำเร็จ ลองถ่ายใหม่ให้ชัดขึ้น หรือพิมพ์ตัวเลขเอง",
  invalid_ai_response: "AI ตอบกลับในรูปแบบที่ไม่คาดคิด ลองใหม่อีกครั้ง หรือพิมพ์ตัวเลขเอง",
};

const CONFIDENCE_TEXT = { high: "AI มั่นใจสูง", medium: "AI มั่นใจปานกลาง", low: "AI มั่นใจต่ำ — ตรวจให้ละเอียด" };

// ---- i18n: Thai is the source language (keys); other languages are looked up here.
// To add a language, add an entry to I18N keyed by the Home Assistant language code,
// e.g. I18N.de = { "บันทึกบิล": "Rechnung speichern", ... }; missing keys fall back to Thai.
const I18N = {
  en: {
    "อัตราค่าไฟต่อหน่วยดูผิดปกติ (นอกช่วง 1.5 – 12 บาท) ตรวจตัวเลขอีกครั้ง": "The rate per unit looks unusual (outside 1.5 – 12). Please check the numbers.",
    "วันที่สิ้นสุดรอบบิลเป็นวันในอนาคต กรุณาตรวจวันที่": "The period end date is in the future. Please check the date.",
    "วันเริ่มต้นรอบบิลต้องไม่เกินวันสิ้นสุดรอบบิล": "The period start must not be after the period end.",
    "จำนวนหน่วยอยู่นอกช่วงปกติ (1 – 5,000 kWh)": "The number of units is outside the usual range (1 – 5,000 kWh).",
    "ยอดเงินอยู่นอกช่วงปกติ (1 – 100,000 บาท)": "The amount is outside the usual range (1 – 100,000).",
    "ไฟล์รูปใหญ่เกิน 8 MB": "The image is larger than 8 MB.",
    "รองรับเฉพาะไฟล์ JPEG, PNG หรือ WebP": "Only JPEG, PNG or WebP images are supported.",
    "AI อ่านรูปไม่สำเร็จ ลองถ่ายใหม่ให้ชัดขึ้น หรือพิมพ์ตัวเลขเอง": "The AI could not read the photo. Try a clearer photo or type the numbers yourself.",
    "AI ตอบกลับในรูปแบบที่ไม่คาดคิด ลองใหม่อีกครั้ง หรือพิมพ์ตัวเลขเอง": "The AI replied in an unexpected format. Try again or type the numbers yourself.",
    "AI มั่นใจสูง": "AI confidence: high",
    "AI มั่นใจปานกลาง": "AI confidence: medium",
    "AI มั่นใจต่ำ — ตรวจให้ละเอียด": "AI confidence: low — check carefully",
    "ค่าไฟ": "Electricity",
    "ค่าไฟรอบนี้ (ประมาณการ)": "This cycle (estimate)",
    "ถ่ายรูปบิล": "Take a photo",
    "เลือกรูป": "Choose image",
    "รูปบิล": "Bill photo",
    "กำลังอ่านบิล…": "Reading the bill…",
    "ถ่ายหรือลากรูปบิลมาวางที่นี่": "Take a photo or drop the bill image here",
    "AI จะอ่านวันที่ หน่วย และยอดเงินให้อัตโนมัติ คุณตรวจแก้ได้ก่อนบันทึก": "The AI reads the date, units and amount for you; you can check and edit before saving.",
    "เช่น บิลเดือน ต.ค.": "e.g. October bill",
    "บันทึกบิล": "Save bill",
    "รายละเอียดเพิ่มเติม (ไม่บังคับ)": "More details (optional)",
    "วันเริ่มต้นรอบบิล": "Period start date",
    "ค่าไฟฟ้าฐาน / ค่าพลังงานไฟฟ้า": "Energy charge",
    "บาท": "{cur}",
    "ค่าไฟฟ้าผันแปร (Ft)": "Per-kWh adder (Ft)",
    "ค่าบริการรายเดือน": "Monthly service charge",
    "ภาษีมูลค่าเพิ่ม 7%": "Tax / VAT",
    "หมายเหตุ": "Note",
    "เพิ่มบิลใหม่": "Add a new bill",
    "ถ่ายรูปบิลหรือพิมพ์ตัวเลขเองก็ได้ วันตัดรอบขยับได้ตามบิลจริง": "Photograph the bill or type the numbers. The billing day can follow your real bill.",
    "วันสิ้นสุดรอบบิล": "Period end date",
    "จำนวนหน่วยที่ใช้": "Units used",
    "ยอดเงินรวมทั้งสิ้น": "Total amount",
    "อัตราค่าไฟจริงต่อหน่วย": "Real rate per unit",
    "แนวโน้มค่าไฟรายรอบบิล": "Bill trend",
    "ประวัติบิล": "Bill history",
    "ส่งออกเป็นไฟล์ CSV": "Export as CSV",
    "บิลที่บันทึกไว้ เรียงจากล่าสุด (กดที่แถวเพื่อดูรายละเอียด)": "Saved bills, newest first (tap a row for details)",
    "ตั้งจุดเริ่มนับ": "Set baseline",
    "ขั้นสูง: ตั้งจุดเริ่มนับของมิเตอร์": "Advanced: set a meter's baseline",
    "หน่วยรอบนี้ = ค่ามิเตอร์ปัจจุบัน − จุดเริ่มนับ ใส่ 0 ถ้าตัวนับเพิ่งเริ่มนับจาก 0 และอยากให้ยอดสะสมทั้งหมดเป็นของรอบนี้": "Cycle energy = current meter value − baseline. Enter 0 if the counter just started from 0 and its whole total should count in this cycle.",
    "มิเตอร์": "Meter",
    "ค่าจุดเริ่มนับ": "Baseline value",
    "กดอีกครั้งเพื่อยืนยัน": "Press again to confirm",
    "ตั้งจุดเริ่มนับแล้ว": "Baseline set",
    "ตั้งไม่สำเร็จ: ": "Could not set: ",
    "฿ ": "฿ ",
    " หน่วย": " kWh",
    "ยังไม่มีข้อมูลหน่วย": "No energy data yet",
    " · ผ่านมา ": " · elapsed ",
    " วัน": " day(s)",
    " บาท/หน่วย": " {cur}/kWh",
    "อัตราจากบิลจริง": "Rate from a real bill",
    "ใช้อัตราสำรอง (ยังไม่มีบิล)": "Using the fallback rate (no bill yet)",
    " (ตัดรอบ ": " (billing day ",
    "คาดการณ์ถึงวันตัดรอบ ≈ ฿": "Forecast to billing day ≈ ฿",
    "คาดการณ์ 30 วัน ≈ ฿": "30-day forecast ≈ ฿",
    "ไฟรอบนี้ที่ไม่มีมิเตอร์ย่อย": "Unmetered this cycle",
    "ยอดบิลล่าสุด": "Last bill amount",
    "หน่วยตามบิลล่าสุด": "Last bill units",
    "ไฟที่ไม่ได้วัด": "Unmetered energy",
    "kWh · วัดได้ ": "kWh · metered ",
    "ยังไม่มีบิลที่บันทึก": "No bills saved yet",
    "ถ่ายรูปบิลใบแรกได้เลย": "Photograph your first bill to start",
    "ลบบิลนี้": "Delete this bill",
    "ยืนยันลบ": "Confirm delete",
    "หน่วย/วัน": "kWh/day",
    "บาท/วัน": "{cur}/day",
    "฿": "฿",
    "ยอดเงิน vs ก่อนหน้า": "Amount vs previous",
    "หน่วย vs ก่อนหน้า": "Units vs previous",
    "รายละเอียดรายการค่าไฟ": "Bill breakdown",
    "ผลรวมรายการไม่ตรงกับยอดรวม": "The items do not add up to the total",
    "แก้ไขบิลนี้": "Edit this bill",
    "แก้ไข": "Edit",
    "ต้องมีบิลอย่างน้อย 2 รอบเพื่อแสดงกราฟ": "At least 2 bills are needed to show the chart",
    "กราฟยอดบิลและหน่วยไฟรายรอบบิล": "Chart of bill amount and energy per billing period",
    "ยอดบิล (บาท)": "Bill amount ({cur})",
    "หน่วยไฟ (สูงสุด ": "Energy (max ",
    "ยังไม่มีบิลให้ส่งออก": "No bills to export",
    "ส่งออก ": "Exported ",
    " บิลเป็น CSV แล้ว": " bills to CSV",
    " กำลังแก้ไขบิลวันที่ ": " Editing the bill of ",
    " (เปลี่ยนวันสิ้นสุดรอบบิลไม่ได้ ถ้าจะเปลี่ยนให้ลบแล้วเพิ่มใหม่)": " (the period end cannot be changed; delete and add again to change it)",
    "ยกเลิก": "Cancel",
    " บาท": " {cur}",
    "สแกนไม่สำเร็จ (": "Scan failed (",
    ") พิมพ์ตัวเลขเองได้": "). You can type the numbers yourself.",
    "คำเตือน: ": "Warning: ",
    "มีบิลของวันที่นี้อยู่แล้ว ต้องการแทนที่หรือไม่?": "A bill for this date already exists. Replace it?",
    "แทนที่": "Replace",
    "บันทึกบิลแล้ว · อัตรา ": "Bill saved · rate ",
    "บันทึกไม่สำเร็จ: ": "Could not save: ",
    "ลบบิลแล้ว": "Bill deleted",
    "ลบไม่สำเร็จ: ": "Could not delete: ",
    "วันสิ้นสุดรอบบิล: ": "Period end: ",
    "ยังไม่ได้ตั้งค่า AI — ไปที่ Settings → Devices & services → Add integration → Anthropic แล้วใส่ API key ระหว่างนี้พิมพ์ตัวเลขเองได้": "AI is not set up — go to Settings → Devices & services → Add integration → Anthropic and enter an API key. Meanwhile you can type the numbers yourself."
  },
};
let LANG = "th";
let LOCALE = "th-TH";
let CURRENCY = "THB";
let CUR_SYMBOL = "฿";
function setLanguage(hass) {
  const code = String((hass && hass.locale && hass.locale.language) || (hass && hass.language) || "th").toLowerCase();
  const base = code.split("-")[0];
  LANG = I18N[code] ? code : I18N[base] ? base : base === "th" ? "th" : "en";
  LOCALE = LANG === "th" ? "th-TH" : code || "en";
  CURRENCY = (hass && hass.config && hass.config.currency) || "THB";
  try {
    const part = new Intl.NumberFormat(LOCALE, { style: "currency", currency: CURRENCY, currencyDisplay: "narrowSymbol" })
      .formatToParts(0)
      .find((q) => q.type === "currency");
    CUR_SYMBOL = (part && part.value) || CURRENCY;
  } catch (e) {
    CUR_SYMBOL = CURRENCY;
  }
}
function T(s) {
  const dict = I18N[LANG];
  let out = dict && dict[s] !== undefined ? dict[s] : s;
  if (LANG === "th") {
    if (CURRENCY !== "THB") out = out.replace(/บาท/g, CURRENCY);
  } else {
    out = out.replace(/\{cur\}/g, CURRENCY);
  }
  return out.replace(/฿/g, CUR_SYMBOL);
}

const STYLE = `
  :host {
    --eb-accent: var(--primary-color, #03a9f4);
    --eb-accent-2: color-mix(in srgb, var(--primary-color, #03a9f4) 45%, #7c4dff);
    --eb-radius: 20px;
    --eb-card: var(--card-background-color, #fff);
    --eb-soft: color-mix(in srgb, var(--primary-text-color, #212121) 5%, transparent);
    --eb-line: var(--divider-color, rgba(127,127,127,.25));
    --eb-muted: var(--secondary-text-color, #727272);
    display: block;
    background: var(--primary-background-color, #fafafa);
    color: var(--primary-text-color, #212121);
    font-family: var(--paper-font-body1_-_font-family, Roboto, "Noto Sans Thai", sans-serif);
    min-height: 100%;
    box-sizing: border-box;
  }
  * { box-sizing: border-box; }
  .topbar {
    position: sticky; top: 0; z-index: 5;
    display: flex; align-items: center; gap: 4px;
    height: 56px; padding: 0 8px;
    background: var(--app-header-background-color, var(--primary-background-color));
    color: var(--app-header-text-color, var(--primary-text-color));
    border-bottom: 1px solid var(--eb-line);
  }
  .topbar .title { font-size: 20px; font-weight: 500; margin-left: 4px; }
  .page { max-width: 1100px; margin: 0 auto; padding: 16px 16px 48px; display: grid; gap: 16px; }

  .hero {
    position: relative; overflow: hidden;
    border-radius: var(--eb-radius);
    padding: 24px 24px 22px;
    color: #fff;
    background: linear-gradient(135deg, var(--eb-accent) 0%, var(--eb-accent-2) 100%);
    box-shadow: 0 10px 30px color-mix(in srgb, var(--eb-accent) 35%, transparent);
  }
  .hero::after {
    content: ""; position: absolute; right: -60px; top: -70px; width: 260px; height: 260px; border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, rgba(255,255,255,.28), rgba(255,255,255,0) 70%);
    pointer-events: none;
  }
  .hero-label { font-size: 14px; opacity: .9; display: flex; align-items: center; gap: 8px; }
  .hero-value { font-size: clamp(40px, 9vw, 60px); font-weight: 700; line-height: 1.1; margin: 6px 0 2px; letter-spacing: -.5px; }
  .hero-value small { font-size: .38em; font-weight: 500; opacity: .85; margin-left: 6px; letter-spacing: 0; }
  .hero-sub { font-size: 14px; opacity: .92; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
  .chip {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 12px; border-radius: 999px; font-size: 13px; font-weight: 500;
    background: rgba(255,255,255,.2); backdrop-filter: blur(4px);
  }

  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
  .tile {
    background: var(--eb-card); border: 1px solid var(--eb-line); border-radius: 16px;
    padding: 14px 16px; display: flex; gap: 12px; align-items: center;
  }
  .tile-ico {
    flex: none; width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center;
    background: color-mix(in srgb, var(--eb-accent) 14%, transparent); color: var(--eb-accent);
  }
  .tile-label { font-size: 12px; color: var(--eb-muted); }
  .tile-value { font-size: 20px; font-weight: 650; }
  .tile-value small { font-size: 12px; font-weight: 400; color: var(--eb-muted); margin-left: 3px; }

  .grid { display: grid; gap: 16px; align-items: start; }
  @media (min-width: 860px) { .grid { grid-template-columns: 1.05fr 1fr; } }

  .card {
    background: var(--eb-card); border: 1px solid var(--eb-line); border-radius: var(--eb-radius);
    padding: 20px; box-shadow: var(--ha-card-box-shadow, none);
  }
  .card h2 { margin: 0 0 4px; font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
  .card .hint { margin: 0 0 16px; font-size: 13px; color: var(--eb-muted); }

  .drop {
    position: relative; overflow: hidden;
    border: 2px dashed color-mix(in srgb, var(--eb-accent) 55%, transparent);
    border-radius: 16px; padding: 22px 16px; text-align: center;
    background: color-mix(in srgb, var(--eb-accent) 6%, transparent);
    transition: background .2s, border-color .2s, transform .2s;
  }
  .drop.over { background: color-mix(in srgb, var(--eb-accent) 16%, transparent); transform: scale(1.01); }
  .drop-ico { color: var(--eb-accent); --mdc-icon-size: 40px; }
  .drop-title { font-weight: 600; margin: 6px 0 2px; }
  .drop-sub { font-size: 12.5px; color: var(--eb-muted); margin-bottom: 14px; }
  .btn-row { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
  .preview { display: none; position: relative; margin-bottom: 12px; border-radius: 14px; overflow: hidden; max-height: 220px; }
  .preview.show { display: block; }
  .preview img { width: 100%; max-height: 220px; object-fit: cover; display: block; filter: saturate(.95); }
  .preview.scanning::after {
    content: ""; position: absolute; left: 0; right: 0; top: 0; height: 40%;
    background: linear-gradient(to bottom, rgba(255,255,255,0), color-mix(in srgb, var(--eb-accent) 55%, transparent), rgba(255,255,255,0));
    animation: sweep 1.4s ease-in-out infinite;
  }
  .preview .scan-label {
    position: absolute; left: 10px; bottom: 10px; padding: 6px 12px; border-radius: 999px;
    background: rgba(0,0,0,.6); color: #fff; font-size: 13px; display: none; align-items: center; gap: 8px;
  }
  .preview.scanning .scan-label { display: inline-flex; }
  @keyframes sweep { 0% { transform: translateY(-100%); } 100% { transform: translateY(260%); } }

  .btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    min-height: 44px; padding: 0 18px; border-radius: 12px; border: 0; cursor: pointer;
    font: inherit; font-weight: 600; font-size: 14px;
    color: #fff; background: linear-gradient(135deg, var(--eb-accent), var(--eb-accent-2));
    transition: transform .12s, box-shadow .2s, opacity .2s;
  }
  .btn:hover:not(:disabled) { box-shadow: 0 6px 16px color-mix(in srgb, var(--eb-accent) 35%, transparent); transform: translateY(-1px); }
  .btn:active:not(:disabled) { transform: translateY(0); }
  .btn:disabled { opacity: .4; cursor: not-allowed; }
  .btn.ghost { background: transparent; color: var(--eb-accent); border: 1.5px solid var(--eb-accent); }
  .btn.block { width: 100%; min-height: 50px; font-size: 16px; }
  .btn.small { min-height: 34px; padding: 0 12px; font-size: 13px; border-radius: 10px; }
  .btn.danger { background: var(--error-color, #db4437); }

  .fields { display: grid; gap: 14px; margin-top: 18px; }
  .field label { display: block; font-size: 12.5px; font-weight: 600; color: var(--eb-muted); margin: 0 0 6px 2px; }
  .input {
    display: flex; align-items: center; gap: 8px;
    border: 1.5px solid var(--eb-line); border-radius: 12px; padding: 0 14px; min-height: 50px;
    background: var(--input-fill-color, var(--eb-soft));
    transition: border-color .15s, box-shadow .15s;
  }
  .input:focus-within { border-color: var(--eb-accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--eb-accent) 22%, transparent); }
  .input input {
    flex: 1; min-width: 0; border: 0; outline: 0; background: transparent;
    font: inherit; font-size: 16px; color: var(--primary-text-color); padding: 12px 0;
  }
  .input .unit { color: var(--eb-muted); font-size: 14px; }
  .input.scanned { border-color: color-mix(in srgb, var(--success-color, #43a047) 70%, transparent); }

  /* Collapsible optional details section */
  .details-box {
    margin-top: 14px;
    border: 1.5px solid var(--eb-line);
    border-radius: 14px;
    background: color-mix(in srgb, var(--eb-card) 60%, var(--eb-soft));
    overflow: hidden;
  }
  .details-box summary {
    padding: 12px 14px;
    cursor: pointer;
    font-size: 13.5px;
    font-weight: 600;
    color: var(--eb-accent);
    display: flex;
    align-items: center;
    gap: 8px;
    user-select: none;
    outline: none;
  }
  .details-box summary:hover {
    background: var(--eb-soft);
  }
  .details-box[open] summary {
    border-bottom: 1px solid var(--eb-line);
  }
  .details-body {
    padding: 14px;
    display: grid;
    gap: 12px;
  }

  .rate {
    margin-top: 12px; padding: 12px 16px; border-radius: 14px;
    display: flex; justify-content: space-between; align-items: center;
    background: color-mix(in srgb, var(--eb-accent) 10%, transparent);
  }
  .rate b { font-size: 20px; color: var(--eb-accent); }
  .badge { display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border-radius: 999px; font-size: 12.5px; font-weight: 600; }
  .badge.high { background: rgba(67,160,71,.16); color: var(--success-color, #2e7d32); }
  .badge.medium { background: rgba(251,140,0,.16); color: #e65100; }
  .badge.low { background: rgba(229,57,53,.16); color: var(--error-color, #c62828); }
  .alert { margin-top: 12px; padding: 11px 14px; border-radius: 12px; font-size: 13.5px; line-height: 1.45; display: flex; gap: 10px; }
  .alert.warn { background: rgba(251,140,0,.14); color: #bf5b00; }
  .alert.err { background: rgba(229,57,53,.13); color: var(--error-color, #c62828); }
  .alert.ok { background: rgba(67,160,71,.14); color: var(--success-color, #2e7d32); }
  .alert.ask { background: color-mix(in srgb, var(--eb-accent) 12%, transparent); flex-direction: column; }
  .alert .actions { display: flex; gap: 8px; }

  /* History list with expandable items */
  .history { display: grid; gap: 8px; }
  .row-item {
    border: 1px solid var(--eb-line);
    border-radius: 14px;
    background: var(--eb-card);
    overflow: hidden;
    transition: border-color .15s, box-shadow .15s;
  }
  .row-item:hover {
    border-color: color-mix(in srgb, var(--eb-accent) 40%, var(--eb-line));
  }
  .row-main {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 8px 10px;
    align-items: center;
    padding: 12px 14px;
    cursor: pointer;
    user-select: none;
  }
  .row-left { min-width: 0; }
  .row-date { font-weight: 600; font-size: 15px; display: flex; align-items: center; gap: 6px; }
  .row-meta { font-size: 12.5px; color: var(--eb-muted); margin-top: 2px; }
  .row-right { text-align: right; }
  .row-amt { font-weight: 700; font-size: 16px; }
  .row-chevron {
    color: var(--eb-muted);
    transition: transform .2s ease;
    display: grid; place-items: center;
  }
  .row-item.expanded .row-chevron {
    transform: rotate(180deg);
  }
  .bar-box { padding: 0 14px 10px; }
  .bar { height: 6px; border-radius: 999px; background: var(--eb-soft); overflow: hidden; }
  .bar i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--eb-accent), var(--eb-accent-2)); }

  /* Expanded history details */
  .row-expanded {
    border-top: 1px solid var(--eb-line);
    background: var(--eb-soft);
    padding: 14px;
    display: grid;
    gap: 12px;
    font-size: 13px;
  }
  .row-period {
    font-weight: 600;
    color: var(--eb-muted);
    font-size: 12.5px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 8px 12px;
  }
  .stat-card {
    background: var(--eb-card);
    border: 1px solid var(--eb-line);
    border-radius: 10px;
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .stat-label { font-size: 11.5px; color: var(--eb-muted); }
  .stat-val { font-size: 14px; font-weight: 650; display: flex; align-items: center; gap: 4px; }
  .stat-val.diff-up { color: var(--error-color, #c62828); }
  .stat-val.diff-down { color: var(--success-color, #2e7d32); }

  .charges-box {
    background: var(--eb-card);
    border: 1px solid var(--eb-line);
    border-radius: 12px;
    padding: 10px 12px;
    display: grid;
    gap: 6px;
  }
  .charges-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--eb-muted);
    margin-bottom: 2px;
  }
  .charge-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
    padding: 2px 0;
  }
  .charge-row:not(:last-child) {
    border-bottom: 1px dashed var(--eb-line);
  }
  .charge-val { font-weight: 600; }

  .mismatch-alert {
    background: rgba(251,140,0,.15);
    color: #bf5b00;
    padding: 8px 12px;
    border-radius: 10px;
    font-size: 12.5px;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .note-box {
    font-size: 12.5px;
    color: var(--eb-muted);
    font-style: italic;
    padding: 2px 4px;
    word-break: break-word;
  }

  .row-actions {
    display: flex;
    justify-content: flex-end;
    padding-top: 4px;
  }

  .empty { text-align: center; color: var(--eb-muted); padding: 28px 8px; }
  .empty ha-icon { --mdc-icon-size: 44px; opacity: .5; display: block; margin: 0 auto 6px; }

  .toast {
    position: fixed; left: 50%; bottom: 24px; transform: translate(-50%, 30px); opacity: 0;
    padding: 12px 20px; border-radius: 14px; font-size: 14px; font-weight: 500; color: #fff;
    background: #2e7d32; box-shadow: 0 8px 24px rgba(0,0,0,.25); transition: all .25s; pointer-events: none; z-index: 20;
    max-width: calc(100vw - 32px);
  }
  .toast.show { transform: translate(-50%, 0); opacity: 1; }
  .toast.err { background: #c62828; }
  .spin { width: 16px; height: 16px; border-radius: 50%; border: 2px solid rgba(255,255,255,.4); border-top-color: #fff; animation: rot .8s linear infinite; }
  @keyframes rot { to { transform: rotate(360deg); } }
  .chart-card svg { width: 100%; height: auto; display: block; }
  .chart-card .bar-rect { fill: var(--primary-color, #03a9f4); opacity: .85; }
  .chart-card .bar-rect.latest { opacity: 1; }
  .chart-card .kwh-line { fill: none; stroke: var(--accent-color, #ff9800); stroke-width: 2; }
  .chart-card .kwh-dot { fill: var(--accent-color, #ff9800); }
  .chart-card text { fill: var(--secondary-text-color, #888); font-size: 11px; font-family: inherit; }
  .chart-card .val { fill: var(--primary-text-color, #222); font-size: 11px; }
  .chart-legend { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 6px; font-size: 12px; color: var(--secondary-text-color, #888); }
  .chart-legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
  .edit-banner { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 10px 12px; margin-bottom: 12px; border-radius: 12px; background: var(--secondary-background-color, #eee); font-size: 14px; }
  .card-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .card-head h2 { margin: 0; }
  .input input:disabled { opacity: .6; }
  @media (max-width: 520px) {
    .page { padding: 12px 12px 40px; }
    .hero { padding: 20px; }
    .row-main { grid-template-columns: 1fr auto auto; padding: 10px 12px; }
    .row-amt { font-size: 15px; }
  }
`;

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : String(v));
  }
  for (const c of children) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return node;
}
const icon = (name) => el("ha-icon", { icon: name });
const num = (v, d = 2) =>
  Number(v).toLocaleString(LOCALE, { minimumFractionDigits: d, maximumFractionDigits: d });

class ElectricityBillPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._narrow = false;
    this._built = false;
    this._sig = "";
    this._scanning = false;
    this._fromScan = false;
    this._confidence = null;
    this._warnings = [];
    this._scanError = null;
    this._pendingReplace = false;
    this._delArmed = null;
    this._previewUrl = null;
    this._toastTimer = null;
    this._expandedIds = new Set();
    this._editing = null;
  }

  set hass(h) {
    this._hass = h;
    if (!this._built) {
      setLanguage(h);
      this._build();
    }
    if (this._menu) this._menu.hass = h;
    this._refresh();
  }
  set narrow(v) {
    this._narrow = Boolean(v);
    if (this._menu) this._menu.narrow = this._narrow;
  }
  set panel(_v) {}

  /* ------------------------------ build ------------------------------ */
  _build() {
    this._built = true;
    const root = this.shadowRoot;
    root.append(el("style", { text: STYLE }));

    this._menu = el("ha-menu-button");
    this._menu.hass = this._hass;
    this._menu.narrow = this._narrow;
    root.append(el("div", { class: "topbar" }, this._menu, el("div", { class: "title", text: T("ค่าไฟ") })));

    // hero
    this._heroValue = el("div", { class: "hero-value" });
    this._heroSub = el("div", { class: "hero-sub" });
    this._heroChips = el("div", { class: "chips" });
    const hero = el(
      "div",
      { class: "hero" },
      el("div", { class: "hero-label" }, icon("mdi:flash"), T("ค่าไฟรอบนี้ (ประมาณการ)")),
      this._heroValue,
      this._heroSub,
      this._heroChips
    );

    // tiles
    this._tiles = el("div", { class: "tiles" });

    // scan card
    this._cameraInput = el("input", { type: "file", accept: "image/*", capture: "environment", style: "display:none" });
    this._galleryInput = el("input", { type: "file", accept: "image/*", style: "display:none" });
    for (const inp of [this._cameraInput, this._galleryInput]) {
      inp.addEventListener("change", (e) => {
        const f = e.target.files && e.target.files[0];
        if (f) this._scan(f);
      });
    }
    this._cameraBtn = el("button", { class: "btn", onclick: () => this._cameraInput.click() }, icon("mdi:camera"), T("ถ่ายรูปบิล"));
    this._galleryBtn = el("button", { class: "btn ghost", onclick: () => this._galleryInput.click() }, icon("mdi:image"), T("เลือกรูป"));
    this._previewImg = el("img", { alt: T("รูปบิล") });
    this._preview = el(
      "div",
      { class: "preview" },
      this._previewImg,
      el("span", { class: "scan-label" }, el("span", { class: "spin" }), T("กำลังอ่านบิล…"))
    );
    this._drop = el(
      "div",
      { class: "drop" },
      el("div", { class: "drop-ico" }, icon("mdi:receipt-text-outline")),
      el("div", { class: "drop-title", text: T("ถ่ายหรือลากรูปบิลมาวางที่นี่") }),
      el("div", { class: "drop-sub", text: T("AI จะอ่านวันที่ หน่วย และยอดเงินให้อัตโนมัติ คุณตรวจแก้ได้ก่อนบันทึก") }),
      el("div", { class: "btn-row" }, this._cameraBtn, this._galleryBtn),
      this._cameraInput,
      this._galleryInput
    );
    for (const ev of ["dragenter", "dragover"]) {
      this._drop.addEventListener(ev, (e) => {
        e.preventDefault();
        this._drop.classList.add("over");
      });
    }
    for (const ev of ["dragleave", "drop"]) {
      this._drop.addEventListener(ev, (e) => {
        e.preventDefault();
        this._drop.classList.remove("over");
      });
    }
    this._drop.addEventListener("drop", (e) => {
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) this._scan(f);
    });

    this._notes = el("div"); // errors / warnings / confidence

    // Primary required inputs
    this._dateInput = el("input", { type: "date" });
    this._kwhInput = el("input", { type: "number", step: "any", min: "0", inputmode: "decimal", placeholder: "0.00" });
    this._amountInput = el("input", { type: "number", step: "any", min: "0", inputmode: "decimal", placeholder: "0.00" });

    // Optional detailed inputs
    this._startDateInput = el("input", { type: "date" });
    this._energyChargeInput = el("input", { type: "number", step: "any", min: "0", inputmode: "decimal", placeholder: "0.00" });
    this._ftChargeInput = el("input", { type: "number", step: "any", inputmode: "decimal", placeholder: "0.00" });
    this._serviceChargeInput = el("input", { type: "number", step: "any", min: "0", inputmode: "decimal", placeholder: "0.00" });
    this._vatInput = el("input", { type: "number", step: "any", min: "0", inputmode: "decimal", placeholder: "0.00" });
    this._noteInput = el("input", { type: "text", placeholder: T("เช่น บิลเดือน ต.ค.") });

    const allInputs = [
      this._dateInput,
      this._kwhInput,
      this._amountInput,
      this._startDateInput,
      this._energyChargeInput,
      this._ftChargeInput,
      this._serviceChargeInput,
      this._vatInput,
      this._noteInput,
    ];
    for (const i of allInputs) {
      i.addEventListener("input", () => {
        const wrap = i.closest(".input");
        if (wrap) wrap.classList.remove("scanned");
        this._pendingReplace = false;
        this._onInput();
      });
    }

    const field = (label, input, unit) =>
      el("div", { class: "field" }, el("label", { text: label }), el("div", { class: "input" }, input, unit ? el("span", { class: "unit", text: unit }) : null));

    this._rateVal = el("b", { text: "–" });
    this._askBox = el("div");
    this._saveBtn = el("button", { class: "btn block", disabled: true, onclick: () => this._save(false) }, icon("mdi:content-save"), T("บันทึกบิล"));

    // Collapsible optional details section
    this._detailsEl = el(
      "details",
      { class: "details-box" },
      el("summary", {}, icon("mdi:tune-variant"), T("รายละเอียดเพิ่มเติม (ไม่บังคับ)")),
      el(
        "div",
        { class: "details-body" },
        field(T("วันเริ่มต้นรอบบิล"), this._startDateInput, null),
        field(T("ค่าไฟฟ้าฐาน / ค่าพลังงานไฟฟ้า"), this._energyChargeInput, T("บาท")),
        field(T("ค่าไฟฟ้าผันแปร (Ft)"), this._ftChargeInput, T("บาท")),
        field(T("ค่าบริการรายเดือน"), this._serviceChargeInput, T("บาท")),
        field(T("ภาษีมูลค่าเพิ่ม 7%"), this._vatInput, T("บาท")),
        field(T("หมายเหตุ"), this._noteInput, null)
      )
    );

    this._editBanner = el("div");
    const addCard = el(
      "div",
      { class: "card" },
      el("h2", {}, icon("mdi:camera-plus"), T("เพิ่มบิลใหม่")),
      this._editBanner,
      el("p", { class: "hint", text: T("ถ่ายรูปบิลหรือพิมพ์ตัวเลขเองก็ได้ วันตัดรอบขยับได้ตามบิลจริง") }),
      this._preview,
      this._drop,
      this._notes,
      el(
        "div",
        { class: "fields" },
        field(T("วันสิ้นสุดรอบบิล"), this._dateInput, null),
        field(T("จำนวนหน่วยที่ใช้"), this._kwhInput, "kWh"),
        field(T("ยอดเงินรวมทั้งสิ้น"), this._amountInput, T("บาท")),
        this._detailsEl
      ),
      el("div", { class: "rate" }, el("span", { text: T("อัตราค่าไฟจริงต่อหน่วย") }), el("span", {}, this._rateVal)),
      this._askBox,
      el("div", { style: "margin-top:14px" }, this._saveBtn)
    );

    // history card
    this._history = el("div", { class: "history" });
    this._addCard = addCard;
    this._chart = el("div");
    const chartCard = el(
      "div",
      { class: "card chart-card" },
      el("h2", {}, icon("mdi:chart-bar"), T("แนวโน้มค่าไฟรายรอบบิล")),
      this._chart
    );
    const histCard = el(
      "div",
      { class: "card" },
      el(
        "div",
        { class: "card-head" },
        el("h2", {}, icon("mdi:history"), T("ประวัติบิล")),
        el("button", { class: "btn small ghost", title: T("ส่งออกเป็นไฟล์ CSV"), onclick: () => this._exportCsv() }, icon("mdi:download"), "CSV")
      ),
      el("p", { class: "hint", text: T("บิลที่บันทึกไว้ เรียงจากล่าสุด (กดที่แถวเพื่อดูรายละเอียด)") }),
      this._history
    );

    // advanced: set a source's cycle baseline
    this._baseSel = el("select", {});
    this._baseVal = el("input", { type: "number", step: "any", min: "0", inputmode: "decimal", placeholder: "0", value: "0" });
    this._baseBtn = el("button", { class: "btn ghost block", onclick: () => this._onSetBaseline() }, icon("mdi:flag-checkered"), T("ตั้งจุดเริ่มนับ"));
    this._baseArmed = false;
    const baseCard = el(
      "div",
      { class: "card" },
      el(
        "details",
        { class: "details-box" },
        el("summary", {}, icon("mdi:tune"), T("ขั้นสูง: ตั้งจุดเริ่มนับของมิเตอร์")),
        el(
          "div",
          { class: "details-body" },
          el("p", { class: "hint", text: T("หน่วยรอบนี้ = ค่ามิเตอร์ปัจจุบัน − จุดเริ่มนับ ใส่ 0 ถ้าตัวนับเพิ่งเริ่มนับจาก 0 และอยากให้ยอดสะสมทั้งหมดเป็นของรอบนี้") }),
          field(T("มิเตอร์"), this._baseSel, null),
          field(T("ค่าจุดเริ่มนับ"), this._baseVal, "kWh"),
          this._baseBtn
        )
      )
    );

    this._toast = el("div", { class: "toast" });
    root.append(el("div", { class: "page" }, hero, this._tiles, chartCard, el("div", { class: "grid" }, addCard, histCard), baseCard), this._toast);
  }

  /* ------------------------------ state ------------------------------ */
  _st(id) {
    const s = this._hass.states[id];
    if (!s || s.state === "unavailable" || s.state === "unknown") return null;
    return s;
  }

  _refresh() {
    const ids = [
      "sensor.electricity_bill_effective_rate",
      "sensor.electricity_bill_cycle_energy",
      "sensor.electricity_bill_cycle_cost_estimate",
      "sensor.electricity_bill_last_bill_amount",
      "sensor.electricity_bill_last_bill_energy",
      "sensor.electricity_bill_last_bill_unmetered_energy",
      "sensor.electricity_bill_cycle_unmetered_energy",
      "sensor.electricity_bill_cycle_bill_estimate",
      "sensor.electricity_bill_forecast_bill",
      "sensor.electricity_bill_bill_history",
    ];
    const sig =
      ids
        .map((i) => {
          const s = this._hass.states[i];
          return s ? s.state + "|" + s.last_updated : "-";
        })
        .join(";") +
      "|" +
      this._delArmed +
      "|" +
      Array.from(this._expandedIds).join(",");
    if (sig === this._sig) return; // nothing relevant changed
    this._sig = sig;
    this._renderStatus();
    this._renderHistory();
    this._renderChart();
  }

  _renderBaselineOptions() {
    const cycle = this._hass.states["sensor.electricity_bill_cycle_energy"];
    const ids = Object.keys((cycle && cycle.attributes && cycle.attributes.per_source) || {});
    const key = ids.join(",");
    if (key === this._baseKey) return;
    this._baseKey = key;
    const prev = this._baseSel.value;
    this._baseSel.replaceChildren(
      ...ids.map((id) => {
        const fs = this._hass.states[id];
        return el("option", { value: id, text: ((fs && fs.attributes.friendly_name) || id) + " (" + id + ")" });
      })
    );
    if (ids.includes(prev)) this._baseSel.value = prev;
  }

  async _onSetBaseline() {
    const entity = this._baseSel.value;
    if (!entity) return;
    if (!this._baseArmed) {
      this._baseArmed = true;
      this._baseBtn.textContent = T("กดอีกครั้งเพื่อยืนยัน");
      clearTimeout(this._baseTimer);
      this._baseTimer = setTimeout(() => {
        this._baseArmed = false;
        this._baseBtn.replaceChildren(icon("mdi:flag-checkered"), T("ตั้งจุดเริ่มนับ"));
      }, 3000);
      return;
    }
    clearTimeout(this._baseTimer);
    this._baseArmed = false;
    this._baseBtn.replaceChildren(icon("mdi:flag-checkered"), T("ตั้งจุดเริ่มนับ"));
    const value = this._baseVal.value === "" ? 0 : Number(this._baseVal.value);
    try {
      await this._hass.callService("electricity_bill", "set_baseline", { entity_id: entity, value });
      this._toastMsg(T("ตั้งจุดเริ่มนับแล้ว"), false);
    } catch (err) {
      this._toastMsg(T("ตั้งไม่สำเร็จ: ") + ((err && err.message) || err), true);
    }
    this._sig = "";
    this._refresh();
  }

  _renderStatus() {
    this._renderBaselineOptions();
    const rate = this._st("sensor.electricity_bill_effective_rate");
    const cyc = this._st("sensor.electricity_bill_cycle_energy");
    const costSimple = this._st("sensor.electricity_bill_cycle_cost_estimate");
    const costTariff = this._st("sensor.electricity_bill_cycle_bill_estimate");
    const cost = costTariff || costSimple;
    const fc = this._st("sensor.electricity_bill_forecast_bill");
    const lastAmt = this._st("sensor.electricity_bill_last_bill_amount");
    const lastKwh = this._st("sensor.electricity_bill_last_bill_energy");
    const unm = this._st("sensor.electricity_bill_last_bill_unmetered_energy");

    this._heroValue.replaceChildren(
      document.createTextNode(T("฿ ") + (cost ? num(cost.state, 2) : "–"))
    );
    const days = cyc && cyc.attributes.days_in_cycle;
    const kwhTxt = cyc ? num(cyc.state, 1) + T(" หน่วย") : T("ยังไม่มีข้อมูลหน่วย");
    this._heroSub.textContent =
      kwhTxt + (days != null ? T(" · ผ่านมา ") + days + T(" วัน") : "") + (rate ? " · " + num(rate.state, 2) + T(" บาท/หน่วย") : "");

    this._heroChips.replaceChildren();
    if (rate) {
      const fromBill = rate.attributes.source === "bill";
      this._heroChips.append(
        el("span", { class: "chip" }, icon(fromBill ? "mdi:check-decagram" : "mdi:information-outline"), fromBill ? T("อัตราจากบิลจริง") : T("ใช้อัตราสำรอง (ยังไม่มีบิล)"))
      );
    }
    if (fc) {
      const cd = fc.attributes.cutoff_date ? new Date(fc.attributes.cutoff_date + "T00:00:00") : null;
      const cdTxt = cd ? T(" (ตัดรอบ ") + cd.getDate() + "/" + (cd.getMonth() + 1) + ")" : "";
      this._heroChips.append(el("span", { class: "chip" }, icon("mdi:trending-up"), T("คาดการณ์ถึงวันตัดรอบ ≈ ฿") + num(fc.state, 0) + cdTxt));
    } else if (cost && cyc && Number(days) >= 3) {
      const proj = (Number(cost.state) / Number(days)) * 30;
      this._heroChips.append(el("span", { class: "chip" }, icon("mdi:trending-up"), T("คาดการณ์ 30 วัน ≈ ฿") + num(proj, 0)));
    }

    const tile = (ico, label, value, unit) =>
      el(
        "div",
        { class: "tile" },
        el("div", { class: "tile-ico" }, icon(ico)),
        el(
          "div",
          {},
          el("div", { class: "tile-label", text: label }),
          el("div", { class: "tile-value" }, value === null ? "–" : value, value !== null && unit ? el("small", { text: unit }) : null)
        )
      );
    const cycUnm = this._st("sensor.electricity_bill_cycle_unmetered_energy");
    const cycleUnmTile = this._hass.states["sensor.electricity_bill_cycle_unmetered_energy"]
      ? [tile("mdi:home-lightning-bolt-outline", T("ไฟรอบนี้ที่ไม่มีมิเตอร์ย่อย"), cycUnm ? num(cycUnm.state, 1) : null, "kWh")]
      : [];
    this._tiles.replaceChildren(
      ...cycleUnmTile,
      tile("mdi:receipt-text", T("ยอดบิลล่าสุด"), lastAmt ? num(lastAmt.state, 2) : null, T("บาท")),
      tile("mdi:lightning-bolt", T("หน่วยตามบิลล่าสุด"), lastKwh ? num(lastKwh.state, 1) : null, "kWh"),
      tile(
        "mdi:eye-off-outline",
        T("ไฟที่ไม่ได้วัด"),
        unm ? num(unm.state, 1) : null,
        unm && unm.attributes.share_metered_percent != null ? T("kWh · วัดได้ ") + num(unm.attributes.share_metered_percent, 0) + "%" : "kWh"
      )
    );
  }

  _renderHistory() {
    const s = this._hass.states["sensor.electricity_bill_bill_history"];
    const bills = (s && s.attributes && s.attributes.bills) || [];
    this._history.replaceChildren();
    if (!bills.length) {
      this._history.append(el("div", { class: "empty" }, icon("mdi:file-document-outline"), T("ยังไม่มีบิลที่บันทึก"), el("br"), T("ถ่ายรูปบิลใบแรกได้เลย")));
      return;
    }
    const max = Math.max(...bills.map((b) => Number(b.amount) || 0), 1);
    for (const b of bills) {
      const d = b.period_end ? new Date(b.period_end + "T12:00:00") : null;
      const dateTxt = d && !isNaN(d) ? d.toLocaleDateString(LOCALE, { day: "numeric", month: "short", year: "2-digit" }) : b.period_end || "–";
      const rowKey = b.id || b.period_end;
      const isExpanded = this._expandedIds.has(rowKey);
      const armed = this._delArmed === b.period_end;

      const delBtn = el(
        "button",
        {
          class: "btn small " + (armed ? "danger" : "ghost"),
          title: T("ลบบิลนี้"),
          onclick: (e) => {
            e.stopPropagation();
            this._onDelete(b.period_end);
          },
        },
        icon(armed ? "mdi:delete-forever" : "mdi:delete-outline"),
        armed ? T("ยืนยันลบ") : null
      );

      // Main one-line summary
      const rowMain = el(
        "div",
        {
          class: "row-main",
          onclick: () => {
            if (this._expandedIds.has(rowKey)) {
              this._expandedIds.delete(rowKey);
            } else {
              this._expandedIds.add(rowKey);
            }
            this._sig = "";
            this._refresh();
          },
        },
        el(
          "div",
          { class: "row-left" },
          el("div", { class: "row-date" }, dateTxt),
          el("div", { class: "row-meta", text: num(b.kwh, 1) + " kWh · " + num(b.rate, 2) + T(" บาท/หน่วย") })
        ),
        el(
          "div",
          { class: "row-right" },
          el("div", { class: "row-amt", text: T("฿ ") + num(b.amount, 2) })
        ),
        el("div", { class: "row-chevron" }, icon("mdi:chevron-down"))
      );

      const barBox = el(
        "div",
        { class: "bar-box" },
        el("div", { class: "bar" }, el("i", { style: "width:" + Math.max(4, Math.round(((Number(b.amount) || 0) / max) * 100)) + "%" }))
      );

      const rowEl = el("div", { class: "row-item" + (isExpanded ? " expanded" : "") }, rowMain, barBox);

      // Expanded section
      if (isExpanded) {
        // 1. Period formatting
        let periodTxt = "";
        if (b.period_start && b.period_end) {
          const sDate = new Date(b.period_start + "T12:00:00");
          const sTxt = !isNaN(sDate) ? sDate.toLocaleDateString(LOCALE, { day: "numeric", month: "short", year: "2-digit" }) : b.period_start;
          periodTxt = `${sTxt} – ${dateTxt}` + (b.days != null ? ` (${b.days}${T(" วัน")})` : "");
        } else {
          periodTxt = T("วันสิ้นสุดรอบบิล: ") + dateTxt + (b.days != null ? ` (${b.days}${T(" วัน")})` : "");
        }

        // 2. Diff badges (green down arrow / red up arrow)
        const formatDiff = (val) => {
          if (val == null) return el("span", { text: "–" });
          if (val > 0) {
            return el("span", { class: "diff-up" }, icon("mdi:arrow-up"), `+${num(val, 1)}%`);
          }
          if (val < 0) {
            return el("span", { class: "diff-down" }, icon("mdi:arrow-down"), `${num(val, 1)}%`);
          }
          return el("span", { text: "0.0%" });
        };

        const statsGrid = el(
          "div",
          { class: "stats-grid" },
          el(
            "div",
            { class: "stat-card" },
            el("span", { class: "stat-label", text: T("หน่วย/วัน") }),
            el("span", { class: "stat-val", text: b.kwh_per_day != null ? num(b.kwh_per_day, 2) + " kWh" : "–" })
          ),
          el(
            "div",
            { class: "stat-card" },
            el("span", { class: "stat-label", text: T("บาท/วัน") }),
            el("span", { class: "stat-val", text: b.baht_per_day != null ? T("฿") + num(b.baht_per_day, 2) : "–" })
          ),
          el(
            "div",
            { class: "stat-card" },
            el("span", { class: "stat-label", text: T("ยอดเงิน vs ก่อนหน้า") }),
            el("span", { class: "stat-val" }, formatDiff(b.amount_change_pct))
          ),
          el(
            "div",
            { class: "stat-card" },
            el("span", { class: "stat-label", text: T("หน่วย vs ก่อนหน้า") }),
            el("span", { class: "stat-val" }, formatDiff(b.kwh_change_pct))
          )
        );

        // 3. The four items (show "-" when null)
        const chargeRow = (label, val, unit = T("บาท")) => {
          let displayVal = "–";
          if (val !== null && val !== undefined) {
            displayVal = (val > 0 && label.includes("Ft") ? "+" : "") + num(val, 2) + " " + unit;
          }
          return el("div", { class: "charge-row" }, el("span", { text: label }), el("span", { class: "charge-val", text: displayVal }));
        };

        const chargesBox = el(
          "div",
          { class: "charges-box" },
          el("div", { class: "charges-title", text: T("รายละเอียดรายการค่าไฟ") }),
          chargeRow(T("ค่าไฟฟ้าฐาน / ค่าพลังงานไฟฟ้า"), b.energy_charge),
          chargeRow(T("ค่าไฟฟ้าผันแปร (Ft)"), b.ft_charge),
          chargeRow(T("ค่าบริการรายเดือน"), b.service_charge),
          chargeRow(T("ภาษีมูลค่าเพิ่ม 7%"), b.vat)
        );

        const expandedChildren = [
          el("div", { class: "row-period" }, icon("mdi:calendar-range"), periodTxt),
          statsGrid,
          chargesBox,
        ];

        // 4. Mismatch warning line when items_mismatch
        if (b.items_mismatch) {
          expandedChildren.push(
            el("div", { class: "mismatch-alert" }, icon("mdi:alert"), T("ผลรวมรายการไม่ตรงกับยอดรวม"))
          );
        }

        // 5. Note
        if (b.note && b.note.trim()) {
          expandedChildren.push(
            el("div", { class: "note-box" }, icon("mdi:note-text-outline"), " " + b.note)
          );
        }

        // 6. Row actions (delete button)
        const editBtn = el(
          "button",
          {
            class: "btn small ghost",
            title: T("แก้ไขบิลนี้"),
            onclick: (e) => {
              e.stopPropagation();
              this._onEdit(b);
            },
          },
          icon("mdi:pencil-outline"),
          T("แก้ไข")
        );
        expandedChildren.push(
          el("div", { class: "row-actions" }, editBtn, delBtn)
        );

        rowEl.append(el("div", { class: "row-expanded" }, ...expandedChildren));
      }

      this._history.append(rowEl);
    }
  }

  /* ------------------------------ chart / csv / edit ------------------------------ */
  _renderChart() {
    const s = this._hass.states["sensor.electricity_bill_bill_history"];
    const all = ((s && s.attributes && s.attributes.bills) || []).slice().reverse(); // oldest first
    const bills = all.slice(-12);
    this._chart.replaceChildren();
    if (bills.length < 2) {
      this._chart.append(el("p", { class: "hint", text: T("ต้องมีบิลอย่างน้อย 2 รอบเพื่อแสดงกราฟ") }));
      return;
    }
    const W = 600;
    const H = 210;
    const padL = 8;
    const padR = 8;
    const padT = 22;
    const padB = 30;
    const maxAmt = Math.max(...bills.map((b) => Number(b.amount) || 0), 1);
    const maxKwh = Math.max(...bills.map((b) => Number(b.kwh) || 0), 1);
    const slot = (W - padL - padR) / bills.length;
    const barW = Math.min(46, slot * 0.62);
    const NS = "http://www.w3.org/2000/svg";
    const svgEl = (tag, attrs, text) => {
      const n = document.createElementNS(NS, tag);
      for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, String(v));
      if (text !== undefined) n.textContent = text;
      return n;
    };
    const svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": T("กราฟยอดบิลและหน่วยไฟรายรอบบิล") });
    const pts = [];
    bills.forEach((b, i) => {
      const x = padL + slot * i + (slot - barW) / 2;
      const h = ((Number(b.amount) || 0) / maxAmt) * (H - padT - padB);
      const y = H - padB - h;
      svg.append(svgEl("rect", { class: "bar-rect" + (i === bills.length - 1 ? " latest" : ""), x, y, width: barW, height: Math.max(2, h), rx: 4 }));
      svg.append(svgEl("text", { class: "val", x: x + barW / 2, y: y - 5, "text-anchor": "middle" }, num(b.amount, 0)));
      const d = b.period_end ? new Date(b.period_end + "T12:00:00") : null;
      const label = d && !isNaN(d) ? d.toLocaleDateString(LOCALE, { month: "short" }) : "";
      svg.append(svgEl("text", { x: x + barW / 2, y: H - padB + 16, "text-anchor": "middle" }, label));
      pts.push([x + barW / 2, H - padB - ((Number(b.kwh) || 0) / maxKwh) * (H - padT - padB)]);
    });
    svg.append(svgEl("polyline", { class: "kwh-line", points: pts.map((q) => q[0].toFixed(1) + "," + q[1].toFixed(1)).join(" ") }));
    for (const q of pts) svg.append(svgEl("circle", { class: "kwh-dot", cx: q[0], cy: q[1], r: 3.5 }));
    this._chart.append(svg);
    this._chart.append(
      el(
        "div",
        { class: "chart-legend" },
        el("span", {}, el("i", { style: "background:var(--primary-color,#03a9f4)" }), T("ยอดบิล (บาท)")),
        el("span", {}, el("i", { style: "background:var(--accent-color,#ff9800)" }), T("หน่วยไฟ (สูงสุด ") + num(maxKwh, 0) + " kWh)")
      )
    );
  }

  _exportCsv() {
    const s = this._hass.states["sensor.electricity_bill_bill_history"];
    const bills = ((s && s.attributes && s.attributes.bills) || []).slice().reverse();
    if (!bills.length) {
      this._toastMsg(T("ยังไม่มีบิลให้ส่งออก"), true);
      return;
    }
    const cols = [
      "period_start", "period_end", "days", "kwh", "amount", "rate",
      "energy_charge", "ft_charge", "service_charge", "vat", "kwh_per_day", "baht_per_day", "note",
    ];
    const esc = (v) => {
      if (v === null || v === undefined) return "";
      const str = String(v);
      return /[",\n]/.test(str) ? '"' + str.replace(/"/g, '""') + '"' : str;
    };
    const lines = [cols.join(",")].concat(bills.map((b) => cols.map((c) => esc(b[c])).join(",")));
    const blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = el("a", { href: url, download: "electricity-bills.csv" });
    this.shadowRoot.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    this._toastMsg(T("ส่งออก ") + bills.length + T(" บิลเป็น CSV แล้ว"), false);
  }

  _onEdit(b) {
    this._editing = b.period_end;
    this._dateInput.value = b.period_end || "";
    this._dateInput.disabled = true;
    this._kwhInput.value = b.kwh != null ? b.kwh : "";
    this._amountInput.value = b.amount != null ? b.amount : "";
    this._startDateInput.value = b.period_start_manual || "";
    this._energyChargeInput.value = b.energy_charge != null ? b.energy_charge : "";
    this._ftChargeInput.value = b.ft_charge != null ? b.ft_charge : "";
    this._serviceChargeInput.value = b.service_charge != null ? b.service_charge : "";
    this._vatInput.value = b.vat != null ? b.vat : "";
    this._noteInput.value = b.note && b.note !== "manual" && b.note !== "scan" ? b.note : "";
    if (this._detailsEl) this._detailsEl.open = [b.energy_charge, b.ft_charge, b.service_charge, b.vat].some((v) => v != null);
    const d = b.period_end ? new Date(b.period_end + "T12:00:00") : null;
    const dTxt = d && !isNaN(d) ? d.toLocaleDateString(LOCALE, { day: "numeric", month: "short", year: "2-digit" }) : b.period_end;
    this._editBanner.replaceChildren(
      el(
        "div",
        { class: "edit-banner" },
        el("span", {}, icon("mdi:pencil"), T(" กำลังแก้ไขบิลวันที่ ") + dTxt + T(" (เปลี่ยนวันสิ้นสุดรอบบิลไม่ได้ ถ้าจะเปลี่ยนให้ลบแล้วเพิ่มใหม่)")),
        el("button", { class: "btn small ghost", onclick: () => this._exitEdit(true) }, T("ยกเลิก"))
      )
    );
    this._onInput();
    this._addCard.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  _exitEdit(clearInputs) {
    this._editing = null;
    this._dateInput.disabled = false;
    this._editBanner.replaceChildren();
    if (clearInputs) {
      for (const i of [this._dateInput, this._kwhInput, this._amountInput, this._startDateInput, this._energyChargeInput, this._ftChargeInput, this._serviceChargeInput, this._vatInput, this._noteInput]) {
        i.value = "";
      }
      if (this._detailsEl) this._detailsEl.open = false;
      this._onInput();
    }
  }

  /* ------------------------------ form ------------------------------ */
  _onInput() {
    const kwh = parseFloat(this._kwhInput.value);
    const amt = parseFloat(this._amountInput.value);
    const okK = !isNaN(kwh) && kwh > 0;
    const okA = !isNaN(amt) && amt > 0;
    this._rateVal.textContent = okK && okA ? num(amt / kwh, 2) + T(" บาท") : "–";
    this._saveBtn.disabled = !(this._dateInput.value && okK && okA);
    this._askBox.replaceChildren();
  }

  _renderNotes() {
    this._notes.replaceChildren();
    if (this._scanError) {
      this._notes.append(el("div", { class: "alert err" }, icon("mdi:alert-circle"), T(ERROR_MESSAGES[this._scanError] || "")  || T("สแกนไม่สำเร็จ (") + this._scanError + T(") พิมพ์ตัวเลขเองได้")));
    }
    if (this._confidence) {
      const c = ["high", "medium", "low"].includes(this._confidence) ? this._confidence : "low";
      this._notes.append(el("div", { style: "margin-top:12px" }, el("span", { class: "badge " + c }, icon("mdi:robot-outline"), T(CONFIDENCE_TEXT[c]))));
    }
    for (const code of this._warnings) {
      this._notes.append(el("div", { class: "alert warn" }, icon("mdi:alert"), T(WARNING_MESSAGES[code] || "") || T("คำเตือน: ") + code));
    }
  }

  /* ------------------------------ image scan ------------------------------ */
  _resize(file) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        const max = 1600;
        let w = img.naturalWidth;
        let h = img.naturalHeight;
        if (Math.max(w, h) > max) {
          const k = max / Math.max(w, h);
          w = Math.round(w * k);
          h = Math.round(h * k);
        }
        const c = document.createElement("canvas");
        c.width = w;
        c.height = h;
        c.getContext("2d").drawImage(img, 0, 0, w, h);
        URL.revokeObjectURL(url);
        c.toBlob((b) => (b ? resolve(b) : reject(new Error("resize_failed"))), "image/jpeg", 0.85);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("image_load_failed"));
      };
      img.src = url;
    });
  }

  async _scan(file) {
    if (this._scanning) return;
    this._scanning = true;
    this._scanError = null;
    this._warnings = [];
    this._confidence = null;
    this._renderNotes();
    this._cameraBtn.disabled = this._galleryBtn.disabled = true;

    if (this._previewUrl) URL.revokeObjectURL(this._previewUrl);
    this._previewUrl = URL.createObjectURL(file);
    this._previewImg.src = this._previewUrl;
    this._preview.classList.add("show", "scanning");

    try {
      const blob = await this._resize(file);
      const fd = new FormData();
      fd.append("file", blob, "bill.jpg");
      const resp = await this._hass.fetchWithAuth("/api/electricity_bill/scan", { method: "POST", body: fd });
      let data = null;
      try {
        data = await resp.json();
      } catch (_e) {
        data = null;
      }
      if (data && data.ok && data.result) {
        const r = data.result;
        this._fromScan = true;
        const mark = (input, v) => {
          if (v === null || v === undefined || v === "") return false;
          input.value = v;
          const wrap = input.closest(".input");
          if (wrap) wrap.classList.add("scanned");
          return true;
        };

        // Required fields
        mark(this._dateInput, r.period_end);
        mark(this._kwhInput, r.kwh);
        mark(this._amountInput, r.amount);

        // Optional detailed fields pre-filled from scan
        let hadOptional = false;
        if (mark(this._startDateInput, r.period_start)) hadOptional = true;
        if (mark(this._energyChargeInput, r.energy_charge)) hadOptional = true;
        if (mark(this._ftChargeInput, r.ft_charge)) hadOptional = true;
        if (mark(this._serviceChargeInput, r.service_charge)) hadOptional = true;
        if (mark(this._vatInput, r.vat)) hadOptional = true;

        if (hadOptional && this._detailsEl) {
          this._detailsEl.open = true;
        }

        this._confidence = r.confidence || "low";
        this._warnings = Array.isArray(r.warnings) ? r.warnings : [];
        if (r.period_end == null && r.kwh == null && r.amount == null) this._scanError = "ai_task_failed";
      } else {
        this._scanError = (data && data.error) || "scan_failed";
      }
    } catch (err) {
      this._scanError = (err && err.message) || "upload_failed";
    } finally {
      this._scanning = false;
      this._preview.classList.remove("scanning");
      this._cameraBtn.disabled = this._galleryBtn.disabled = false;
      this._cameraInput.value = "";
      this._galleryInput.value = "";
      this._renderNotes();
      this._onInput();
    }
  }

  /* ------------------------------ save / delete ------------------------------ */
  async _save(replace) {
    const period_end = this._dateInput.value;
    const kwh = parseFloat(this._kwhInput.value);
    const amount = parseFloat(this._amountInput.value);
    if (!period_end || !(kwh > 0) || !(amount > 0)) return;

    const s = this._hass.states["sensor.electricity_bill_bill_history"];
    const exists = ((s && s.attributes.bills) || []).some((b) => b.period_end === period_end);
    if (this._editing === period_end) replace = true;
    if (exists && !replace) {
      this._askBox.replaceChildren(
        el(
          "div",
          { class: "alert ask" },
          el("div", { text: T("มีบิลของวันที่นี้อยู่แล้ว ต้องการแทนที่หรือไม่?") }),
          el(
            "div",
            { class: "actions" },
            el("button", { class: "btn small", onclick: () => this._save(true) }, T("แทนที่")),
            el("button", { class: "btn small ghost", onclick: () => this._askBox.replaceChildren() }, T("ยกเลิก"))
          )
        )
      );
      return;
    }

    this._saveBtn.disabled = true;
    this._askBox.replaceChildren();

    const parseCharge = (inp) => {
      const v = parseFloat(inp.value);
      return isNaN(v) ? null : v;
    };

    const payload = {
      period_end,
      kwh,
      amount,
      note: this._noteInput.value.trim() || (this._fromScan ? "scan" : "manual"),
      replace: Boolean(replace),
    };

    if (this._startDateInput.value) {
      payload.period_start = this._startDateInput.value;
    }
    const ec = parseCharge(this._energyChargeInput);
    if (ec !== null) payload.energy_charge = ec;
    const ft = parseCharge(this._ftChargeInput);
    if (ft !== null) payload.ft_charge = ft;
    const sc = parseCharge(this._serviceChargeInput);
    if (sc !== null) payload.service_charge = sc;
    const vat = parseCharge(this._vatInput);
    if (vat !== null) payload.vat = vat;

    try {
      await this._hass.callService("electricity_bill", "add_bill", payload);
      this._toastMsg(T("บันทึกบิลแล้ว · อัตรา ") + num(amount / kwh, 2) + T(" บาท/หน่วย"), false);

      const allInputs = [
        this._dateInput,
        this._kwhInput,
        this._amountInput,
        this._startDateInput,
        this._energyChargeInput,
        this._ftChargeInput,
        this._serviceChargeInput,
        this._vatInput,
        this._noteInput,
      ];
      for (const i of allInputs) {
        i.value = "";
        const wrap = i.closest(".input");
        if (wrap) wrap.classList.remove("scanned");
      }
      if (this._detailsEl) this._detailsEl.open = false;
      this._exitEdit(false);

      this._fromScan = false;
      this._confidence = null;
      this._warnings = [];
      this._scanError = null;
      this._preview.classList.remove("show");
      this._renderNotes();
    } catch (err) {
      this._toastMsg(T("บันทึกไม่สำเร็จ: ") + ((err && err.message) || err), true);
    } finally {
      this._onInput();
    }
  }

  async _onDelete(periodEnd) {
    if (!periodEnd) return;
    if (this._delArmed !== periodEnd) {
      this._delArmed = periodEnd;
      this._sig = "";
      this._refresh();
      clearTimeout(this._delTimer);
      this._delTimer = setTimeout(() => {
        this._delArmed = null;
        this._sig = "";
        if (this._hass) this._refresh();
      }, 3000);
      return;
    }
    clearTimeout(this._delTimer);
    this._delArmed = null;
    try {
      await this._hass.callService("electricity_bill", "remove_bill", { period_end: periodEnd });
      this._toastMsg(T("ลบบิลแล้ว"), false);
    } catch (err) {
      this._toastMsg(T("ลบไม่สำเร็จ: ") + ((err && err.message) || err), true);
    }
    this._sig = "";
    this._refresh();
  }

  _toastMsg(text, isErr) {
    this._toast.textContent = text;
    this._toast.className = "toast show" + (isErr ? " err" : "");
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => this._toast.classList.remove("show"), 3500);
  }
}

if (!customElements.get("electricity-bill-panel")) {
  customElements.define("electricity-bill-panel", ElectricityBillPanel);
}
