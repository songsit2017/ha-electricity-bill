# SPEC v3 - detailed bill data (Electricity Bill integration)

Goal: each saved bill carries more detail and the history shows it. Keep everything backward compatible:
bills already in storage (keys id, period_start, period_end, kwh, amount, rate, snapshot, measured_kwh, note) must keep working
with no migration; do not change STORAGE_VERSION. All new fields are OPTIONAL.

## 1. New optional bill fields (stored in the bill record)
| key | meaning (Thai bill label) | type |
|---|---|---|
| period_start | start of billing period (ISO YYYY-MM-DD). Already exists but is always null today | str or null |
| energy_charge | ค่าไฟฟ้าฐาน / ค่าพลังงานไฟฟ้า, THB | float >= 0 or null |
| ft_charge | ค่าไฟฟ้าผันแปร (Ft), THB (may be negative) | float or null |
| service_charge | ค่าบริการรายเดือน, THB | float >= 0 or null |
| vat | ภาษีมูลค่าเพิ่ม 7%, THB | float >= 0 or null |
Rules: never invent values; null/missing means "not provided". Do NOT require them to sum to `amount`; if all four are
present and |sum - amount| > 0.05 set a derived flag `items_mismatch: true` in the formatted history (not stored).
Validation: numbers must be finite; energy/service/vat >= 0; period_start must be <= period_end, else ServiceValidationError
(translation_key `invalid_period`).

## 2. Services (services.yaml, strings.json, translations/en.json + th.json)
`add_bill` gets optional fields period_start (date selector), energy_charge, ft_charge, service_charge, vat (number selectors, mode box, unit THB).
`coordinator.async_add_bill(...)` takes the same new keyword args (all default None) and stores them. Existing calls/tests keep working.

## 3. Derived stats (calc.py, pure functions, unit-tested; NOT stored)
`format_bill_history(bills, max_items=24)` returns, newest first, for each bill:
id, period_start (stored value, else previous bill's period_end + 1 day, else null), period_end, days
(= (period_end - period_start).days + 1 when period_start known, else null), kwh, amount, rate,
kwh_per_day, baht_per_day (null when days unknown), kwh_change_pct and amount_change_pct versus the previous (older) bill
(null for the oldest), energy_charge, ft_charge, service_charge, vat, items_mismatch, note, source ("scan"/"manual"/"" from the note field is NOT needed - just pass note through).
Round: per-day values 2 decimals, pct 1 decimal. Division by zero -> null.
Add helper functions (e.g. `derive_period_start`, `calculate_per_day`, `calculate_change_pct`, `items_sum_mismatch`) and test each in tests/test_calc.py
(cases: first bill, bill with explicit period_start, bill without, zero previous kwh, negative Ft, mismatch / no mismatch).

## 4. Sensors (sensor.py)
- `sensor.electricity_bill_bill_history` attribute `bills` = the new richer list (keep state = bill count).
- `sensor.electricity_bill_last_bill_amount` attributes: add days, kwh_per_day, baht_per_day, amount_change_pct, plus the four item fields (null when missing). Keep every existing attribute.
- Keep unique_ids and entity ids unchanged.

## 5. Scan (scan.py)
Extend PROMPT and STRUCTURE with period_start (ISO, same BE->Gregorian rule), energy_charge, ft_charge, service_charge, vat
(all optional numbers, "use null if not clearly readable, never guess"). validate_extraction must accept/validate them (keep old behaviour for the old fields) and return them.

## 6. HTTP views + panel (views.py, frontend/panel.js)
- The add/scan endpoints pass the new fields through; scan result pre-fills the form.
- Panel add-bill form: after the 3 required inputs (period_end, kWh, amount) add a collapsible "รายละเอียดเพิ่มเติม (ไม่บังคับ)" section with period_start and the four charges + note. Thai labels as in the table above.
- Panel history: each row stays one line (date, kWh, THB, rate) and is expandable; expanded shows: period (start - end, N วัน), หน่วย/วัน, บาท/วัน, change vs previous bill (green down arrow / red up arrow with %), the four items (show "-" when null), a warning line "ผลรวมรายการไม่ตรงกับยอดรวม" when items_mismatch, and the note. Use the same styling approach/CSS variables the panel already uses (light + dark). No new external libraries.
- Keep the panel working on phone width.

## 7. Docs
README.md: document new fields/attributes with one example `electricity_bill.add_bill` call (example values clearly marked as example only). Bump manifest.json version 0.2.0 -> 0.3.0.

## Acceptance
- `python -m pytest tests` passes (existing + new tests). No new third-party dependency.
- Old stored bills (no new keys) load and render; history for them shows nulls, no exceptions.
- No change to entity ids, unique_ids, service names, storage key/version.
- Do not run anything outside this repo folder. Do not touch git; do not commit.
