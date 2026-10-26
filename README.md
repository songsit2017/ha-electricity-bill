# Electricity Bill (ระบบติดตามบิลค่าไฟสำหรับ Home Assistant)

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
- **ตั้งจุดเริ่มนับเองได้ (v0.3.1)**: บริการ `set_baseline` สำหรับเซ็นเซอร์ที่เพิ่งเพิ่ม เช่น เบรกเกอร์วัดไฟรวมทั้งบ้าน
- **รองรับ 2 ภาษา**: รองรับภาษาไทย (TH) และภาษาอังกฤษ (EN) เต็มรูปแบบ

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

> **ใช้เซ็นเซอร์วัดไฟรวมทั้งบ้านหรือมิเตอร์ย่อย?** ระบบรวมหน่วยของทุก Source เข้าด้วยกัน ถ้ามีมิเตอร์/เบรกเกอร์วัดไฟรวมทั้งบ้านอยู่แล้ว (เช่น Tuya Local Main Breaker) ให้เลือกเป็น Source เพียงตัวเดียว ถ้าเลือกทั้งตัวรวมและมิเตอร์ย่อย หน่วยจะถูกนับซ้ำ ส่วนมิเตอร์ย่อยยังใช้ในแดชบอร์ดของ Home Assistant แยกต่างหากได้ตามปกติ
4. สามารถปรับเปลี่ยนรายการเซ็นเซอร์และ Fallback Rate ภายหลังได้ตลอดเวลาผ่านปุ่ม **Configure (กำหนดค่า)**

---

## เอนทิตีที่สร้างขึ้น (Entities)

ทุกเซ็นเซอร์อยู่ภายใต้อุปกรณ์ **Electricity Bill**:

| Entity ID | ชื่อเซ็นเซอร์ | หน่วย | คำอธิบาย | Attributes สำคัญ |
|---|---|---|---|---|
| `sensor.electricity_bill_cycle_energy` | Cycle Energy | kWh | พลังงานที่ใช้ในรอบบิลปัจจุบัน | `per_source`, `cycle_start`, `days_in_cycle` |
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
