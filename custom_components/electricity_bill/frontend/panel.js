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
    "ใช้ไฟวันนี้": "Today",
    " · เมื่อวาน ": " · yesterday ",
    "เทียบรอบก่อน ": "vs previous cycle ",
    "ใช้ไฟรายเครื่อง (รอบนี้)": "Energy by device (this cycle)",
    "ยังไม่มีข้อมูลรายเครื่อง": "No per-device data yet",
    "ใช้ไฟรายวัน (รอบนี้)": "Daily usage (this cycle)",
    "ยังไม่มีสถิติรายวัน มิเตอร์เพิ่งเริ่มบันทึก": "No daily statistics yet: the meter has just started recording",
    "อ่านสถิติรายวันไม่สำเร็จ": "Could not read the daily statistics",
    "เฉลี่ย ": "Avg ",
    "รวม ": "Total ",
    "วันนี้": "Today",

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
  vi: {
    "ใช้ไฟวันนี้": "Hôm nay",
    " · เมื่อวาน ": " · hôm qua ",
    "เทียบรอบก่อน ": "so với kỳ trước ",
    "ใช้ไฟรายเครื่อง (รอบนี้)": "Điện theo thiết bị (kỳ này)",
    "ยังไม่มีข้อมูลรายเครื่อง": "Chưa có dữ liệu theo thiết bị",
    "ใช้ไฟรายวัน (รอบนี้)": "Mức dùng theo ngày (kỳ này)",
    "ยังไม่มีสถิติรายวัน มิเตอร์เพิ่งเริ่มบันทึก": "Chưa có thống kê theo ngày: công tơ vừa bắt đầu ghi",
    "อ่านสถิติรายวันไม่สำเร็จ": "Không đọc được thống kê theo ngày",
    "เฉลี่ย ": "TB ",
    "รวม ": "Tổng ",
    "วันนี้": "Hôm nay",
    "อัตราค่าไฟต่อหน่วยดูผิดปกติ (นอกช่วง 1.5 – 12 บาท) ตรวจตัวเลขอีกครั้ง": "Đơn giá mỗi số điện có vẻ bất thường (ngoài 1,5 – 12). Vui lòng kiểm tra lại số liệu.",
    "วันที่สิ้นสุดรอบบิลเป็นวันในอนาคต กรุณาตรวจวันที่": "Ngày kết thúc kỳ hóa đơn ở tương lai. Vui lòng kiểm tra ngày.",
    "วันเริ่มต้นรอบบิลต้องไม่เกินวันสิ้นสุดรอบบิล": "Ngày bắt đầu kỳ không được sau ngày kết thúc.",
    "จำนวนหน่วยอยู่นอกช่วงปกติ (1 – 5,000 kWh)": "Số kWh nằm ngoài khoảng thông thường (1 – 5.000 kWh).",
    "ยอดเงินอยู่นอกช่วงปกติ (1 – 100,000 บาท)": "Số tiền nằm ngoài khoảng thông thường (1 – 100.000).",
    "ไฟล์รูปใหญ่เกิน 8 MB": "Ảnh lớn hơn 8 MB.",
    "รองรับเฉพาะไฟล์ JPEG, PNG หรือ WebP": "Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP.",
    "AI อ่านรูปไม่สำเร็จ ลองถ่ายใหม่ให้ชัดขึ้น หรือพิมพ์ตัวเลขเอง": "AI không đọc được ảnh. Hãy chụp lại rõ hơn hoặc tự nhập số.",
    "AI ตอบกลับในรูปแบบที่ไม่คาดคิด ลองใหม่อีกครั้ง หรือพิมพ์ตัวเลขเอง": "AI trả lời sai định dạng dự kiến. Hãy thử lại hoặc tự nhập số.",
    "AI มั่นใจสูง": "Độ tin cậy của AI: cao",
    "AI มั่นใจปานกลาง": "Độ tin cậy của AI: trung bình",
    "AI มั่นใจต่ำ — ตรวจให้ละเอียด": "Độ tin cậy của AI: thấp — hãy kiểm tra kỹ",
    "ค่าไฟ": "Tiền điện",
    "ค่าไฟรอบนี้ (ประมาณการ)": "Kỳ này (ước tính)",
    "ถ่ายรูปบิล": "Chụp ảnh hóa đơn",
    "เลือกรูป": "Chọn ảnh",
    "รูปบิล": "Ảnh hóa đơn",
    "กำลังอ่านบิล…": "Đang đọc hóa đơn…",
    "ถ่ายหรือลากรูปบิลมาวางที่นี่": "Chụp ảnh hoặc kéo ảnh hóa đơn vào đây",
    "AI จะอ่านวันที่ หน่วย และยอดเงินให้อัตโนมัติ คุณตรวจแก้ได้ก่อนบันทึก": "AI sẽ đọc ngày, số điện và số tiền cho bạn; bạn có thể kiểm tra và sửa trước khi lưu.",
    "เช่น บิลเดือน ต.ค.": "vd. hóa đơn tháng 10",
    "บันทึกบิล": "Lưu hóa đơn",
    "รายละเอียดเพิ่มเติม (ไม่บังคับ)": "Chi tiết thêm (không bắt buộc)",
    "วันเริ่มต้นรอบบิล": "Ngày bắt đầu kỳ",
    "ค่าไฟฟ้าฐาน / ค่าพลังงานไฟฟ้า": "Tiền điện năng",
    "บาท": "{cur}",
    "ค่าไฟฟ้าผันแปร (Ft)": "Phụ thu theo kWh (Ft)",
    "ค่าบริการรายเดือน": "Phí dịch vụ hằng tháng",
    "ภาษีมูลค่าเพิ่ม 7%": "Thuế / VAT",
    "หมายเหตุ": "Ghi chú",
    "เพิ่มบิลใหม่": "Thêm hóa đơn mới",
    "ถ่ายรูปบิลหรือพิมพ์ตัวเลขเองก็ได้ วันตัดรอบขยับได้ตามบิลจริง": "Chụp hóa đơn hoặc tự nhập số. Ngày chốt có thể theo hóa đơn thực tế.",
    "วันสิ้นสุดรอบบิล": "Ngày kết thúc kỳ",
    "จำนวนหน่วยที่ใช้": "Số điện đã dùng",
    "ยอดเงินรวมทั้งสิ้น": "Tổng số tiền",
    "อัตราค่าไฟจริงต่อหน่วย": "Đơn giá thực tế mỗi số",
    "แนวโน้มค่าไฟรายรอบบิล": "Xu hướng hóa đơn",
    "ประวัติบิล": "Lịch sử hóa đơn",
    "ส่งออกเป็นไฟล์ CSV": "Xuất ra tệp CSV",
    "บิลที่บันทึกไว้ เรียงจากล่าสุด (กดที่แถวเพื่อดูรายละเอียด)": "Hóa đơn đã lưu, mới nhất trước (chạm vào dòng để xem chi tiết)",
    "ตั้งจุดเริ่มนับ": "Đặt mốc bắt đầu",
    "ขั้นสูง: ตั้งจุดเริ่มนับของมิเตอร์": "Nâng cao: đặt mốc bắt đầu của công tơ",
    "หน่วยรอบนี้ = ค่ามิเตอร์ปัจจุบัน − จุดเริ่มนับ ใส่ 0 ถ้าตัวนับเพิ่งเริ่มนับจาก 0 และอยากให้ยอดสะสมทั้งหมดเป็นของรอบนี้": "Điện kỳ này = số công tơ hiện tại − mốc bắt đầu. Nhập 0 nếu bộ đếm vừa bắt đầu từ 0 và muốn tính toàn bộ vào kỳ này.",
    "มิเตอร์": "Công tơ",
    "ค่าจุดเริ่มนับ": "Giá trị mốc",
    "กดอีกครั้งเพื่อยืนยัน": "Nhấn lần nữa để xác nhận",
    "ตั้งจุดเริ่มนับแล้ว": "Đã đặt mốc bắt đầu",
    "ตั้งไม่สำเร็จ: ": "Không đặt được: ",
    "฿ ": "฿ ",
    " หน่วย": " kWh",
    "ยังไม่มีข้อมูลหน่วย": "Chưa có dữ liệu điện năng",
    " · ผ่านมา ": " · đã qua ",
    " วัน": " ngày",
    " บาท/หน่วย": " {cur}/kWh",
    "อัตราจากบิลจริง": "Đơn giá từ hóa đơn thực",
    "ใช้อัตราสำรอง (ยังไม่มีบิล)": "Đang dùng đơn giá dự phòng (chưa có hóa đơn)",
    " (ตัดรอบ ": " (ngày chốt ",
    "คาดการณ์ถึงวันตัดรอบ ≈ ฿": "Dự báo đến ngày chốt ≈ ฿",
    "คาดการณ์ 30 วัน ≈ ฿": "Dự báo 30 ngày ≈ ฿",
    "ไฟรอบนี้ที่ไม่มีมิเตอร์ย่อย": "Điện chưa đo kỳ này",
    "ยอดบิลล่าสุด": "Số tiền hóa đơn gần nhất",
    "หน่วยตามบิลล่าสุด": "Số điện hóa đơn gần nhất",
    "ไฟที่ไม่ได้วัด": "Điện không đo được",
    "kWh · วัดได้ ": "kWh · đo được ",
    "ยังไม่มีบิลที่บันทึก": "Chưa có hóa đơn nào được lưu",
    "ถ่ายรูปบิลใบแรกได้เลย": "Hãy chụp hóa đơn đầu tiên để bắt đầu",
    "ลบบิลนี้": "Xóa hóa đơn này",
    "ยืนยันลบ": "Xác nhận xóa",
    "หน่วย/วัน": "kWh/ngày",
    "บาท/วัน": "{cur}/ngày",
    "฿": "฿",
    "ยอดเงิน vs ก่อนหน้า": "Số tiền so với trước",
    "หน่วย vs ก่อนหน้า": "Số điện so với trước",
    "รายละเอียดรายการค่าไฟ": "Chi tiết hóa đơn",
    "ผลรวมรายการไม่ตรงกับยอดรวม": "Tổng các khoản không khớp với tổng cộng",
    "แก้ไขบิลนี้": "Sửa hóa đơn này",
    "แก้ไข": "Sửa",
    "ต้องมีบิลอย่างน้อย 2 รอบเพื่อแสดงกราฟ": "Cần ít nhất 2 hóa đơn để hiển thị biểu đồ",
    "กราฟยอดบิลและหน่วยไฟรายรอบบิล": "Biểu đồ số tiền và điện năng theo kỳ hóa đơn",
    "ยอดบิล (บาท)": "Số tiền hóa đơn ({cur})",
    "หน่วยไฟ (สูงสุด ": "Điện năng (tối đa ",
    "ยังไม่มีบิลให้ส่งออก": "Chưa có hóa đơn để xuất",
    "ส่งออก ": "Đã xuất ",
    " บิลเป็น CSV แล้ว": " hóa đơn ra CSV",
    " กำลังแก้ไขบิลวันที่ ": " Đang sửa hóa đơn ngày ",
    " (เปลี่ยนวันสิ้นสุดรอบบิลไม่ได้ ถ้าจะเปลี่ยนให้ลบแล้วเพิ่มใหม่)": " (không đổi được ngày kết thúc kỳ; hãy xóa rồi thêm lại để đổi)",
    "ยกเลิก": "Hủy",
    " บาท": " {cur}",
    "สแกนไม่สำเร็จ (": "Quét không thành công (",
    ") พิมพ์ตัวเลขเองได้": "). Bạn có thể tự nhập số.",
    "คำเตือน: ": "Cảnh báo: ",
    "มีบิลของวันที่นี้อยู่แล้ว ต้องการแทนที่หรือไม่?": "Đã có hóa đơn cho ngày này. Thay thế?",
    "แทนที่": "Thay thế",
    "บันทึกบิลแล้ว · อัตรา ": "Đã lưu hóa đơn · đơn giá ",
    "บันทึกไม่สำเร็จ: ": "Không lưu được: ",
    "ลบบิลแล้ว": "Đã xóa hóa đơn",
    "ลบไม่สำเร็จ: ": "Không xóa được: ",
    "วันสิ้นสุดรอบบิล: ": "Ngày kết thúc kỳ: ",
    "ยังไม่ได้ตั้งค่า AI — ไปที่ Settings → Devices & services → Add integration → Anthropic แล้วใส่ API key ระหว่างนี้พิมพ์ตัวเลขเองได้": "Chưa thiết lập AI — vào Settings → Devices & services → Add integration → Anthropic rồi nhập API key. Trong lúc này bạn có thể tự nhập số."
  },
  ms: {
    "ใช้ไฟวันนี้": "Hari ini",
    " · เมื่อวาน ": " · semalam ",
    "เทียบรอบก่อน ": "berbanding kitaran lalu ",
    "ใช้ไฟรายเครื่อง (รอบนี้)": "Tenaga mengikut peranti (kitaran ini)",
    "ยังไม่มีข้อมูลรายเครื่อง": "Belum ada data mengikut peranti",
    "ใช้ไฟรายวัน (รอบนี้)": "Penggunaan harian (kitaran ini)",
    "ยังไม่มีสถิติรายวัน มิเตอร์เพิ่งเริ่มบันทึก": "Belum ada statistik harian: meter baru mula merekod",
    "อ่านสถิติรายวันไม่สำเร็จ": "Tidak dapat membaca statistik harian",
    "เฉลี่ย ": "Purata ",
    "รวม ": "Jumlah ",
    "วันนี้": "Hari ini",
    "อัตราค่าไฟต่อหน่วยดูผิดปกติ (นอกช่วง 1.5 – 12 บาท) ตรวจตัวเลขอีกครั้ง": "Kadar seunit kelihatan luar biasa (di luar 1.5 – 12). Sila semak angka.",
    "วันที่สิ้นสุดรอบบิลเป็นวันในอนาคต กรุณาตรวจวันที่": "Tarikh akhir tempoh berada pada masa hadapan. Sila semak tarikh.",
    "วันเริ่มต้นรอบบิลต้องไม่เกินวันสิ้นสุดรอบบิล": "Tarikh mula tempoh tidak boleh selepas tarikh akhir.",
    "จำนวนหน่วยอยู่นอกช่วงปกติ (1 – 5,000 kWh)": "Bilangan unit di luar julat biasa (1 – 5,000 kWh).",
    "ยอดเงินอยู่นอกช่วงปกติ (1 – 100,000 บาท)": "Jumlah wang di luar julat biasa (1 – 100,000).",
    "ไฟล์รูปใหญ่เกิน 8 MB": "Imej lebih besar daripada 8 MB.",
    "รองรับเฉพาะไฟล์ JPEG, PNG หรือ WebP": "Hanya imej JPEG, PNG atau WebP disokong.",
    "AI อ่านรูปไม่สำเร็จ ลองถ่ายใหม่ให้ชัดขึ้น หรือพิมพ์ตัวเลขเอง": "AI tidak dapat membaca foto. Cuba foto yang lebih jelas atau taip angka sendiri.",
    "AI ตอบกลับในรูปแบบที่ไม่คาดคิด ลองใหม่อีกครั้ง หรือพิมพ์ตัวเลขเอง": "AI membalas dalam format yang tidak dijangka. Cuba lagi atau taip angka sendiri.",
    "AI มั่นใจสูง": "Keyakinan AI: tinggi",
    "AI มั่นใจปานกลาง": "Keyakinan AI: sederhana",
    "AI มั่นใจต่ำ — ตรวจให้ละเอียด": "Keyakinan AI: rendah — semak dengan teliti",
    "ค่าไฟ": "Elektrik",
    "ค่าไฟรอบนี้ (ประมาณการ)": "Kitaran ini (anggaran)",
    "ถ่ายรูปบิล": "Ambil foto",
    "เลือกรูป": "Pilih imej",
    "รูปบิล": "Foto bil",
    "กำลังอ่านบิล…": "Membaca bil…",
    "ถ่ายหรือลากรูปบิลมาวางที่นี่": "Ambil foto atau lepaskan imej bil di sini",
    "AI จะอ่านวันที่ หน่วย และยอดเงินให้อัตโนมัติ คุณตรวจแก้ได้ก่อนบันทึก": "AI membaca tarikh, unit dan jumlah untuk anda; anda boleh menyemak dan mengedit sebelum menyimpan.",
    "เช่น บิลเดือน ต.ค.": "cth. bil Oktober",
    "บันทึกบิล": "Simpan bil",
    "รายละเอียดเพิ่มเติม (ไม่บังคับ)": "Butiran lanjut (pilihan)",
    "วันเริ่มต้นรอบบิล": "Tarikh mula tempoh",
    "ค่าไฟฟ้าฐาน / ค่าพลังงานไฟฟ้า": "Caj tenaga",
    "บาท": "{cur}",
    "ค่าไฟฟ้าผันแปร (Ft)": "Tambahan per kWh (Ft)",
    "ค่าบริการรายเดือน": "Caj perkhidmatan bulanan",
    "ภาษีมูลค่าเพิ่ม 7%": "Cukai / VAT",
    "หมายเหตุ": "Nota",
    "เพิ่มบิลใหม่": "Tambah bil baharu",
    "ถ่ายรูปบิลหรือพิมพ์ตัวเลขเองก็ได้ วันตัดรอบขยับได้ตามบิลจริง": "Ambil foto bil atau taip angka. Hari bil boleh mengikut bil sebenar anda.",
    "วันสิ้นสุดรอบบิล": "Tarikh akhir tempoh",
    "จำนวนหน่วยที่ใช้": "Unit digunakan",
    "ยอดเงินรวมทั้งสิ้น": "Jumlah keseluruhan",
    "อัตราค่าไฟจริงต่อหน่วย": "Kadar sebenar seunit",
    "แนวโน้มค่าไฟรายรอบบิล": "Aliran bil",
    "ประวัติบิล": "Sejarah bil",
    "ส่งออกเป็นไฟล์ CSV": "Eksport sebagai CSV",
    "บิลที่บันทึกไว้ เรียงจากล่าสุด (กดที่แถวเพื่อดูรายละเอียด)": "Bil tersimpan, terbaharu dahulu (ketik baris untuk butiran)",
    "ตั้งจุดเริ่มนับ": "Tetapkan garis asas",
    "ขั้นสูง: ตั้งจุดเริ่มนับของมิเตอร์": "Lanjutan: tetapkan garis asas meter",
    "หน่วยรอบนี้ = ค่ามิเตอร์ปัจจุบัน − จุดเริ่มนับ ใส่ 0 ถ้าตัวนับเพิ่งเริ่มนับจาก 0 และอยากให้ยอดสะสมทั้งหมดเป็นของรอบนี้": "Tenaga kitaran = nilai meter semasa − garis asas. Masukkan 0 jika pembilang baru bermula dari 0 dan jumlahnya perlu dikira dalam kitaran ini.",
    "มิเตอร์": "Meter",
    "ค่าจุดเริ่มนับ": "Nilai garis asas",
    "กดอีกครั้งเพื่อยืนยัน": "Tekan sekali lagi untuk mengesahkan",
    "ตั้งจุดเริ่มนับแล้ว": "Garis asas ditetapkan",
    "ตั้งไม่สำเร็จ: ": "Tidak dapat menetapkan: ",
    "฿ ": "฿ ",
    " หน่วย": " kWh",
    "ยังไม่มีข้อมูลหน่วย": "Belum ada data tenaga",
    " · ผ่านมา ": " · berlalu ",
    " วัน": " hari",
    " บาท/หน่วย": " {cur}/kWh",
    "อัตราจากบิลจริง": "Kadar daripada bil sebenar",
    "ใช้อัตราสำรอง (ยังไม่มีบิล)": "Menggunakan kadar sandaran (belum ada bil)",
    " (ตัดรอบ ": " (hari bil ",
    "คาดการณ์ถึงวันตัดรอบ ≈ ฿": "Ramalan hingga hari bil ≈ ฿",
    "คาดการณ์ 30 วัน ≈ ฿": "Ramalan 30 hari ≈ ฿",
    "ไฟรอบนี้ที่ไม่มีมิเตอร์ย่อย": "Tanpa meter kitaran ini",
    "ยอดบิลล่าสุด": "Jumlah bil terakhir",
    "หน่วยตามบิลล่าสุด": "Unit bil terakhir",
    "ไฟที่ไม่ได้วัด": "Tenaga tanpa meter",
    "kWh · วัดได้ ": "kWh · diukur ",
    "ยังไม่มีบิลที่บันทึก": "Belum ada bil disimpan",
    "ถ่ายรูปบิลใบแรกได้เลย": "Ambil foto bil pertama anda untuk bermula",
    "ลบบิลนี้": "Padam bil ini",
    "ยืนยันลบ": "Sahkan padam",
    "หน่วย/วัน": "kWh/hari",
    "บาท/วัน": "{cur}/hari",
    "฿": "฿",
    "ยอดเงิน vs ก่อนหน้า": "Jumlah berbanding sebelumnya",
    "หน่วย vs ก่อนหน้า": "Unit berbanding sebelumnya",
    "รายละเอียดรายการค่าไฟ": "Pecahan bil",
    "ผลรวมรายการไม่ตรงกับยอดรวม": "Jumlah butiran tidak sepadan dengan jumlah keseluruhan",
    "แก้ไขบิลนี้": "Edit bil ini",
    "แก้ไข": "Edit",
    "ต้องมีบิลอย่างน้อย 2 รอบเพื่อแสดงกราฟ": "Sekurang-kurangnya 2 bil diperlukan untuk memaparkan carta",
    "กราฟยอดบิลและหน่วยไฟรายรอบบิล": "Carta jumlah bil dan tenaga bagi setiap tempoh bil",
    "ยอดบิล (บาท)": "Jumlah bil ({cur})",
    "หน่วยไฟ (สูงสุด ": "Tenaga (maks ",
    "ยังไม่มีบิลให้ส่งออก": "Tiada bil untuk dieksport",
    "ส่งออก ": "Dieksport ",
    " บิลเป็น CSV แล้ว": " bil ke CSV",
    " กำลังแก้ไขบิลวันที่ ": " Mengedit bil bertarikh ",
    " (เปลี่ยนวันสิ้นสุดรอบบิลไม่ได้ ถ้าจะเปลี่ยนให้ลบแล้วเพิ่มใหม่)": " (tarikh akhir tempoh tidak boleh diubah; padam dan tambah semula untuk mengubahnya)",
    "ยกเลิก": "Batal",
    " บาท": " {cur}",
    "สแกนไม่สำเร็จ (": "Imbasan gagal (",
    ") พิมพ์ตัวเลขเองได้": "). Anda boleh menaip angka sendiri.",
    "คำเตือน: ": "Amaran: ",
    "มีบิลของวันที่นี้อยู่แล้ว ต้องการแทนที่หรือไม่?": "Bil untuk tarikh ini sudah wujud. Ganti?",
    "แทนที่": "Ganti",
    "บันทึกบิลแล้ว · อัตรา ": "Bil disimpan · kadar ",
    "บันทึกไม่สำเร็จ: ": "Tidak dapat menyimpan: ",
    "ลบบิลแล้ว": "Bil dipadam",
    "ลบไม่สำเร็จ: ": "Tidak dapat memadam: ",
    "วันสิ้นสุดรอบบิล: ": "Akhir tempoh: ",
    "ยังไม่ได้ตั้งค่า AI — ไปที่ Settings → Devices & services → Add integration → Anthropic แล้วใส่ API key ระหว่างนี้พิมพ์ตัวเลขเองได้": "AI belum disediakan — pergi ke Settings → Devices & services → Add integration → Anthropic dan masukkan kunci API. Sementara itu anda boleh menaip angka sendiri."
  },
  id: {
    "ใช้ไฟวันนี้": "Hari ini",
    " · เมื่อวาน ": " · kemarin ",
    "เทียบรอบก่อน ": "dibanding siklus lalu ",
    "ใช้ไฟรายเครื่อง (รอบนี้)": "Energi per perangkat (siklus ini)",
    "ยังไม่มีข้อมูลรายเครื่อง": "Belum ada data per perangkat",
    "ใช้ไฟรายวัน (รอบนี้)": "Pemakaian harian (siklus ini)",
    "ยังไม่มีสถิติรายวัน มิเตอร์เพิ่งเริ่มบันทึก": "Belum ada statistik harian: meter baru mulai merekam",
    "อ่านสถิติรายวันไม่สำเร็จ": "Tidak dapat membaca statistik harian",
    "เฉลี่ย ": "Rata-rata ",
    "รวม ": "Total ",
    "วันนี้": "Hari ini",
    "อัตราค่าไฟต่อหน่วยดูผิดปกติ (นอกช่วง 1.5 – 12 บาท) ตรวจตัวเลขอีกครั้ง": "Tarif per unit tampak tidak wajar (di luar 1,5 – 12). Silakan periksa angkanya.",
    "วันที่สิ้นสุดรอบบิลเป็นวันในอนาคต กรุณาตรวจวันที่": "Tanggal akhir periode ada di masa depan. Silakan periksa tanggalnya.",
    "วันเริ่มต้นรอบบิลต้องไม่เกินวันสิ้นสุดรอบบิล": "Tanggal mulai periode tidak boleh setelah tanggal akhir.",
    "จำนวนหน่วยอยู่นอกช่วงปกติ (1 – 5,000 kWh)": "Jumlah unit di luar rentang wajar (1 – 5.000 kWh).",
    "ยอดเงินอยู่นอกช่วงปกติ (1 – 100,000 บาท)": "Jumlah di luar rentang wajar (1 – 100.000).",
    "ไฟล์รูปใหญ่เกิน 8 MB": "Gambar lebih besar dari 8 MB.",
    "รองรับเฉพาะไฟล์ JPEG, PNG หรือ WebP": "Hanya gambar JPEG, PNG, atau WebP yang didukung.",
    "AI อ่านรูปไม่สำเร็จ ลองถ่ายใหม่ให้ชัดขึ้น หรือพิมพ์ตัวเลขเอง": "AI tidak dapat membaca foto. Coba foto yang lebih jelas atau ketik angkanya sendiri.",
    "AI ตอบกลับในรูปแบบที่ไม่คาดคิด ลองใหม่อีกครั้ง หรือพิมพ์ตัวเลขเอง": "AI membalas dengan format yang tidak terduga. Coba lagi atau ketik angkanya sendiri.",
    "AI มั่นใจสูง": "Keyakinan AI: tinggi",
    "AI มั่นใจปานกลาง": "Keyakinan AI: sedang",
    "AI มั่นใจต่ำ — ตรวจให้ละเอียด": "Keyakinan AI: rendah — periksa dengan teliti",
    "ค่าไฟ": "Listrik",
    "ค่าไฟรอบนี้ (ประมาณการ)": "Siklus ini (perkiraan)",
    "ถ่ายรูปบิล": "Ambil foto",
    "เลือกรูป": "Pilih gambar",
    "รูปบิล": "Foto tagihan",
    "กำลังอ่านบิล…": "Membaca tagihan…",
    "ถ่ายหรือลากรูปบิลมาวางที่นี่": "Ambil foto atau tarik gambar tagihan ke sini",
    "AI จะอ่านวันที่ หน่วย และยอดเงินให้อัตโนมัติ คุณตรวจแก้ได้ก่อนบันทึก": "AI membaca tanggal, unit, dan jumlah untuk Anda; Anda dapat memeriksa dan mengubahnya sebelum menyimpan.",
    "เช่น บิลเดือน ต.ค.": "mis. tagihan Oktober",
    "บันทึกบิล": "Simpan tagihan",
    "รายละเอียดเพิ่มเติม (ไม่บังคับ)": "Detail tambahan (opsional)",
    "วันเริ่มต้นรอบบิล": "Tanggal mulai periode",
    "ค่าไฟฟ้าฐาน / ค่าพลังงานไฟฟ้า": "Biaya energi",
    "บาท": "{cur}",
    "ค่าไฟฟ้าผันแปร (Ft)": "Tambahan per kWh (Ft)",
    "ค่าบริการรายเดือน": "Biaya layanan bulanan",
    "ภาษีมูลค่าเพิ่ม 7%": "Pajak / PPN",
    "หมายเหตุ": "Catatan",
    "เพิ่มบิลใหม่": "Tambah tagihan baru",
    "ถ่ายรูปบิลหรือพิมพ์ตัวเลขเองก็ได้ วันตัดรอบขยับได้ตามบิลจริง": "Foto tagihan atau ketik angkanya. Tanggal tutup buku dapat mengikuti tagihan sebenarnya.",
    "วันสิ้นสุดรอบบิล": "Tanggal akhir periode",
    "จำนวนหน่วยที่ใช้": "Unit terpakai",
    "ยอดเงินรวมทั้งสิ้น": "Jumlah total",
    "อัตราค่าไฟจริงต่อหน่วย": "Tarif riil per unit",
    "แนวโน้มค่าไฟรายรอบบิล": "Tren tagihan",
    "ประวัติบิล": "Riwayat tagihan",
    "ส่งออกเป็นไฟล์ CSV": "Ekspor sebagai CSV",
    "บิลที่บันทึกไว้ เรียงจากล่าสุด (กดที่แถวเพื่อดูรายละเอียด)": "Tagihan tersimpan, terbaru dulu (ketuk baris untuk detail)",
    "ตั้งจุดเริ่มนับ": "Setel titik awal",
    "ขั้นสูง: ตั้งจุดเริ่มนับของมิเตอร์": "Lanjutan: setel titik awal meter",
    "หน่วยรอบนี้ = ค่ามิเตอร์ปัจจุบัน − จุดเริ่มนับ ใส่ 0 ถ้าตัวนับเพิ่งเริ่มนับจาก 0 และอยากให้ยอดสะสมทั้งหมดเป็นของรอบนี้": "Energi siklus = nilai meter saat ini − titik awal. Isi 0 jika penghitung baru mulai dari 0 dan seluruh totalnya harus dihitung di siklus ini.",
    "มิเตอร์": "Meter",
    "ค่าจุดเริ่มนับ": "Nilai titik awal",
    "กดอีกครั้งเพื่อยืนยัน": "Tekan lagi untuk konfirmasi",
    "ตั้งจุดเริ่มนับแล้ว": "Titik awal disetel",
    "ตั้งไม่สำเร็จ: ": "Tidak dapat menyetel: ",
    "฿ ": "฿ ",
    " หน่วย": " kWh",
    "ยังไม่มีข้อมูลหน่วย": "Belum ada data energi",
    " · ผ่านมา ": " · berjalan ",
    " วัน": " hari",
    " บาท/หน่วย": " {cur}/kWh",
    "อัตราจากบิลจริง": "Tarif dari tagihan nyata",
    "ใช้อัตราสำรอง (ยังไม่มีบิล)": "Memakai tarif cadangan (belum ada tagihan)",
    " (ตัดรอบ ": " (tanggal tutup ",
    "คาดการณ์ถึงวันตัดรอบ ≈ ฿": "Perkiraan hingga tanggal tutup ≈ ฿",
    "คาดการณ์ 30 วัน ≈ ฿": "Perkiraan 30 hari ≈ ฿",
    "ไฟรอบนี้ที่ไม่มีมิเตอร์ย่อย": "Tanpa meter siklus ini",
    "ยอดบิลล่าสุด": "Jumlah tagihan terakhir",
    "หน่วยตามบิลล่าสุด": "Unit tagihan terakhir",
    "ไฟที่ไม่ได้วัด": "Energi tanpa meter",
    "kWh · วัดได้ ": "kWh · terukur ",
    "ยังไม่มีบิลที่บันทึก": "Belum ada tagihan tersimpan",
    "ถ่ายรูปบิลใบแรกได้เลย": "Foto tagihan pertama Anda untuk memulai",
    "ลบบิลนี้": "Hapus tagihan ini",
    "ยืนยันลบ": "Konfirmasi hapus",
    "หน่วย/วัน": "kWh/hari",
    "บาท/วัน": "{cur}/hari",
    "฿": "฿",
    "ยอดเงิน vs ก่อนหน้า": "Jumlah dibanding sebelumnya",
    "หน่วย vs ก่อนหน้า": "Unit dibanding sebelumnya",
    "รายละเอียดรายการค่าไฟ": "Rincian tagihan",
    "ผลรวมรายการไม่ตรงกับยอดรวม": "Jumlah rincian tidak sesuai dengan total",
    "แก้ไขบิลนี้": "Ubah tagihan ini",
    "แก้ไข": "Ubah",
    "ต้องมีบิลอย่างน้อย 2 รอบเพื่อแสดงกราฟ": "Minimal 2 tagihan diperlukan untuk menampilkan grafik",
    "กราฟยอดบิลและหน่วยไฟรายรอบบิล": "Grafik jumlah tagihan dan energi per periode tagihan",
    "ยอดบิล (บาท)": "Jumlah tagihan ({cur})",
    "หน่วยไฟ (สูงสุด ": "Energi (maks ",
    "ยังไม่มีบิลให้ส่งออก": "Tidak ada tagihan untuk diekspor",
    "ส่งออก ": "Diekspor ",
    " บิลเป็น CSV แล้ว": " tagihan ke CSV",
    " กำลังแก้ไขบิลวันที่ ": " Mengubah tagihan tanggal ",
    " (เปลี่ยนวันสิ้นสุดรอบบิลไม่ได้ ถ้าจะเปลี่ยนให้ลบแล้วเพิ่มใหม่)": " (tanggal akhir periode tidak dapat diubah; hapus lalu tambah lagi untuk mengubahnya)",
    "ยกเลิก": "Batal",
    " บาท": " {cur}",
    "สแกนไม่สำเร็จ (": "Pemindaian gagal (",
    ") พิมพ์ตัวเลขเองได้": "). Anda dapat mengetik angkanya sendiri.",
    "คำเตือน: ": "Peringatan: ",
    "มีบิลของวันที่นี้อยู่แล้ว ต้องการแทนที่หรือไม่?": "Tagihan untuk tanggal ini sudah ada. Gantikan?",
    "แทนที่": "Ganti",
    "บันทึกบิลแล้ว · อัตรา ": "Tagihan disimpan · tarif ",
    "บันทึกไม่สำเร็จ: ": "Tidak dapat menyimpan: ",
    "ลบบิลแล้ว": "Tagihan dihapus",
    "ลบไม่สำเร็จ: ": "Tidak dapat menghapus: ",
    "วันสิ้นสุดรอบบิล: ": "Akhir periode: ",
    "ยังไม่ได้ตั้งค่า AI — ไปที่ Settings → Devices & services → Add integration → Anthropic แล้วใส่ API key ระหว่างนี้พิมพ์ตัวเลขเองได้": "AI belum diatur — buka Settings → Devices & services → Add integration → Anthropic lalu masukkan kunci API. Sementara itu Anda dapat mengetik angkanya sendiri."
  },
  ru: {
    "ใช้ไฟวันนี้": "Сегодня",
    " · เมื่อวาน ": " · вчера ",
    "เทียบรอบก่อน ": "к прошлому периоду ",
    "ใช้ไฟรายเครื่อง (รอบนี้)": "Энергия по устройствам (текущий период)",
    "ยังไม่มีข้อมูลรายเครื่อง": "Данных по устройствам пока нет",
    "ใช้ไฟรายวัน (รอบนี้)": "Потребление по дням (текущий период)",
    "ยังไม่มีสถิติรายวัน มิเตอร์เพิ่งเริ่มบันทึก": "Статистики по дням пока нет: счётчик только начал запись",
    "อ่านสถิติรายวันไม่สำเร็จ": "Не удалось прочитать статистику по дням",
    "เฉลี่ย ": "Сред. ",
    "รวม ": "Всего ",
    "วันนี้": "Сегодня",
    "อัตราค่าไฟต่อหน่วยดูผิดปกติ (นอกช่วง 1.5 – 12 บาท) ตรวจตัวเลขอีกครั้ง": "Тариф за единицу выглядит необычно (вне диапазона 1,5 – 12). Проверьте числа.",
    "วันที่สิ้นสุดรอบบิลเป็นวันในอนาคต กรุณาตรวจวันที่": "Дата окончания периода в будущем. Проверьте дату.",
    "วันเริ่มต้นรอบบิลต้องไม่เกินวันสิ้นสุดรอบบิล": "Дата начала периода не может быть позже даты окончания.",
    "จำนวนหน่วยอยู่นอกช่วงปกติ (1 – 5,000 kWh)": "Количество единиц вне обычного диапазона (1 – 5 000 кВт·ч).",
    "ยอดเงินอยู่นอกช่วงปกติ (1 – 100,000 บาท)": "Сумма вне обычного диапазона (1 – 100 000).",
    "ไฟล์รูปใหญ่เกิน 8 MB": "Изображение больше 8 МБ.",
    "รองรับเฉพาะไฟล์ JPEG, PNG หรือ WebP": "Поддерживаются только изображения JPEG, PNG и WebP.",
    "AI อ่านรูปไม่สำเร็จ ลองถ่ายใหม่ให้ชัดขึ้น หรือพิมพ์ตัวเลขเอง": "ИИ не смог прочитать фото. Сфотографируйте чётче или введите числа вручную.",
    "AI ตอบกลับในรูปแบบที่ไม่คาดคิด ลองใหม่อีกครั้ง หรือพิมพ์ตัวเลขเอง": "ИИ ответил в неожиданном формате. Повторите попытку или введите числа вручную.",
    "AI มั่นใจสูง": "Уверенность ИИ: высокая",
    "AI มั่นใจปานกลาง": "Уверенность ИИ: средняя",
    "AI มั่นใจต่ำ — ตรวจให้ละเอียด": "Уверенность ИИ: низкая — проверьте внимательно",
    "ค่าไฟ": "Электричество",
    "ค่าไฟรอบนี้ (ประมาณการ)": "Текущий период (оценка)",
    "ถ่ายรูปบิล": "Сфотографировать",
    "เลือกรูป": "Выбрать изображение",
    "รูปบิล": "Фото счёта",
    "กำลังอ่านบิล…": "Чтение счёта…",
    "ถ่ายหรือลากรูปบิลมาวางที่นี่": "Сфотографируйте или перетащите изображение счёта сюда",
    "AI จะอ่านวันที่ หน่วย และยอดเงินให้อัตโนมัติ คุณตรวจแก้ได้ก่อนบันทึก": "ИИ считает дату, единицы и сумму; перед сохранением их можно проверить и исправить.",
    "เช่น บิลเดือน ต.ค.": "напр. счёт за октябрь",
    "บันทึกบิล": "Сохранить счёт",
    "รายละเอียดเพิ่มเติม (ไม่บังคับ)": "Дополнительно (необязательно)",
    "วันเริ่มต้นรอบบิล": "Дата начала периода",
    "ค่าไฟฟ้าฐาน / ค่าพลังงานไฟฟ้า": "Плата за энергию",
    "บาท": "{cur}",
    "ค่าไฟฟ้าผันแปร (Ft)": "Надбавка за кВт·ч (Ft)",
    "ค่าบริการรายเดือน": "Ежемесячная плата за обслуживание",
    "ภาษีมูลค่าเพิ่ม 7%": "Налог / НДС",
    "หมายเหตุ": "Заметка",
    "เพิ่มบิลใหม่": "Добавить новый счёт",
    "ถ่ายรูปบิลหรือพิมพ์ตัวเลขเองก็ได้ วันตัดรอบขยับได้ตามบิลจริง": "Сфотографируйте счёт или введите числа. День расчёта может следовать вашему реальному счёту.",
    "วันสิ้นสุดรอบบิล": "Дата окончания периода",
    "จำนวนหน่วยที่ใช้": "Использовано единиц",
    "ยอดเงินรวมทั้งสิ้น": "Итоговая сумма",
    "อัตราค่าไฟจริงต่อหน่วย": "Фактический тариф за единицу",
    "แนวโน้มค่าไฟรายรอบบิล": "Динамика счетов",
    "ประวัติบิล": "История счетов",
    "ส่งออกเป็นไฟล์ CSV": "Экспорт в CSV",
    "บิลที่บันทึกไว้ เรียงจากล่าสุด (กดที่แถวเพื่อดูรายละเอียด)": "Сохранённые счета, новые сверху (нажмите строку для подробностей)",
    "ตั้งจุดเริ่มนับ": "Задать начальное значение",
    "ขั้นสูง: ตั้งจุดเริ่มนับของมิเตอร์": "Дополнительно: начальное значение счётчика",
    "หน่วยรอบนี้ = ค่ามิเตอร์ปัจจุบัน − จุดเริ่มนับ ใส่ 0 ถ้าตัวนับเพิ่งเริ่มนับจาก 0 และอยากให้ยอดสะสมทั้งหมดเป็นของรอบนี้": "Энергия периода = текущее показание − начальное значение. Введите 0, если счётчик только что начал с 0 и весь итог нужно учесть в этом периоде.",
    "มิเตอร์": "Счётчик",
    "ค่าจุดเริ่มนับ": "Начальное значение",
    "กดอีกครั้งเพื่อยืนยัน": "Нажмите ещё раз для подтверждения",
    "ตั้งจุดเริ่มนับแล้ว": "Начальное значение задано",
    "ตั้งไม่สำเร็จ: ": "Не удалось задать: ",
    "฿ ": "฿ ",
    " หน่วย": " кВт·ч",
    "ยังไม่มีข้อมูลหน่วย": "Данных об энергии пока нет",
    " · ผ่านมา ": " · прошло ",
    " วัน": " дн.",
    " บาท/หน่วย": " {cur}/кВт·ч",
    "อัตราจากบิลจริง": "Тариф из реального счёта",
    "ใช้อัตราสำรอง (ยังไม่มีบิล)": "Используется резервный тариф (счетов пока нет)",
    " (ตัดรอบ ": " (день расчёта ",
    "คาดการณ์ถึงวันตัดรอบ ≈ ฿": "Прогноз до дня расчёта ≈ ฿",
    "คาดการณ์ 30 วัน ≈ ฿": "Прогноз на 30 дней ≈ ฿",
    "ไฟรอบนี้ที่ไม่มีมิเตอร์ย่อย": "Без счётчиков в этом периоде",
    "ยอดบิลล่าสุด": "Сумма последнего счёта",
    "หน่วยตามบิลล่าสุด": "Единицы последнего счёта",
    "ไฟที่ไม่ได้วัด": "Неучтённая энергия",
    "kWh · วัดได้ ": "кВт·ч · измерено ",
    "ยังไม่มีบิลที่บันทึก": "Сохранённых счетов пока нет",
    "ถ่ายรูปบิลใบแรกได้เลย": "Сфотографируйте первый счёт, чтобы начать",
    "ลบบิลนี้": "Удалить этот счёт",
    "ยืนยันลบ": "Подтвердить удаление",
    "หน่วย/วัน": "кВт·ч/дн.",
    "บาท/วัน": "{cur}/дн.",
    "฿": "฿",
    "ยอดเงิน vs ก่อนหน้า": "Сумма к предыдущему",
    "หน่วย vs ก่อนหน้า": "Единицы к предыдущему",
    "รายละเอียดรายการค่าไฟ": "Состав счёта",
    "ผลรวมรายการไม่ตรงกับยอดรวม": "Сумма позиций не совпадает с итогом",
    "แก้ไขบิลนี้": "Изменить этот счёт",
    "แก้ไข": "Изменить",
    "ต้องมีบิลอย่างน้อย 2 รอบเพื่อแสดงกราฟ": "Для графика нужно минимум 2 счёта",
    "กราฟยอดบิลและหน่วยไฟรายรอบบิล": "График суммы счёта и энергии по периодам",
    "ยอดบิล (บาท)": "Сумма счёта ({cur})",
    "หน่วยไฟ (สูงสุด ": "Энергия (макс. ",
    "ยังไม่มีบิลให้ส่งออก": "Нет счетов для экспорта",
    "ส่งออก ": "Экспортировано ",
    " บิลเป็น CSV แล้ว": " счетов в CSV",
    " กำลังแก้ไขบิลวันที่ ": " Редактирование счёта от ",
    " (เปลี่ยนวันสิ้นสุดรอบบิลไม่ได้ ถ้าจะเปลี่ยนให้ลบแล้วเพิ่มใหม่)": " (дату окончания периода изменить нельзя; удалите и добавьте заново)",
    "ยกเลิก": "Отмена",
    " บาท": " {cur}",
    "สแกนไม่สำเร็จ (": "Сканирование не удалось (",
    ") พิมพ์ตัวเลขเองได้": "). Числа можно ввести вручную.",
    "คำเตือน: ": "Предупреждение: ",
    "มีบิลของวันที่นี้อยู่แล้ว ต้องการแทนที่หรือไม่?": "Счёт на эту дату уже существует. Заменить?",
    "แทนที่": "Заменить",
    "บันทึกบิลแล้ว · อัตรา ": "Счёт сохранён · тариф ",
    "บันทึกไม่สำเร็จ: ": "Не удалось сохранить: ",
    "ลบบิลแล้ว": "Счёт удалён",
    "ลบไม่สำเร็จ: ": "Не удалось удалить: ",
    "วันสิ้นสุดรอบบิล: ": "Окончание периода: ",
    "ยังไม่ได้ตั้งค่า AI — ไปที่ Settings → Devices & services → Add integration → Anthropic แล้วใส่ API key ระหว่างนี้พิมพ์ตัวเลขเองได้": "ИИ не настроен — откройте Settings → Devices & services → Add integration → Anthropic и введите ключ API. Пока можно вводить числа вручную."
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
  /* ---- design refresh ---- */
  .page, .grid, .tiles { min-width: 0; }
  .page > *, .grid > *, .tiles > * { min-width: 0; }
  .page { grid-template-columns: minmax(0, 1fr); }
  .chart-card svg { max-width: 100%; }
  :host { --eb-ok: var(--success-color, #43a047); --eb-warn: var(--warning-color, #ffa000); --eb-violet: #7c4dff; font-variant-numeric: tabular-nums; }
  .page { gap: 18px; padding-top: 20px; }
  .hero {
    display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: center;
    padding: 26px 28px;
    background:
      radial-gradient(120% 140% at 100% 0%, rgba(255,255,255,.22), rgba(255,255,255,0) 55%),
      linear-gradient(135deg, var(--eb-accent) 0%, var(--eb-accent-2) 100%);
    box-shadow: 0 18px 40px -12px color-mix(in srgb, var(--eb-accent) 55%, transparent), inset 0 1px 0 rgba(255,255,255,.25);
  }
  .hero-main { min-width: 0; }
  .hero-label { text-transform: uppercase; letter-spacing: .08em; font-size: 12px; font-weight: 600; opacity: .85; }
  .hero-value { font-size: clamp(44px, 9vw, 68px); font-weight: 800; letter-spacing: -1.5px; text-shadow: 0 2px 14px rgba(0,0,0,.18); }
  .hero-ring { position: relative; width: 112px; height: 112px; display: none; }
  .hero-ring.show { display: block; }
  .hero-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
  .hero-ring .trk { fill: none; stroke: rgba(255,255,255,.25); stroke-width: 9; }
  .hero-ring .prg { fill: none; stroke: #fff; stroke-width: 9; stroke-linecap: round; transition: stroke-dashoffset .9s cubic-bezier(.2,.8,.2,1); }
  .hero-ring .mid { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; line-height: 1.1; }
  .hero-ring .mid b { font-size: 26px; font-weight: 750; }
  .hero-ring .mid span { font-size: 11px; opacity: .85; margin-top: 2px; }
  .chip { background: rgba(255,255,255,.18); border: 1px solid rgba(255,255,255,.28); }
  .tile { transition: transform .15s, box-shadow .2s, border-color .2s; }
  .tile:hover { transform: translateY(-2px); box-shadow: 0 10px 24px -14px rgba(0,0,0,.45); border-color: color-mix(in srgb, var(--eb-accent) 45%, var(--eb-line)); }
  .tile-ico { width: 46px; height: 46px; border-radius: 14px; }
  .tile:nth-child(4n+2) .tile-ico { background: color-mix(in srgb, var(--eb-ok) 16%, transparent); color: var(--eb-ok); }
  .tile:nth-child(4n+3) .tile-ico { background: color-mix(in srgb, var(--eb-warn) 18%, transparent); color: var(--eb-warn); }
  .tile:nth-child(4n+4) .tile-ico { background: color-mix(in srgb, var(--eb-violet) 16%, transparent); color: var(--eb-violet); }
  .tile-value { font-size: 22px; font-weight: 700; letter-spacing: -.3px; }
  .card { border-radius: 22px; padding: 22px; transition: box-shadow .2s, border-color .2s; }
  .card:hover { border-color: color-mix(in srgb, var(--eb-accent) 30%, var(--eb-line)); }
  .card h2 { font-size: 17px; letter-spacing: -.2px; }
  .card h2 ha-icon { color: var(--eb-accent); background: color-mix(in srgb, var(--eb-accent) 13%, transparent); border-radius: 10px; padding: 5px; --mdc-icon-size: 20px; }
  .chart-card .grid-line { stroke: var(--eb-line); stroke-dasharray: 3 5; stroke-width: 1; }
  .chart-card .bar-rect { fill: url(#ebBar); opacity: 1; transform-box: fill-box; transform-origin: 50% 100%; animation: ebGrow .7s cubic-bezier(.2,.8,.2,1) both; }
  .chart-card .bar-rect:not(.latest) { opacity: .55; }
  .chart-card .kwh-line { stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 1200; animation: ebDraw 1.1s ease-out .15s both; }
  .chart-card .kwh-dot { stroke: var(--eb-card); stroke-width: 2; }
  .chart-card .val { font-weight: 650; font-size: 11.5px; }
  @keyframes ebGrow { from { transform: scaleY(0); } to { transform: scaleY(1); } }
  @keyframes ebDraw { from { stroke-dashoffset: 1200; } to { stroke-dashoffset: 0; } }
  .row-item { border-radius: 14px; transition: background .15s; }
  .row-main:hover { background: var(--eb-soft); }
  .bar { height: 6px; border-radius: 999px; }
  .bar i { border-radius: 999px; background: linear-gradient(90deg, var(--eb-accent), var(--eb-accent-2)); }
  .btn { border-radius: 14px; }
  @media (max-width: 520px) { .hero { grid-template-columns: 1fr; padding: 22px; } .hero-ring { width: 92px; height: 92px; justify-self: start; } .hero-ring .mid b { font-size: 21px; } }
  .stack { display: flex; height: 16px; border-radius: 999px; overflow: hidden; background: var(--eb-soft); margin: 10px 0 14px; }
  .stack i { display: block; height: 100%; transition: width .7s cubic-bezier(.2,.8,.2,1); }
  .dev-row { display: grid; grid-template-columns: 14px 1fr auto auto; gap: 10px; align-items: center; padding: 8px 2px; border-bottom: 1px dashed var(--eb-line); font-size: 14px; }
  .dev-row:last-child { border-bottom: 0; }
  .dev-dot { width: 10px; height: 10px; border-radius: 50%; }
  .dev-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .dev-kwh { font-weight: 650; }
  .dev-pct { color: var(--eb-muted); font-size: 12.5px; min-width: 44px; text-align: right; }
  .daily-card svg { width: 100%; height: auto; display: block; max-width: 100%; }
  .daily-card .d-bar { fill: var(--eb-accent); opacity: .8; transform-box: fill-box; transform-origin: 50% 100%; animation: ebGrow .6s cubic-bezier(.2,.8,.2,1) both; }
  .daily-card .d-bar.today { fill: var(--eb-accent-2); opacity: 1; }
  .daily-card .d-avg { stroke: var(--accent-color, #ff9800); stroke-width: 1.5; stroke-dasharray: 5 4; }
  .daily-card text { fill: var(--secondary-text-color, #888); font-size: 10.5px; font-family: inherit; }
  .daily-card .d-val { fill: var(--primary-text-color, #222); font-weight: 600; }
  .daily-sum { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; color: var(--eb-muted); margin-top: 6px; }
  .daily-sum b { color: var(--primary-text-color, #222); }
  @media (prefers-reduced-motion: reduce) { .chart-card .bar-rect, .chart-card .kwh-line { animation: none; } .hero-ring .prg { transition: none; } }
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
    this._heroRing = el("div", { class: "hero-ring" });
    const hero = el(
      "div",
      { class: "hero" },
      el(
        "div",
        { class: "hero-main" },
        el("div", { class: "hero-label" }, icon("mdi:flash"), T("ค่าไฟรอบนี้ (ประมาณการ)")),
        this._heroValue,
        this._heroSub,
        this._heroChips
      ),
      this._heroRing
    );

    // tiles
    this._tiles = el("div", { class: "tiles" });

    // scan card
    this._cameraInput = el("input", { type: "file", accept: "image/*;capture=camera", capture: "environment", style: "display:none" });
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
    this._breakdown = el("div");
    const breakdownCard = el(
      "div",
      { class: "card" },
      el("h2", {}, icon("mdi:chart-donut"), T("ใช้ไฟรายเครื่อง (รอบนี้)")),
      this._breakdown
    );
    this._daily = el("div");
    this._dailyData = null;
    this._dailyKey = "";
    this._dailyFetchedAt = 0;
    const dailyCard = el(
      "div",
      { class: "card daily-card" },
      el("h2", {}, icon("mdi:calendar-today"), T("ใช้ไฟรายวัน (รอบนี้)")),
      this._daily
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
    root.append(el("div", { class: "page" }, hero, this._tiles, chartCard, el("div", { class: "grid" }, breakdownCard, dailyCard), el("div", { class: "grid" }, addCard, histCard), baseCard), this._toast);
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
      "sensor.electricity_bill_today_energy",
      "sensor.electricity_bill_yesterday_energy",
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
    this._renderBreakdown();
    this._renderDaily();
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

  _renderRing(elapsed, total) {
    this._heroRing.replaceChildren();
    if (!(total > 0) || !(elapsed >= 0)) {
      this._heroRing.classList.remove("show");
      return;
    }
    this._heroRing.classList.add("show");
    const NS = "http://www.w3.org/2000/svg";
    const mk = (tag, attrs) => {
      const n = document.createElementNS(NS, tag);
      for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
      return n;
    };
    const r = 46;
    const c = 2 * Math.PI * r;
    const frac = Math.min(1, elapsed / total);
    const svg = mk("svg", { viewBox: "0 0 112 112" });
    svg.append(mk("circle", { class: "trk", cx: 56, cy: 56, r }));
    svg.append(mk("circle", { class: "prg", cx: 56, cy: 56, r, "stroke-dasharray": c.toFixed(1), "stroke-dashoffset": (c * (1 - frac)).toFixed(1) }));
    const mid = el("div", { class: "mid" }, el("b", { text: Math.round(elapsed) + "/" + Math.round(total) }), el("span", { text: T(" วัน").trim() }));
    this._heroRing.append(svg, mid);
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

    this._renderRing(Number(days), fc ? Number(fc.attributes.cycle_days) : NaN);
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
    const todayS = this._st("sensor.electricity_bill_today_energy");
    const ydayS = this._st("sensor.electricity_bill_yesterday_energy");
    const todayTile = this._hass.states["sensor.electricity_bill_today_energy"]
      ? [
          tile(
            "mdi:calendar-today",
            T("ใช้ไฟวันนี้"),
            todayS ? num(todayS.state, 2) : null,
            "kWh" + (ydayS ? T(" · เมื่อวาน ") + num(ydayS.state, 2) : "")
          ),
        ]
      : [];
    this._tiles.replaceChildren(
      ...todayTile,
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

        const perDev = Object.entries(b.per_source_kwh || {}).filter(([id]) => id !== this._mainMeter()).sort((x, y) => y[1] - x[1]);
        const devBox = perDev.length
          ? el(
              "div",
              { class: "charges-box" },
              el("div", { class: "charges-title", text: T("ใช้ไฟรายเครื่อง (รอบนี้)").replace(/\s*\(.*\)$/, "") }),
              ...perDev.map(([id, kwh]) =>
                el(
                  "div",
                  { class: "charge-row" },
                  el("span", { text: this._nameOf(id) }),
                  el("span", { class: "charge-val", text: num(kwh, 1) + " kWh · " + T("฿") + num(kwh * (Number(b.rate) || 0), 0) })
                )
              )
            )
          : null;
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
        if (devBox) expandedChildren.push(devBox);

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
    const H = 230;
    const padL = 8;
    const padR = 8;
    const padT = 26;
    const padB = 32;
    const plotH = H - padT - padB;
    const maxAmt = Math.max(...bills.map((b) => Number(b.amount) || 0), 1);
    const maxKwh = Math.max(...bills.map((b) => Number(b.kwh) || 0), 1);
    const slot = (W - padL - padR) / bills.length;
    const barW = Math.min(46, slot * 0.6);
    const NS = "http://www.w3.org/2000/svg";
    const svgEl = (tag, attrs, text) => {
      const n = document.createElementNS(NS, tag);
      for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, String(v));
      if (text !== undefined) n.textContent = text;
      return n;
    };
    const svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": T("กราฟยอดบิลและหน่วยไฟรายรอบบิล") });
    const defs = svgEl("defs");
    const grad = svgEl("linearGradient", { id: "ebBar", x1: 0, y1: 0, x2: 0, y2: 1 });
    grad.append(svgEl("stop", { offset: "0%", "stop-color": "var(--eb-accent-2, #7c4dff)" }));
    grad.append(svgEl("stop", { offset: "100%", "stop-color": "var(--eb-accent, #03a9f4)", "stop-opacity": 0.75 }));
    defs.append(grad);
    svg.append(defs);
    for (let g = 0; g <= 3; g++) {
      const y = padT + (plotH * g) / 3;
      svg.append(svgEl("line", { class: "grid-line", x1: padL, x2: W - padR, y1: y, y2: y }));
    }
    const pts = [];
    bills.forEach((b, i) => {
      const x = padL + slot * i + (slot - barW) / 2;
      const h = ((Number(b.amount) || 0) / maxAmt) * plotH;
      const y = H - padB - h;
      const rect = svgEl("rect", { class: "bar-rect" + (i === bills.length - 1 ? " latest" : ""), x, y, width: barW, height: Math.max(3, h), rx: 8 });
      rect.style.animationDelay = i * 45 + "ms";
      rect.append(svgEl("title", {}, (b.period_end || "") + " · " + num(b.amount, 2) + " · " + num(b.kwh, 1) + " kWh"));
      svg.append(rect);
      svg.append(svgEl("text", { class: "val", x: x + barW / 2, y: y - 7, "text-anchor": "middle" }, num(b.amount, 0)));
      const d = b.period_end ? new Date(b.period_end + "T12:00:00") : null;
      const label = d && !isNaN(d) ? d.toLocaleDateString(LOCALE, { month: "short" }) : "";
      svg.append(svgEl("text", { x: x + barW / 2, y: H - padB + 18, "text-anchor": "middle" }, label));
      pts.push([x + barW / 2, H - padB - ((Number(b.kwh) || 0) / maxKwh) * plotH]);
    });
    // smooth curve through the kWh points (cardinal spline)
    let dpath = "M" + pts[0][0].toFixed(1) + "," + pts[0][1].toFixed(1);
    for (let k = 0; k < pts.length - 1; k++) {
      const p0 = pts[k - 1] || pts[k];
      const p1 = pts[k];
      const p2 = pts[k + 1];
      const p3 = pts[k + 2] || p2;
      const c1x = p1[0] + (p2[0] - p0[0]) / 6;
      const c1y = p1[1] + (p2[1] - p0[1]) / 6;
      const c2x = p2[0] - (p3[0] - p1[0]) / 6;
      const c2y = p2[1] - (p3[1] - p1[1]) / 6;
      dpath += " C" + [c1x, c1y, c2x, c2y, p2[0], p2[1]].map((v) => v.toFixed(1)).join(",");
    }
    svg.append(svgEl("path", { class: "kwh-line", d: dpath }));
    for (const q of pts) svg.append(svgEl("circle", { class: "kwh-dot", cx: q[0], cy: q[1], r: 4.5 }));
    this._chart.append(svg);
    this._chart.append(
      el(
        "div",
        { class: "chart-legend" },
        el("span", {}, el("i", { style: "background:linear-gradient(135deg,var(--eb-accent-2,#7c4dff),var(--eb-accent,#03a9f4))" }), T("ยอดบิล (บาท)")),
        el("span", {}, el("i", { style: "background:var(--accent-color,#ff9800)" }), T("หน่วยไฟ (สูงสุด ") + num(maxKwh, 0) + " kWh)")
      )
    );
  }

  _nameOf(id) {
    const s = this._hass.states[id];
    const n = (s && s.attributes && s.attributes.friendly_name) || id;
    return String(n).replace(/_/g, " ").replace(/\s*kwh\s*$/i, "").trim() || String(n);
  }

  _mainMeter() {
    const un = this._hass.states["sensor.electricity_bill_cycle_unmetered_energy"];
    return (un && un.attributes && un.attributes.main_meter) || null;
  }

  _renderBreakdown() {
    const cyc = this._st("sensor.electricity_bill_cycle_energy");
    this._breakdown.replaceChildren();
    const per = (cyc && cyc.attributes && cyc.attributes.per_source) || {};
    const main = this._mainMeter();
    const unm = this._st("sensor.electricity_bill_cycle_unmetered_energy");
    const rows = [];
    for (const [id, v] of Object.entries(per)) {
      if (id === main) continue;
      rows.push({ name: this._nameOf(id), kwh: Number(v) || 0 });
    }
    rows.sort((a, b) => b.kwh - a.kwh);
    if (main && unm) rows.push({ name: T("ไฟรอบนี้ที่ไม่มีมิเตอร์ย่อย"), kwh: Number(unm.state) || 0, other: true });
    const total = rows.reduce((s, r) => s + r.kwh, 0);
    if (!rows.length || !(total > 0)) {
      this._breakdown.append(el("p", { class: "hint", text: T("ยังไม่มีข้อมูลรายเครื่อง") }));
      return;
    }
    const palette = ["var(--eb-accent)", "var(--eb-ok)", "var(--eb-warn)", "var(--eb-violet)", "#00acc1", "#ec407a", "#8d6e63", "#5c6bc0"];
    const rate = Number((this._st("sensor.electricity_bill_effective_rate") || {}).state) || 0;
    const stack = el("div", { class: "stack" });
    const list = el("div", {});
    rows.forEach((r, i) => {
      const color = r.other ? "var(--eb-line)" : palette[i % palette.length];
      const pct = (r.kwh / total) * 100;
      stack.append(el("i", { style: "width:" + pct.toFixed(2) + "%;background:" + color, title: r.name + " " + num(r.kwh, 2) + " kWh" }));
      list.append(
        el(
          "div",
          { class: "dev-row" },
          el("span", { class: "dev-dot", style: "background:" + color }),
          el("span", { class: "dev-name", text: r.name }),
          el("span", { class: "dev-kwh", text: num(r.kwh, 2) + " kWh" + (rate ? T(" · ฿") + num(r.kwh * rate, 0) : "") }),
          el("span", { class: "dev-pct", text: num(pct, 0) + "%" })
        )
      );
    });
    this._breakdown.append(stack, list);
  }

  async _loadDaily() {
    const cyc = this._st("sensor.electricity_bill_cycle_energy");
    if (!cyc) return;
    const main = this._mainMeter();
    const per = (cyc.attributes && cyc.attributes.per_source) || {};
    const ids = main ? [main] : Object.keys(per);
    if (!ids.length) return;
    const startStr = cyc.attributes.cycle_start;
    const start = startStr ? new Date(startStr + "T00:00:00") : new Date(Date.now() - 30 * 86400000);
    const key = ids.join(",") + "|" + start.toISOString();
    const now = Date.now();
    if (key === this._dailyKey && now - this._dailyFetchedAt < 300000) return;
    this._dailyKey = key;
    this._dailyFetchedAt = now;
    try {
      const res = await this._hass.callWS({
        type: "recorder/statistics_during_period",
        start_time: start.toISOString(),
        statistic_ids: ids,
        period: "day",
        types: ["change"],
      });
      const byDay = new Map();
      for (const id of ids) {
        for (const row of res[id] || []) {
          byDay.set(row.start, (byDay.get(row.start) || 0) + (Number(row.change) || 0));
        }
      }
      this._dailyData = Array.from(byDay.entries()).sort((a, b) => a[0] - b[0]).map(([s, c]) => ({ start: s, kwh: c }));
      this._dailyError = false;
      this._prevCompare = null;
      // same number of days from the start of the previous billing cycle (needs statistics that far back)
      const hist = this._hass.states["sensor.electricity_bill_bill_history"];
      const last = hist && hist.attributes && hist.attributes.bills && hist.attributes.bills[0];
      const n = this._dailyData.length;
      if (last && last.period_start && n > 0) {
        const pStart = new Date(last.period_start + "T00:00:00");
        const pEnd = new Date(pStart.getTime() + n * 86400000);
        const prev = await this._hass.callWS({
          type: "recorder/statistics_during_period",
          start_time: pStart.toISOString(),
          end_time: pEnd.toISOString(),
          statistic_ids: ids,
          period: "day",
          types: ["change"],
        });
        const prevByDay = new Map();
        for (const id of ids) for (const row of prev[id] || []) prevByDay.set(row.start, (prevByDay.get(row.start) || 0) + (Number(row.change) || 0));
        const prevTotal = Array.from(prevByDay.values()).reduce((s, v) => s + v, 0);
        const curTotal = this._dailyData.reduce((s, d) => s + d.kwh, 0);
        if (prevByDay.size >= n && prevTotal > 0) this._prevCompare = ((curTotal - prevTotal) / prevTotal) * 100;
      }
    } catch (e) {
      this._dailyData = [];
      this._dailyError = true;
    }
    this._renderDaily();
  }

  _renderDaily() {
    this._loadDaily();
    this._daily.replaceChildren();
    const data = this._dailyData;
    if (!data || !data.length || this._dailyError) {
      if (data) this._daily.append(el("p", { class: "hint", text: T(this._dailyError ? "อ่านสถิติรายวันไม่สำเร็จ" : "ยังไม่มีสถิติรายวัน มิเตอร์เพิ่งเริ่มบันทึก") }));
      return;
    }
    const W = 600;
    const H = 190;
    const padT = 22;
    const padB = 26;
    const plotH = H - padT - padB;
    const max = Math.max(...data.map((d) => d.kwh), 0.1);
    const total = data.reduce((s, d) => s + d.kwh, 0);
    const avg = total / data.length;
    const slot = W / data.length;
    const barW = Math.max(3, Math.min(34, slot * 0.7));
    const NS = "http://www.w3.org/2000/svg";
    const mk = (tag, attrs, text) => {
      const n = document.createElementNS(NS, tag);
      for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, String(v));
      if (text !== undefined) n.textContent = text;
      return n;
    };
    const svg = mk("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": T("ใช้ไฟรายวัน (รอบนี้)") });
    const todayKey = new Date().toDateString();
    const everyLabel = data.length > 20 ? 3 : data.length > 10 ? 2 : 1;
    data.forEach((d, i) => {
      const x = slot * i + (slot - barW) / 2;
      const h = (d.kwh / max) * plotH;
      const y = H - padB - h;
      const dt = new Date(d.start);
      const isToday = dt.toDateString() === todayKey;
      const rect = mk("rect", { class: "d-bar" + (isToday ? " today" : ""), x, y, width: barW, height: Math.max(2, h), rx: Math.min(6, barW / 2) });
      rect.style.animationDelay = i * 25 + "ms";
      rect.append(mk("title", {}, dt.toLocaleDateString(LOCALE, { day: "numeric", month: "short" }) + " · " + num(d.kwh, 2) + " kWh"));
      svg.append(rect);
      if (data.length <= 14) svg.append(mk("text", { class: "d-val", x: x + barW / 2, y: y - 5, "text-anchor": "middle" }, num(d.kwh, 1)));
      if (i % everyLabel === 0) svg.append(mk("text", { x: x + barW / 2, y: H - padB + 15, "text-anchor": "middle" }, String(dt.getDate())));
    });
    const ay = H - padB - (avg / max) * plotH;
    svg.append(mk("line", { class: "d-avg", x1: 0, x2: W, y1: ay, y2: ay }));
    this._daily.append(svg);
    this._daily.append(
      el(
        "div",
        { class: "daily-sum" },
        el("span", {}, T("รวม "), el("b", { text: num(total, 1) + " kWh" })),
        el("span", {}, T("เฉลี่ย "), el("b", { text: num(avg, 2) + " " + T("หน่วย/วัน") })),
        this._prevCompare != null
          ? el("span", {}, T("เทียบรอบก่อน "), el("b", { text: (this._prevCompare > 0 ? "+" : "") + num(this._prevCompare, 1) + "%" }))
          : null
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
