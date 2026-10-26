# Changelog

## 0.8.1
- Fix: the sidebar panel kept showing the old page after an update because browsers cached `panel.js`; the panel URL now carries the integration version (`panel.js?v=<version>`). After updating to 0.8.1 restart HA once and reload the page; later updates need no manual cache clearing.

## 0.8.0
- Panel i18n: Thai and English follow the Home Assistant language; numbers, dates and the currency symbol follow the HA locale and currency. New languages are added in the `I18N` object.
- Panel redesign: hero card with billing-cycle progress ring, gradient bar chart with grid, smooth kWh curve and entrance animations, colour-coded tiles, softer cards, reduced-motion support.
- Fix: grid children can shrink on narrow screens (chart no longer overflows).

## 0.7.0
- Panel: bill trend chart (amount bars + kWh line, last 12 bills), edit a saved bill in place (period end fixed; saved with replace), CSV export of the bill history (UTF-8 with BOM for Excel).
- Panel texts remain Thai only.

## 0.6.1
- Fix: the second options page ("Tariff, billing day and budget") failed to open with "Unknown error occurred" because the Ft field used a number step (0.0001) below Home Assistant's minimum (0.001); it now uses a free step.
- Docs: the billing-day sensor entity id is `sensor.electricity_bill_next_billing_day` (README said `next_cutoff_date`).

## 0.6.0
- Tariff profiles (`none` default, `thailand_residential`, `custom` tiers) with per-kWh adder (Ft), fixed monthly charge and tax; new sensors `Cycle Bill Estimate`, `Forecast Bill`, `Next Billing Day`.
- Billing day by month length (30 / 31 / February) with forecast to the next billing day.
- Events `electricity_bill_cutoff_day` (12:00 on the billing day) and `electricity_bill_budget_exceeded` (optional budget threshold, once per cycle).
- Monetary sensors follow the Home Assistant currency instead of a fixed THB.
- Panel: hero uses the tariff estimate and shows the forecast to the billing day.
- Verified against the real September and October 2026 PEA bills.

## 0.5.0
- Main (whole-house) meter option: cycle energy and cost use the main meter only; the other sources become sub-meters for the breakdown.
- New sensor `Cycle Unmetered Energy` (main meter minus sub-meters), created when a main meter is set.
- Optional main meter reset button, pressed automatically after a newer bill is recorded; energy used between the bill's period end and the reset is carried into the new cycle (negative baseline).
- Panel: tile for unmetered energy this cycle and an "Advanced" card to set a meter's baseline.
- Bills' measured energy now uses the main meter only when one is configured.

## 0.4.0
- Repository hygiene: MIT license, CI (HACS validation, hassfest, tests), tag-driven release workflow, brand icon, manifest keys sorted for hassfest.

## 0.3.1
- New service `electricity_bill.set_baseline`.
- Codeowner and README install URL; English README (`README.en.md`).

## 0.3.0
- Detailed bill data: period start, itemised charges (energy, Ft, service, VAT), per-day figures, change versus previous bill.

## 0.2.0
- Bill photo scan (AI Task) and one-page sidebar panel.

## 0.1.0
- Initial release: bills, effective rate, cycle estimate.
