# Electricity Bill (ระบบติดตามบิลค่าไฟสำหรับ Home Assistant)

**ภาษาไทย** | [English](README.en.md)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)

Home Assistant custom integration สำหรับบันทึกบิลค่าไฟฟ้าประจำเดือน (จำนวนหน่วย kWh + ยอดเงินบาท + วันสิ้นสุดรอบบิล) เพื่อคำนวณ**อัตราค่าไฟจริงต่อหน่วย (Real Effective Rate)** และประมาณการค่าไฟฟ้าของรอบบิลปัจจุบันแบบเรียลไทม์

---

## จุดเด่น (Key Features)

- **วันตัดรอบบิลยืดหยุ่น (Dynamic Billing Period Cut-off)**: วันที่ในบิลไม่ได้ตรงกันทุกเดือน (เช่น 25 ก.ย. แล้วตามด้วย 23 ต.ค.) ระบบรองรับวันสิ้นสุดรอบบิลที่เปลี่ยนไปในแต่ละเดือนโดยอัตโนมัติ
- **อัตราค่าไฟจริง (Real Cost per Unit)**: คำนวณ `บาท / kWh` จากบิลจริงล่าสุด แทนที่การเดาค่าคงที่ 4.40 บาท/หน่วย
- **ประมาณการค่าไฟรอบปัจจุบัน (Running Cycle Estimate)**: คำนวณพลังงานสะสมตั้งแต่เริ่มรอบใหม่คูณด้วยอัตราค่าไฟจริง
- **ดึงสถิติย้อนหลังอัตโนมัติ (Long-term Statistics)**: หากใส่วันสิ้นสุดรอบบิลย้อนหลัง ระบบจะดึงค่ามิเตอร์ ณ สิ้นวันนั้นจาก HA Recorder Long-term Statistics อัตโนมัติ
- **ป้องกันปัญหามิเตอร์รีเซ็ต (Meter Reset Handling)**: หากอุปกรณ์สมาร์ทปลั๊กหรือมิเตอร์ถูกรีเซ็ตค่าเป็น 0 จะไม่ทำให้เกิดค่าติดลบ
- **รายละเอียดบิล (v0.3+)**: บันทึกวันเริ่มรอบ ค่าไฟฟ้าฐาน Ft ค่าบริการ VAT พร้อมสถิติต่อวันและเปลี่ยนแปลงจากบิลก่อน (ดูหัวข้อ "รายละเอียดบิล")
- **หน้าจอ "ค่าไฟ" ในแถบเมนูข้าง**: กรอกบิลเอง หรือถ่ายรูป/อัปโหลดบิลให้ AI Task (เช่น Anthropic) อ่านค่าให้ (ไม่บังคับ)
- **ตั้งจุดเริ่มนับเองได้ (v0.3.1)**: บริการ `set_baseline` (และการ์ด "ขั้นสูง" ในหน้าจอ "ค่าไฟ" v0.5) สำหรับเซ็นเซอร์ที่เพิ่งเพิ่ม เช่น เบรกเกอร์วัดไฟรวมทั้งบ้าน
- **มิเตอร์หลักรวมทั้งบ้าน (v0.5)**: ตั้งมิเตอร์หลักตัวเดียวเป็นตัวคิดหน่วยและค่าไฟ ส่วนมิเตอร์ย่อยใช้แยกดูรายเครื่อง มีเซ็นเซอร์ไฟรอบนี้ที่ไม่มีมิเตอร์ย่อยแบบเรียลไทม์ และกดปุ่มรีเซ็ตมิเตอร์หลักให้อัตโนมัติหลังบันทึกบิล
- **โปรไฟล์อัตราค่าไฟ (v0.6)**: เลือก "ไม่ใช้" (ค่าเริ่มต้น ใช้ได้ทุกประเทศ), "ไทย บ้านอยู่อาศัย" หรือ "กำหนดเอง" เพื่อประมาณบิลเต็มตามขั้นบันได + ค่าเพิ่มต่อหน่วย (Ft) + ค่าบริการ + ภาษี และคาดการณ์ถึงวันตัดรอบ (ดูหัวข้อ "อัตราค่าไฟและการคาดการณ์")
- **หน้าจอ "ค่าไฟ" (v0.7)**: กราฟยอดบิลและหน่วยไฟรายรอบบิล (12 รอบล่าสุด), แก้ไขบิลที่บันทึกแล้ว (ปุ่ม "แก้ไข" ในรายการประวัติ วันสิ้นสุดรอบบิลเปลี่ยนไม่ได้), ส่งออกประวัติเป็นไฟล์ CSV และใช้งานบนมือถือได้
- **รองรับ 6 ภาษา**: ไทย อังกฤษ เวียดนาม มาเลย์ อินโดนีเซีย และรัสเซีย ทั้งหน้าจอ "ค่าไฟ" และหน้าตั้งค่า เลือกตามภาษาของ Home Assistant (ภาษาอื่นแสดงเป็นอังกฤษ) ใช้สกุลเงินที่ตั้งใน HA คำแปลภาษาใหม่เป็นแบบที่เขียนด้วยเครื่อง ยินดีรับการตรวจแก้จากเจ้าของภาษา เพิ่มภาษาใหม่ได้ที่ตัวแปร `I18N` ใน `frontend/panel.js` และไฟล์ `translations/<รหัสภาษา>.json`
- **ใช้ไฟรายเครื่องและรายวัน (v0.9)**: การ์ดแบ่งสัดส่วนหน่วยไฟของแต่ละมิเตอร์ย่อยและไฟที่ไม่มีมิเตอร์ย่อยในรอบนี้ พร้อมค่าไฟโดยประมาณ และกราฟแท่งหน่วยไฟรายวันของรอบนี้ (จากสถิติระยะยาวของ HA)
- **ใช้ไฟวันนี้ เมื่อวาน และเฉลี่ยรายวัน (v0.10)**: เซ็นเซอร์ใหม่ 3 ตัว พร้อมแจ้งเตือนเมื่อวันนี้ใช้ไฟสูงกว่าค่าเฉลี่ยของรอบตามจำนวนเท่าที่ตั้ง (อีเวนต์ `electricity_bill_high_usage`) และเทียบกับรอบก่อนในกราฟรายวัน (เมื่อมีสถิติย้อนหลังพอ)
- **ค่าไฟรายเครื่องรายรอบบิล (v0.14)**: ทุกมิเตอร์ใน Source (และมิเตอร์หลัก) ได้เซ็นเซอร์ 2 ตัวอัตโนมัติ เช่น `sensor.electricity_bill_aircon_bedroom_cycle_energy` (หน่วยไฟรอบบิลนี้) และ `..._cycle_cost` (ค่าไฟรอบบิลนี้ = หน่วย × อัตราเฉลี่ยจริงของบิลล่าสุด) ทั้งสองเริ่มนับใหม่ทุกรอบบิล: ตอนบันทึกบิลใหม่ หรืออัตโนมัติตอนเที่ยงคืนหลังวันตัดรอบถ้ายังไม่ได้บันทึกบิล (เมื่อบันทึกบิลทีหลัง จุดตัดจะปรับให้ตรงวันที่ในบิลเอง) ยอดของแต่ละเครื่องในแต่ละรอบถูกเก็บไว้ในบิลนั้น และแสดงในหน้าจอ "ค่าไฟ" เมื่อกดดูบิล
- **ดีไซน์ใหม่ (v0.8)**: การ์ดสรุปพร้อมวงแหวนความคืบหน้าของรอบบิล กราฟแท่งไล่สีพร้อมเส้นโค้งหน่วยไฟและแอนิเมชัน ไอคอนสีแยกตามประเภทข้อมูล

---

## การติดตั้งผ่าน HACS (Installation via HACS)

1. เปิด **Home Assistant** ไปที่เมนู **HACS** > **Integrations**
2. กดเมนูสามจุดมุมขวาบน เลือก **Custom repositories**
3. ใส่ Repository URL `https://github.com/songsit2017/ha-electricity-bill` เลือกหมวดหมู่ (Category) เป็น **Integration** แล้วกด **Add**
4. ค้นหา **Electricity Bill** แล้วกด **Download**
5. รีสตาร์ท Home Assistant

เมื่อมีเวอร์ชันใหม่ (GitHub Release) HACS จะแจ้งในหน้า Updates ของ Home Assistant และกดอัปเดตได้ทันที (รีสตาร์ท HA หลังอัปเดต)

---

## การตั้งค่า (Configuration)

1. ไปที่ **Settings (การตั้งค่า)** > **Devices & Services (อุปกรณ์และบริการ)** > **Add Integration (เพิ่มการรวมระบบ)**
2. ค้นหา **Electricity Bill**
3. กำหนดค่า:
   - **Name**: ชื่อของอุปกรณ์ (ค่าเริ่มต้น: `Electricity Bill`)
   - **Source Energy Sensors**: เลือกเซ็นเซอร์วัดพลังงาน (kWh) ที่ต้องการติดตาม (เช่น `sensor.aircon_bedroom_kwh`, `sensor.pc_kwh`, `sensor.water_pump_kwh` ฯลฯ)
   - **Fallback Rate**: อัตราค่าไฟสำรองก่อนมีบิลแรก (ค่าเริ่มต้น: `4.40` บาท/kWh)
   - **AI Task Entity** (ไม่บังคับ): เอนทิตี `ai_task.*` สำหรับอ่านบิลจากรูปภาพ

4. สามารถปรับเปลี่ยนรายการเซ็นเซอร์และ Fallback Rate ภายหลังได้ตลอดเวลาผ่านปุ่ม **Configure (กำหนดค่า)**

> **มีมิเตอร์/เบรกเกอร์วัดไฟรวมทั้งบ้าน (v0.5)?** ใน **Configure** ให้เลือกเป็น **มิเตอร์หลัก (Main meter)** แล้วใส่มิเตอร์ย่อย (แอร์ ปั๊มน้ำ ฯลฯ) ไว้ในช่อง Source Energy Sensors:
> - หน่วยและค่าไฟรอบนี้คิดจากมิเตอร์หลักตัวเดียว มิเตอร์ย่อยไม่ถูกนับซ้ำ ใช้แยกดูรายเครื่องเท่านั้น
> - ได้เซ็นเซอร์ `sensor.electricity_bill_cycle_unmetered_energy` = หน่วยของมิเตอร์หลักลบผลรวมมิเตอร์ย่อยในรอบนี้ (ไม่ติดลบ)
> - **ปุ่มรีเซ็ตมิเตอร์หลัก** (ไม่บังคับ เช่น `button.main_breaker_energy_reset`): เมื่อบันทึกบิลที่ใหม่กว่าบิลเดิม ระบบกดปุ่มให้เองหนึ่งครั้ง และเก็บหน่วยที่ใช้ตั้งแต่วันสิ้นสุดรอบบิลถึงตอนรีเซ็ตไว้ในรอบใหม่
> - ถ้าไม่ตั้งมิเตอร์หลัก ระบบทำงานเหมือนเดิม (รวมหน่วยของทุก Source) อย่าเลือกมิเตอร์รวมและมิเตอร์ย่อยเป็น Source ธรรมดาพร้อมกัน เพราะหน่วยจะนับซ้ำ

---

## เอนทิตีที่สร้างขึ้น (Entities)

ทุกเซ็นเซอร์อยู่ภายใต้อุปกรณ์ **Electricity Bill**:

| Entity ID | ชื่อเซ็นเซอร์ | หน่วย | คำอธิบาย | Attributes สำคัญ |
|---|---|---|---|---|
| `sensor.electricity_bill_cycle_energy` | Cycle Energy | kWh | พลังงานที่ใช้ในรอบบิลปัจจุบัน | `per_source`, `cycle_start`, `days_in_cycle` |
| `sensor.electricity_bill_cycle_unmetered_energy` | Cycle Unmetered Energy | kWh | หน่วยรอบนี้ที่ไม่มีมิเตอร์ย่อย (มิเตอร์หลัก − มิเตอร์ย่อย) สร้างเฉพาะเมื่อตั้งมิเตอร์หลัก | `main_meter`, `submetered_kwh` |
| `sensor.electricity_bill_cycle_bill_estimate` | Cycle Bill Estimate | บาท/สกุลเงินของ HA | ประมาณการบิลเต็มของรอบนี้ ตามโปรไฟล์อัตราค่าไฟ (ไม่ใช้โปรไฟล์ = หน่วย × อัตราเฉลี่ย) | `energy_charge`, `ft_charge`, `service_charge`, `subtotal`, `vat`, `total` |
| `sensor.electricity_bill_forecast_bill` | Forecast Bill | บาท/สกุลเงินของ HA | คาดการณ์บิลถึงวันตัดรอบถัดไป จากค่าเฉลี่ยต่อวันของรอบนี้ (ต้องตั้งวันตัดรอบ) | `forecast_kwh`, `kwh_per_day`, `cycle_days`, `cutoff_date` |
| `sensor.electricity_bill_next_billing_day` | Next Billing Day | วันที่ | วันตัดรอบถัดไป (ต้องตั้งวันตัดรอบ) | - |
| `sensor.electricity_bill_today_energy` | Today Energy | kWh | หน่วยไฟที่ใช้ตั้งแต่ 00:00 ของวันนี้ (จากมิเตอร์หลัก หรือรวมทุก Source) | - |
| `sensor.electricity_bill_yesterday_energy` | Yesterday Energy | kWh | หน่วยไฟเมื่อวาน (ว่างจนกว่าจะข้ามวันหนึ่งครั้ง) | - |
| `sensor.electricity_bill_daily_average_energy` | Daily Average Energy | kWh | หน่วยไฟเฉลี่ยต่อวันของรอบนี้ | - |
| `sensor.electricity_bill_effective_rate` | Effective Rate | THB/kWh | อัตราค่าไฟจริงต่อหน่วยจากบิลล่าสุด | `source` ("bill"/"fallback"), `based_on_period_end` |
| `sensor.electricity_bill_cycle_cost_estimate` | Cycle Cost Estimate | THB | ประมาณการค่าไฟรอบปัจจุบัน (`cycle_kwh * rate`) | `rate_used` |
| `sensor.electricity_bill_last_bill_amount` | Last Bill Amount | THB | ยอดเงินรวมของบิลล่าสุด | `period_start`, `period_end`, `kwh`, `rate`, `note` |
| `sensor.electricity_bill_last_bill_energy` | Last Bill Energy | kWh | จำนวนหน่วยไฟของบิลล่าสุด | `period_end` |
| `sensor.electricity_bill_last_bill_unmetered_energy` | Last Bill Unmetered Energy | kWh | หน่วยไฟที่ไม่ได้ติดมิเตอร์ (`bill kwh - measured kwh`) | `measured_kwh`, `share_metered_percent` |
| `sensor.electricity_bill_bill_history` | Bill History | - | จำนวนบิลที่บันทึกไว้ในระบบ | `bills` (ประวัติบิลย้อนหลัง สูงสุด 24 บิล ล่าสุดก่อน) |

---

## บริการที่รองรับ (Services)

### 1. `electricity_bill.add_bill`
บันทึกบิลค่าไฟประจำเดือน คำนวณอัตราค่าไฟ และเริ่มรอบการวัดใหม่

```yaml
action: electricity_bill.add_bill
data:
  period_end: "2026-10-23" # วันสุดท้ายของรอบบิลตามใบแจ้งหนี้ (เว้นว่างได้ = วันนี้)
  kwh: 312.0               # จำนวนหน่วยไฟรวมในบิล
  amount: 1385.12          # ยอดเงินรวมในบิล (บาท)
  note: "บิลรอบเดือนตุลาคม"   # บันทึกเพิ่มเติม (ไม่บังคับ)
  # ฟิลด์รายละเอียด (period_start, energy_charge, ft_charge, service_charge, vat) ไม่บังคับ ดูหัวข้อ "รายละเอียดบิล"
  replace: false           # อนุญาตให้บันทึกทับหากมีวันสิ้นสุดรอบบิลซ้ำกัน
```

### 2. `electricity_bill.remove_bill`
ลบบิลตามรหัส (`id`) หรือตามวันสิ้นสุดรอบบิล (`period_end`)

```yaml
action: electricity_bill.remove_bill
data:
  period_end: "2026-10-23"
  # หรือใช้ id: "uuid-ของบิล"
```

### 3. `electricity_bill.reset_cycle`
รีเซ็ตจุดเริ่มต้นของรอบบิลใหม่เป็นค่ามิเตอร์ปัจจุบันทันที โดยไม่บันทึกบิล

```yaml
action: electricity_bill.reset_cycle
```

### 4. `electricity_bill.set_baseline`
ตั้งจุดเริ่มนับของเซ็นเซอร์ต้นทางหนึ่งตัวเป็นค่ามิเตอร์ที่ระบุ (พลังงานรอบนี้ = ค่าปัจจุบัน − จุดเริ่มนับ) ใช้เมื่อเพิ่งเพิ่มเซ็นเซอร์ที่ตัวนับเริ่มจาก 0 อยู่แล้ว เช่น เบรกเกอร์หลักตัวใหม่ แล้วต้องการนับยอดสะสมทั้งหมดเป็นของรอบนี้

```yaml
action: electricity_bill.set_baseline
data:
  entity_id: sensor.main_breaker_energy  # ต้องเป็นหนึ่งใน Source Energy Sensors
  value: 0                               # ค่ามิเตอร์ ณ จุดเริ่มรอบ (ค่าเริ่มต้น 0)
```

> เคล็ดลับ: ถ้ามีเบรกเกอร์/มิเตอร์วัดไฟรวมทั้งบ้านตัวเดียว ให้ใส่เป็น Source เพียงตัวเดียว ไม่ต้องใส่มิเตอร์ย่อยซ้ำ ไม่เช่นนั้นหน่วยจะถูกนับซ้ำ

---

## อัตราค่าไฟและการคาดการณ์ (Tariff & forecast, v0.6)

ใน **Configure** หน้าที่สอง ("อัตราค่าไฟ วันตัดรอบ และงบประมาณ") เลือก **โปรไฟล์อัตราค่าไฟ**:

| โปรไฟล์ | ใช้ทำอะไร |
|---|---|
| `none` (ค่าเริ่มต้น) | ใช้ได้ทุกประเทศ ประมาณจากอัตราเฉลี่ยจริงของบิลล่าสุด (หน่วย × บาท/หน่วย) ไม่ต้องกรอกอะไรเพิ่ม |
| `thailand_residential` | อัตราบ้านอยู่อาศัยของ กฟภ./กฟน. ตั้งแต่บิล ก.ย. 2569: 200 หน่วยแรก 3.0000, 201-400 หน่วย 4.1584, เกิน 400 หน่วย 4.3583 บาท/หน่วย (ผู้ใช้ไม่เกิน 150 หน่วยใช้ตารางขั้นต้น 2.3488/2.9882 เพิ่ม) + Ft + ค่าบริการ + VAT 7% ค่าเริ่มต้น Ft 0.1623, ค่าบริการ 24.62 และวันตัดรอบ 24 (เดือน 30 วัน) / 25 (เดือน 31 วัน) ปรับเองได้ ตรวจเทียบบิลจริงเดือน ก.ย. และ ต.ค. 2569 ตรงภายใน 5 สตางค์ในส่วนค่าพลังงาน |
| `custom` | ใส่ขั้นบันไดเอง เช่น `200:3.0, 400:4.1584, 4.3583` (หน่วยสะสมสูงสุดของขั้น:อัตรา ขั้นสุดท้ายไม่จำกัด) พร้อมค่าเพิ่มต่อหน่วย ค่าบริการรายเดือน และภาษี (%) |

- **วันตัดรอบ**: ตั้งวันของเดือน 30 วัน / 31 วัน / กุมภาพันธ์ (ใส่วันเดียวกันทั้งสามช่องถ้าตัดรอบวันเดียวทุกเดือน) เมื่อตั้งแล้วจะได้เซ็นเซอร์ **Next Billing Day** และ **Forecast Bill** เว้นว่างเพื่อปิด
- **สกุลเงิน**: เซ็นเซอร์ที่เป็นเงินใช้สกุลเงินที่ตั้งใน Home Assistant (Settings > System > General)
- **งบประมาณ**: ตั้ง `budget_threshold` แล้วระบบส่งอีเวนต์ `electricity_bill_budget_exceeded` หนึ่งครั้งต่อรอบเมื่อบิลโดยประมาณถึงจำนวนนั้น (ข้อมูล: `threshold`, `bill_estimate`, `cycle_kwh`, `cycle_start`)
- **ใช้ไฟรายวันสูง**: ตั้ง `high_usage_factor` (เช่น 2 = สองเท่าของค่าเฉลี่ยรายวันของรอบ) แล้วระบบส่งอีเวนต์ `electricity_bill_high_usage` หนึ่งครั้งต่อวัน เมื่อหน่วยไฟวันนี้ถึงเกณฑ์และมากกว่า 2 kWh (ข้อมูล: `date`, `today_kwh`, `daily_average_kwh`, `factor`)
- **สรุปรายวันและรายสัปดาห์ (v0.12)**: ทุกวันเวลา `summary_hour` (ค่าเริ่มต้น 21:00) ระบบส่งอีเวนต์ `electricity_bill_daily_summary` และในวัน `weekly_summary_day` (ค่าเริ่มต้น 6 = อาทิตย์) ส่ง `electricity_bill_weekly_summary` ด้วย ข้อมูลในอีเวนต์มีข้อความสำเร็จรูปใน `message` (ไทยหรืออังกฤษตามภาษา HA) พร้อมตัวเลขดิบ (`today_kwh`, `cost_estimate`, `devices`, `kwh`, `change_pct` ฯลฯ) รายสัปดาห์เทียบกับสัปดาห์ก่อนเมื่อมีข้อมูลครบ 14 วัน ประวัติรายวันเริ่มเก็บหลังติดตั้งและข้ามเที่ยงคืนครั้งแรก

ตัวอย่างออโตเมชันส่งเข้า Telegram (เปลี่ยน `config_entry_id` และ `target` เป็นของคุณ):

```yaml
triggers:
  - trigger: event
    event_type: electricity_bill_daily_summary
  - trigger: event
    event_type: electricity_bill_weekly_summary
actions:
  - action: telegram_bot.send_message
    data:
      config_entry_id: "<telegram config entry id>"
      target: -1001234567890
      message: "{{ trigger.event.data.message }}"
```
- **ดึงสรุปได้ทุกเมื่อ (v0.13)**: บริการ `electricity_bill.get_summary` (`kind`: `daily`, `weekly`, `cycle`) ส่งคืนข้อมูลพร้อม `message` ใช้กับ `response_variable` เช่น ตอบคำสั่งใน Telegram ส่วนอีเวนต์ `electricity_bill_cutoff_day` (12:00 วันตัดรอบ) มี `message` สรุปทั้งรอบพร้อมเตือนให้บันทึกบิล

ตัวอย่างตอบคำสั่ง `/power` และ `/week` ใน Telegram:

```yaml
triggers:
  - trigger: event
    event_type: telegram_command
    event_data:
      command: /power
    id: daily
  - trigger: event
    event_type: telegram_command
    event_data:
      command: /week
    id: weekly
actions:
  - action: electricity_bill.get_summary
    data:
      kind: "{{ trigger.id }}"
    response_variable: summary
  - action: telegram_bot.send_message
    data:
      config_entry_id: "<telegram config entry id>"
      target: "{{ trigger.event.data.chat_id }}"
      message: "{{ summary.message }}"
```

- **ดูแลตัวเอง (v0.13)**: ปุ่ม "ดาวน์โหลดข้อมูลวินิจฉัย" ในหน้า integration และแจ้งเตือนในหน้า Repairs ของ HA เมื่อมิเตอร์หลักไม่ตอบสนองนานกว่า 1 ชั่วโมง หรือค่า Ft ในตั้งค่าไม่ตรงกับบิลล่าสุด ประวัติรายวันเติมย้อนหลังจากสถิติของ HA ได้สูงสุด 28 วัน สรุปรายสัปดาห์จึงครบตั้งแต่สัปดาห์แรก
- **วันตัดรอบ**: เวลา 12:00 ของวันตัดรอบ ระบบส่งอีเวนต์ `electricity_bill_cutoff_day` (ข้อมูล: `cutoff_date`, `cycle_kwh`, `bill_estimate`, `forecast_bill`)

ตัวอย่างออโตเมชันแจ้งเตือนจากอีเวนต์ (เปลี่ยน `notify.mobile_app_xxx` เป็นบริการแจ้งเตือนของคุณ):

```yaml
triggers:
  - trigger: event
    event_type: electricity_bill_cutoff_day
actions:
  - action: notify.mobile_app_xxx
    data:
      message: >-
        วันนี้ตัดรอบบิล ใช้ไป {{ trigger.event.data.cycle_kwh | round(1) }} kWh
        ประมาณ {{ trigger.event.data.bill_estimate }} บาท
```

> ตารางอัตราค่าไฟของไทยในตัวโค้ดอ้างอิงประกาศ กกพ./กฟภ. เมื่อ ก.ย. 2569 ถ้าอัตราเปลี่ยน ให้ใช้โปรไฟล์ `custom` ได้ทันทีโดยไม่ต้องรอเวอร์ชันใหม่

---

## การเปลี่ยน Template Sensor เดิมให้ใช้อัตราค่าไฟจริง

หากเดิมคุณมี Template Sensor ที่ใช้ราคาคงที่ 4.40 บาท เช่น:

```yaml
# เดิม: ใช้ราคาคงที่ 4.40 บาท/หน่วย
sensor:
  - name: "Aircon Bedroom Cost Today"
    unit_of_measurement: "THB"
    state: >
      {{ (states('sensor.aircon_bedroom_daily_kwh') | float(0) * 4.40) | round(2) }}
```

คุณสามารถเปลี่ยนมาอ้างอิง `sensor.electricity_bill_effective_rate` ได้ทันที:

```yaml
# ใหม่: ใช้อัตราค่าไฟจริงจากบิลล่าสุด (Dynamic Real Rate)
sensor:
  - name: "Aircon Bedroom Cost Today"
    unit_of_measurement: "THB"
    state: >
      {% set rate = states('sensor.electricity_bill_effective_rate') | float(4.40) %}
      {% set kwh = states('sensor.aircon_bedroom_daily_kwh') | float(0) %}
      {{ (kwh * rate) | round(2) }}
```

---

## ตัวอย่างการจัดหน้าแดชบอร์ด (Dashboard YAML Example)

### 1. การ์ดแสดงสถานะ (Entities Card)

```yaml
type: entities
title: "⚡ ข้อมูลค่าไฟรอบปัจจุบัน"
show_header_toggle: false
entities:
  - entity: sensor.electricity_bill_cycle_cost_estimate
    name: "ประมาณการค่าไฟรอบนี้"
    icon: mdi:cash-multiple
  - entity: sensor.electricity_bill_cycle_energy
    name: "หน่วยไฟที่ใช้ไปรอบนี้"
    icon: mdi:lightning-bolt
  - entity: sensor.electricity_bill_effective_rate
    name: "อัตราค่าไฟจริงต่อหน่วย"
    icon: mdi:tag-text-outline
  - type: divider
  - entity: sensor.electricity_bill_last_bill_amount
    name: "ยอดบิลล่าสุด"
    icon: mdi:receipt-text
  - entity: sensor.electricity_bill_last_bill_energy
    name: "หน่วยไฟบิลล่าสุด"
    icon: mdi:counter
  - entity: sensor.electricity_bill_last_bill_unmetered_energy
    name: "ไฟส่วนที่ไม่ได้ติดมิเตอร์"
    icon: mdi:help-circle-outline
```

### 2. ปุ่มสำหรับกดบันทึกบิลค่าไฟ (Tile / Button Card with Action)

```yaml
type: tile
entity: sensor.electricity_bill_last_bill_amount
name: "บันทึกบิลค่าไฟใหม่"
icon: mdi:plus-circle
tap_action:
  action: call-service
  service: electricity_bill.add_bill
  data:
    kwh: 300
    amount: 1320
    note: "บันทึกด่วน"
```

หรือใช้การ์ดปุ่มกดเพื่อเปิดหน้าต่าง Service Call ใน Developer Tools หรือใช้ร่วมกับ Script สำหรับป้อนข้อมูลผ่าน Input Helpers

---

## คำอธิบายการใช้งานภาษาไทย (Thai Usage Guide)

1. **เมื่อได้รับบิลค่าไฟประจำเดือน**:
   - เปิดหน้า **Developer Tools (เครื่องมือสำหรับนักพัฒนา)** > **Actions/Services**
   - เลือกบริการ `electricity_bill.add_bill`
   - ใส่ **จำนวนหน่วย (kwh)** และ **ยอดเงินรวม (amount)** จากใบแจ้งหนี้
   - ใส่ **วันสิ้นสุดรอบบิล (period_end)** ตามที่ระบุในใบแจ้งหนี้ (เช่น `2026-10-23`)
   - กดยืนยัน ระบบจะคำนวณอัตราค่าไฟจริงต่อหน่วยทันที และตั้งรอบใหม่ให้อัตโนมัติ
2. **การติดตามระหว่างเดือน**:
   - ตรวจสอบ `sensor.electricity_bill_cycle_cost_estimate` เพื่อดูว่าค่าไฟในรอบปัจจุบันใช้ไปกี่บาทแล้ว
   - ตรวจสอบ `sensor.electricity_bill_last_bill_unmetered_energy` เพื่อดูว่ามีไฟฟ้าในบ้านส่วนใดที่ยังไม่ได้ติดตั้งมิเตอร์วัดพลังงาน

---

## การสแกนบิลด้วยรูปภาพและหน้าจอจัดการค่าไฟ (Scan a Bill & Web UI)

ในเวอร์ชัน 0.2.0 ขึ้นไป มีหน้าจอจัดการค่าไฟเฉพาะในแถบเมนูข้าง (Sidebar) ชื่อ **"ค่าไฟ"** สำหรับถ่ายรูปหรืออัปโหลดบิลค่าไฟ ให้ AI ช่วยอ่านข้อมูลและบันทึกบิลได้ในหน้าเดียว

### 1. การเปิดใช้งาน AI Task (Anthropic Integration)
1. ไปที่ **Settings (การตั้งค่า)** > **Devices & Services (อุปกรณ์และบริการ)** > **Add Integration (เพิ่มการรวมระบบ)**
2. ค้นหาและเลือก **Anthropic**
3. ใส่ API Key แล้วกดยืนยัน ระบบจะสร้างเอนทิตี `ai_task.*` ขึ้นมาอัตโนมัติ
4. Electricity Bill จะตรวจจับเอนทิตี `ai_task` ให้อัตโนมัติ (หรือสามารถระบุเอนทิตีที่ต้องการได้ใน **Configure (กำหนดค่า)** ของ Electricity Bill)
5. *หมายเหตุ: หากยังไม่ได้ตั้งค่า AI Task คุณยังคงสามารถเปิดหน้า "ค่าไฟ" แล้วพิมพ์ตัวเลข วันที่ และยอดเงินเพื่อบันทึกบิลได้ตามปกติ*

### 2. นโยบายความเป็นส่วนตัวและความปลอดภัย (Privacy Note)
- ภาพถ่ายบิลค่าไฟจะถูกส่งไปยังผู้ให้บริการ AI (เช่น Anthropic) เพื่อประมวลผลดึงข้อมูลเฉพาะ วันที่สิ้นสุดรอบบิล, จำนวนหน่วย (kWh), และยอดเงิน (บาท)
- ตัว Integration จะเขียนไฟล์ภาพลงในโฟลเดอร์สื่อชั่วคราว (`electricity_bill_scans`) และ**จะลบไฟล์รูปภาพออกจากระบบทันที**หลังประมวลผลเสร็จสิ้น (ไม่มีการเก็บรูปภาพหรือบันทึกลงในระบบจัดเก็บข้อมูลถาวร)
- ไม่มีการส่งข้อมูลออกไปยังเซิร์ฟเวอร์ภายนอกอื่นใดนอกจาก AI Provider ที่ผู้ใช้ตั้งค่าไว้ใน Home Assistant

### 3. รายการแก้ไขปัญหา (Troubleshooting)
- **ขึ้นข้อความ "ยังไม่ได้ตั้งค่า AI: Settings → Devices & services → Add integration → Anthropic"**:
  ยังไม่มีเอนทิตี `ai_task.*` ใน Home Assistant ให้ทำตามขั้นตอนการติดตั้ง Anthropic ด้านบน หรือพิมพ์ตัวเลขในช่องกรอกข้อมูลเองได้ทันที
- **ขึ้นข้อความ "ขนาดไฟล์รูปภาพเกิน 8 MB" (`file_too_large`)**:
  ระบบหน้าเว็บจะย่อขนาดรูปภาพให้อัตโนมัติก่อนส่ง (ความละเอียดไม่เกิน 1,600 px คุณภาพ 0.85) หากพบข้อผิดพลาดนี้ ให้ตรวจสอบว่ารูปภาพมีขนาดไม่เกิน 8 MiB
- **ขึ้นข้อความ "รูปแบบไฟล์ไม่ถูกต้อง" (`unsupported_media_type`)**:
  รองรับเฉพาะไฟล์รูปภาพประเภท JPEG (`.jpg`), PNG (`.png`), และ WebP (`.webp`) เท่านั้น
- **คำเตือนตรวจสอบข้อมูล (`rate_unusual`, `date_in_future`, `kwh_out_of_range`, `amount_out_of_range`)**:
  - `rate_unusual`: อัตราค่าไฟที่อ่านได้ไม่อยู่ในช่วง 1.5 - 12 บาท/หน่วย
  - `date_in_future`: วันที่ที่อ่านได้เป็นวันในอนาคต (เกินกว่าวันพรุ่งนี้)
  - `kwh_out_of_range`: จำนวนหน่วยไม่อยู่ในช่วง 1 - 5,000 kWh
  - `amount_out_of_range`: ยอดเงินไม่อยู่ในช่วง 1 - 100,000 บาท
  *ช่องกรอกข้อมูลทั้งหมดสามารถแก้ไขตัวเลขและวันที่ได้โดยตรงก่อนกดบันทึก*
- **บันทึกบิลซ้ำวันเดิม**:
  หากมีบิลในวันที่สิ้นสุดรอบบิลนั้นอยู่แล้ว ระบบจะถามยืนยันการแทนที่ข้อมูลเดิม ("มีบิลวันที่นี้แล้ว แทนที่ไหม?") หากกดยืนยันจะบันทึกทับข้อมูลบิลเดิม

## รายละเอียดบิล (v0.3.0+)

`electricity_bill.add_bill` รับค่าเพิ่มได้ (ไม่บังคับ): `period_start`, `energy_charge` (ค่าไฟฟ้าฐาน), `ft_charge` (Ft, ติดลบได้), `service_charge` (ค่าบริการ), `vat`.
ประวัติบิล (`sensor.electricity_bill_bill_history`, attribute `bills`) คำนวณให้เพิ่ม: `days`, `kwh_per_day`, `baht_per_day`, `kwh_change_pct`, `amount_change_pct` (เทียบบิลก่อนหน้า) และ `items_mismatch` เมื่อผลรวมรายการไม่ตรงยอดรวม
ถ้าไม่ระบุ `period_start` จะใช้วันถัดจากวันสิ้นสุดบิลก่อนหน้า บิลเก่าที่ไม่มีฟิลด์เหล่านี้ใช้งานได้ตามเดิม

ตัวอย่าง (ตัวเลขเป็นตัวอย่างเท่านั้น ไม่ใช่บิลจริง):

```yaml
action: electricity_bill.add_bill
data:
  period_end: "2026-11-25"
  kwh: 500
  amount: 2200.00
  energy_charge: 1900.00
  ft_charge: 100.00
  service_charge: 38.22
  vat: 143.78
```
