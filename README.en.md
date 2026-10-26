# Electricity Bill (electricity bill tracker for Home Assistant)

[ภาษาไทย](README.md) | **English**

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)

A Home Assistant custom integration that records your monthly electricity bill (kWh + amount in baht + billing period end date) to work out your **real effective rate per kWh** and a live estimate of the current billing cycle's cost.

---

## Key features

- **Flexible billing cut-off**: the bill date is not the same every month (e.g. 25 Sep, then 23 Oct); every bill carries its own period end date.
- **Real cost per unit**: `THB / kWh` is calculated from your latest actual bill instead of a guessed fixed 4.40.
- **Running cycle estimate**: energy used since the cycle started multiplied by the real rate.
- **Automatic history lookup**: if you enter a past period end date, the meter reading at the end of that day is taken from the HA Recorder long-term statistics.
- **Meter reset handling**: if a smart plug or meter is reset to 0, the cycle energy never goes negative.
- **Bill details (v0.3+)**: period start, base energy charge, Ft, service charge and VAT, plus per-day figures and change versus the previous bill (see "Bill details").
- **"ค่าไฟ" sidebar panel**: enter a bill by hand, or photograph/upload it and let an AI Task (e.g. Anthropic) read the values (optional).
- **Set the starting point yourself (v0.3.1)**: the `set_baseline` service (and the "Advanced" card in the panel, v0.5), for newly added sensors such as a whole-house breaker.
- **Whole-house main meter (v0.5)**: one main meter drives the cycle energy and cost, sub-meters give the per-device breakdown, a live "unmetered this cycle" sensor, and an optional reset button that is pressed automatically after you record a bill.
- **Tariff profiles (v0.6)**: choose "none" (default, works anywhere), "Thailand residential" or "custom" to estimate the full bill from tiers + a per-kWh adder (e.g. Ft) + fixed monthly charge + tax, and forecast it to the billing day (see "Tariff and forecast").
- **"ค่าไฟ" panel (v0.7)**: bill chart (amount and kWh for the last 12 bills), edit a saved bill (Edit button in the history rows; the period end date cannot be changed), CSV export of the history, usable on a phone.
- **Thai and English UI** . The "ค่าไฟ" panel follows the Home Assistant language (Thai / English; other languages show English) and the currency set in HA. Add a language in the `I18N` object of `frontend/panel.js`.
- **New look (v0.8)**: summary card with a billing-cycle progress ring, gradient bar chart with a smooth kWh curve and animations, colour-coded tiles.

---

## Installation via HACS

1. In **Home Assistant** open **HACS** > **Integrations**.
2. Open the three-dot menu (top right) and choose **Custom repositories**.
3. Enter the repository URL `https://github.com/songsit2017/ha-electricity-bill`, set the category to **Integration** and press **Add**.
4. Search for **Electricity Bill** and press **Download**.
5. Restart Home Assistant.

When a new version is published as a GitHub Release, HACS shows it on the Updates page of Home Assistant and you can update with one click (restart HA afterwards).

---

## Configuration

1. Go to **Settings** > **Devices & services** > **Add integration**.
2. Search for **Electricity Bill**.
3. Fill in:
   - **Name**: device name (default `Electricity Bill`).
   - **Source Energy Sensors**: the energy sensors (kWh) to track, e.g. `sensor.aircon_bedroom_kwh`, `sensor.pc_kwh`, `sensor.water_pump_kwh`.
   - **Fallback Rate**: rate used before the first bill is recorded (default `4.40` THB/kWh).
   - **AI Task Entity** (optional): an `ai_task.*` entity used to read bills from a photo.
4. You can change the sensor list and fallback rate at any time with **Configure**.

> **Do you have a whole-house meter/breaker (v0.5)?** In **Configure** set it as the **Main meter** and put your sub-meters (aircon, pump, ...) in Source Energy Sensors:
> - Cycle energy and cost come from the main meter only; sub-meters are never double counted and are used for the breakdown.
> - You get `sensor.electricity_bill_cycle_unmetered_energy` = main meter energy minus the sum of the sub-meters this cycle (never negative).
> - **Main meter reset button** (optional, e.g. `button.main_breaker_energy_reset`): when you record a bill that is newer than the previous one the button is pressed once, and the energy used between the bill's period end and the reset is carried into the new cycle.
> - Without a main meter nothing changes (all sources are summed). Do not select a whole-house meter and its sub-meters as plain sources together, the energy would be counted twice.

---

## Entities

All sensors belong to the **Electricity Bill** device:

| Entity ID | Name | Unit | Description | Key attributes |
|---|---|---|---|---|
| `sensor.electricity_bill_cycle_energy` | Cycle Energy | kWh | Energy used in the current billing cycle | `per_source`, `cycle_start`, `days_in_cycle` |
| `sensor.electricity_bill_cycle_unmetered_energy` | Cycle Unmetered Energy | kWh | Energy this cycle not covered by sub-meters (main − sub-meters); only created when a main meter is set | `main_meter`, `submetered_kwh` |
| `sensor.electricity_bill_cycle_bill_estimate` | Cycle Bill Estimate | HA currency | Estimated full bill of the current cycle for the chosen tariff profile (no profile = units × effective rate) | `energy_charge`, `ft_charge`, `service_charge`, `subtotal`, `vat`, `total` |
| `sensor.electricity_bill_forecast_bill` | Forecast Bill | HA currency | Bill forecast to the next billing day from this cycle's daily average (needs the billing day set) | `forecast_kwh`, `kwh_per_day`, `cycle_days`, `cutoff_date` |
| `sensor.electricity_bill_next_billing_day` | Next Billing Day | date | Next billing (cut-off) day (needs the billing day set) | - |
| `sensor.electricity_bill_effective_rate` | Effective Rate | THB/kWh | Real rate per unit from the latest bill | `source` ("bill"/"fallback"), `based_on_period_end` |
| `sensor.electricity_bill_cycle_cost_estimate` | Cycle Cost Estimate | THB | Estimated cost of the current cycle (`cycle energy * rate`) | `rate_used` |
| `sensor.electricity_bill_last_bill_amount` | Last Bill Amount | THB | Total amount of the latest bill | `period_start`, `period_end`, `kwh`, `rate`, `note` |
| `sensor.electricity_bill_last_bill_energy` | Last Bill Energy | kWh | Units on the latest bill | `period_end` |
| `sensor.electricity_bill_last_bill_unmetered_energy` | Last Bill Unmetered Energy | kWh | Energy not covered by a meter (`bill kWh - measured kWh`) | `measured_kwh`, `share_metered_percent` |
| `sensor.electricity_bill_bill_history` | Bill History | - | Number of stored bills | `bills` (up to 24 bills, newest first) |

---

## Services

### 1. `electricity_bill.add_bill`
Records a monthly bill, calculates the rate and starts a new measuring cycle.

```yaml
action: electricity_bill.add_bill
data:
  period_end: "2026-10-23" # last day of the billing period on the invoice (optional, default today)
  kwh: 312.0               # total units on the bill
  amount: 1385.12          # total amount on the bill (THB)
  note: "October bill"     # optional note
  replace: false           # allow overwriting a bill with the same period end date
  # Optional detail fields (period_start, energy_charge, ft_charge, service_charge, vat): see "Bill details"
```

### 2. `electricity_bill.remove_bill`
Removes a bill by `id` or by `period_end`.

```yaml
action: electricity_bill.remove_bill
data:
  period_end: "2026-10-23"
  # or use id: "uuid-of-the-bill"
```

### 3. `electricity_bill.reset_cycle`
Resets the cycle starting point to the current meter values immediately, without recording a bill.

```yaml
action: electricity_bill.reset_cycle
```

### 4. `electricity_bill.set_baseline`
Sets the cycle starting point of one source sensor to a given meter value (cycle energy = current value − baseline). Use it when you have just added a sensor whose counter already started from 0 (for example a new main breaker) and you want its whole accumulated total to count in this cycle.

```yaml
action: electricity_bill.set_baseline
data:
  entity_id: sensor.main_breaker_energy  # must be one of the Source Energy Sensors
  value: 0                               # meter value at the start of the cycle (default 0)
```

---

## Tariff and forecast (v0.6)

On the second page of **Configure** ("Tariff, billing day and budget") choose a **tariff profile**:

| Profile | What it does |
|---|---|
| `none` (default) | Works in any country. Estimates use the real effective rate of your last bill (units × THB/kWh); nothing else to fill in. |
| `thailand_residential` | Thai PEA/MEA residential tariff from the September 2026 bill: first 200 kWh 3.0000, 201-400 kWh 4.1584, above 400 kWh 4.3583 THB/kWh (users of 150 kWh or less use the small-user table 2.3488 / 2.9882 first) + Ft + monthly service charge + 7% VAT. Defaults: Ft 0.1623, service charge 24.62, billing day 24 (30-day months) / 25 (31-day months), all editable. Checked against the real Sep and Oct 2026 bills: energy charge matches within 5 satang. |
| `custom` | Your own tiers, e.g. `200:3.0, 400:4.1584, 4.3583` (cumulative upper limit in kWh : rate per kWh; the last tier is open-ended) plus a per-kWh adder, a fixed monthly charge and a tax percentage. |

- **Billing day**: set the day of month for 30-day months / 31-day months / February (use the same day in all three for a fixed day). Once set you get **Next Billing Day** and **Forecast Bill** sensors. Leave empty to disable them.
- **Currency**: monetary sensors use the currency configured in Home Assistant (Settings > System > General).
- **Budget**: set `budget_threshold` and the event `electricity_bill_budget_exceeded` is fired once per cycle when the estimated bill reaches it (data: `threshold`, `bill_estimate`, `cycle_kwh`, `cycle_start`).
- **Billing-day event**: at 12:00 on the billing day the event `electricity_bill_cutoff_day` is fired (data: `cutoff_date`, `cycle_kwh`, `bill_estimate`, `forecast_bill`).

Example automation using the event (replace `notify.mobile_app_xxx` with your notifier):

```yaml
triggers:
  - trigger: event
    event_type: electricity_bill_cutoff_day
actions:
  - action: notify.mobile_app_xxx
    data:
      message: >-
        Billing day: {{ trigger.event.data.cycle_kwh | round(1) }} kWh used,
        about {{ trigger.event.data.bill_estimate }} so far
```

> The built-in Thai tariff follows the announced PEA/MEA rates of September 2026. If rates change, use the `custom` profile right away without waiting for a new release.

---

## Replacing a fixed-price template sensor with the real rate

If you have a template sensor using a fixed 4.40 THB:

```yaml
# Before: fixed 4.40 THB/unit
sensor:
  - name: "Aircon Bedroom Cost Today"
    unit_of_measurement: "THB"
    state: >
      {{ (states('sensor.aircon_bedroom_daily_kwh') | float(0) * 4.40) | round(2) }}
```

you can switch to `sensor.electricity_bill_effective_rate`:

```yaml
# After: real rate from the latest bill
sensor:
  - name: "Aircon Bedroom Cost Today"
    unit_of_measurement: "THB"
    state: >
      {% set rate = states('sensor.electricity_bill_effective_rate') | float(4.40) %}
      {% set kwh = states('sensor.aircon_bedroom_daily_kwh') | float(0) %}
      {{ (kwh * rate) | round(2) }}
```

---

## Dashboard examples

### 1. Entities card

```yaml
type: entities
title: "⚡ Current cycle electricity"
show_header_toggle: false
entities:
  - entity: sensor.electricity_bill_cycle_cost_estimate
    name: "Estimated cost this cycle"
    icon: mdi:cash-multiple
  - entity: sensor.electricity_bill_cycle_energy
    name: "Energy used this cycle"
    icon: mdi:lightning-bolt
  - entity: sensor.electricity_bill_effective_rate
    name: "Real rate per unit"
    icon: mdi:tag-text-outline
  - type: divider
  - entity: sensor.electricity_bill_last_bill_amount
    name: "Last bill amount"
    icon: mdi:receipt-text
  - entity: sensor.electricity_bill_last_bill_energy
    name: "Last bill units"
    icon: mdi:counter
  - entity: sensor.electricity_bill_last_bill_unmetered_energy
    name: "Unmetered energy"
    icon: mdi:help-circle-outline
```

### 2. Quick-record button (tile with action)

```yaml
type: tile
entity: sensor.electricity_bill_last_bill_amount
name: "Record a new bill"
icon: mdi:plus-circle
tap_action:
  action: call-service
  service: electricity_bill.add_bill
  data:
    kwh: 300
    amount: 1320
    note: "Quick entry"
```

---

## How to use

1. **When the monthly bill arrives**:
   - Open **Developer tools** > **Actions**, or the **"ค่าไฟ"** sidebar panel.
   - Choose `electricity_bill.add_bill`.
   - Enter the **units (kwh)** and the **total amount (amount)** from the invoice.
   - Enter the **period end date (period_end)** shown on the invoice (e.g. `2026-10-23`).
   - Confirm. The real rate per unit is calculated immediately and a new cycle starts.
2. **During the month**:
   - Watch `sensor.electricity_bill_cycle_cost_estimate` for the cost so far.
   - Watch `sensor.electricity_bill_last_bill_unmetered_energy` to see how much consumption is not covered by any meter.

---

## Scanning a bill and the web UI

From version 0.2.0 there is a sidebar panel named **"ค่าไฟ"** where you can photograph or upload a bill and let an AI read it, then save it on one page.

### 1. Enabling AI Task (Anthropic integration)
1. Go to **Settings** > **Devices & services** > **Add integration**.
2. Search for and select **Anthropic**.
3. Enter the API key and confirm. An `ai_task.*` entity is created automatically.
4. Electricity Bill detects the `ai_task` entity automatically (or choose one in **Configure**).
5. *Note: without AI Task you can still open the panel and type the numbers, date and amount yourself.*

### 2. Privacy
- The bill photo is sent to your configured AI provider (e.g. Anthropic) only to extract the period end date, units (kWh) and amount (THB).
- The image is written to a temporary media folder (`electricity_bill_scans`) and **deleted immediately** after processing; no image is kept in permanent storage.
- Nothing is sent to any server other than the AI provider you configured in Home Assistant.

### 3. Troubleshooting
- **"AI is not set up" message**: there is no `ai_task.*` entity yet. Add the Anthropic integration as above, or type the values by hand.
- **"Image larger than 8 MB" (`file_too_large`)**: the panel shrinks the image before sending (max 1,600 px, quality 0.85). If you still see this, make sure the image is no larger than 8 MiB.
- **"Unsupported file type" (`unsupported_media_type`)**: only JPEG (`.jpg`), PNG (`.png`) and WebP (`.webp`) are accepted.
- **Validation warnings** (`rate_unusual`, `date_in_future`, `kwh_out_of_range`, `amount_out_of_range`):
  - `rate_unusual`: the extracted rate is outside 1.5 - 12 THB/unit.
  - `date_in_future`: the extracted date is in the future (later than tomorrow).
  - `kwh_out_of_range`: units outside 1 - 5,000 kWh.
  - `amount_out_of_range`: amount outside 1 - 100,000 THB.
  *All fields can be edited before you press save.*
- **Saving the same date twice**: if a bill with that period end already exists the panel asks whether to replace it; confirming overwrites the old bill.

## Bill details (v0.3.0+)

`electricity_bill.add_bill` also accepts these optional fields: `period_start`, `energy_charge` (base energy charge), `ft_charge` (Ft, may be negative), `service_charge`, `vat`.
The bill history (`sensor.electricity_bill_bill_history`, attribute `bills`) additionally contains `days`, `kwh_per_day`, `baht_per_day`, `kwh_change_pct`, `amount_change_pct` (versus the previous bill) and `items_mismatch` when the itemised charges do not add up to the total.
If `period_start` is not given, the day after the previous bill's period end is used. Older bills without these fields keep working.

Example (numbers are illustrative only, not a real bill):

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
