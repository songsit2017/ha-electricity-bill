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
- **รองรับ 2 ภาษา**: รองรับภาษาไทย (TH) และภาษาอังกฤษ (EN) เต็มรูปแบบ

---

## การติดตั้งผ่าน HACS (Installation via HACS)

1. เปิด **Home Assistant** ไปที่เมนู **HACS** > **Integrations**
2. กดเมนูสามจุดมุมขวาบน เลือก **Custom repositories**
3. ใส่ Repository URL ของโปรเจกต์นี้ เลือกหมวดหมู่ (Category) เป็น **Integration** แล้วกด **Add**
4. ค้นหา **Electricity Bill** แล้วกด **Download**
5. รีสตาร์ท Home Assistant

---

## การตั้งค่า (Configuration)

1. ไปที่ **Settings (การตั้งค่า)** > **Devices & Services (อุปกรณ์และบริการ)** > **Add Integration (เพิ่มการรวมระบบ)**
2. ค้นหา **Electricity Bill**
3. กำหนดค่า:
   - **Name**: ชื่อของอุปกรณ์ (ค่าเริ่มต้น: `Electricity Bill`)
   - **Source Energy Sensors**: เลือกเซ็นเซอร์วัดพลังงาน (kWh) ที่ต้องการติดตาม (เช่น `sensor.aircon_bedroom_kwh`, `sensor.pc_kwh`, `sensor.water_pump_kwh` ฯลฯ)
   - **Fallback Rate**: อัตราค่าไฟสำรองก่อนมีบิลแรก (ค่าเริ่มต้น: `4.40` บาท/kWh)
4. สามารถปรับเปลี่ยนรายการเซ็นเซอร์และ Fallback Rate ภายหลังได้ตลอดเวลาผ่านปุ่ม **Configure (กำหนดค่า)**

---

## เอนทิตีที่สร้างขึ้น (Entities)

ทุกเซ็นเซอร์อยู่ภายใต้อุปกรณ์ **Electricity Bill**:

| Entity ID | ชื่อเซ็นเซอร์ | หน่วย | คำอธิบาย | Attributes สำคัญ |
|---|---|---|---|---|
| `sensor.electricity_bill_cycle_kwh` | Cycle Energy | kWh | พลังงานที่ใช้ในรอบบิลปัจจุบัน | `per_source`, `cycle_start`, `days_in_cycle` |
| `sensor.electricity_bill_effective_rate` | Effective Rate | THB/kWh | อัตราค่าไฟจริงต่อหน่วยจากบิลล่าสุด | `source` ("bill"/"fallback"), `based_on_period_end` |
| `sensor.electricity_bill_cycle_cost_estimate` | Cycle Cost Estimate | THB | ประมาณการค่าไฟรอบปัจจุบัน (`cycle_kwh * rate`) | `rate_used` |
| `sensor.electricity_bill_last_bill_amount` | Last Bill Amount | THB | ยอดเงินรวมของบิลล่าสุด | `period_start`, `period_end`, `kwh`, `rate`, `note` |
| `sensor.electricity_bill_last_bill_kwh` | Last Bill Energy | kWh | จำนวนหน่วยไฟของบิลล่าสุด | `period_end` |
| `sensor.electricity_bill_last_bill_unmetered_kwh` | Last Bill Unmetered Energy | kWh | หน่วยไฟที่ไม่ได้ติดมิเตอร์ (`bill kwh - measured kwh`) | `measured_kwh`, `share_metered_percent` |
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
  - entity: sensor.electricity_bill_cycle_kwh
    name: "หน่วยไฟที่ใช้ไปรอบนี้"
    icon: mdi:lightning-bolt
  - entity: sensor.electricity_bill_effective_rate
    name: "อัตราค่าไฟจริงต่อหน่วย"
    icon: mdi:tag-text-outline
  - type: divider
  - entity: sensor.electricity_bill_last_bill_amount
    name: "ยอดบิลล่าสุด"
    icon: mdi:receipt-text
  - entity: sensor.electricity_bill_last_bill_kwh
    name: "หน่วยไฟบิลล่าสุด"
    icon: mdi:counter
  - entity: sensor.electricity_bill_last_bill_unmetered_kwh
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
   - ตรวจสอบ `sensor.electricity_bill_last_bill_unmetered_kwh` เพื่อดูว่ามีไฟฟ้าในบ้านส่วนใดที่ยังไม่ได้ติดตั้งมิเตอร์วัดพลังงาน
