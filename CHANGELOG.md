# Changelog

## 0.14.2

- Panel: removed the "take bill photo" button (the Android app opened only the gallery); use "choose photo" instead.

## 0.14.1

- Panel: "take bill photo" now also sends the legacy camera hint so the Android app opens the camera instead of only the gallery.

## 0.14.0
- Per-device sensors for every metered source: "<device> cycle energy" (kWh) and "<device> cycle cost" (kWh x the last bill's average rate), resetting every billing cycle.
- Automatic cycle start at midnight after the billing day when the bill has not been recorded yet; recording the bill later moves the cut to the bill's period end.
- Each bill stores per-meter energy for its period (`per_source_kwh` in the bill history); the panel lists it with cost when a bill is opened.
- Tests: 73 unit + 12 Home Assistant tests (device sensors reset with a new bill, automatic cycle start).
- Python change: restart Home Assistant once after updating.

## 0.13.1
- Cleaner device names in summaries and the panel: a trailing "kWh" is removed (e.g. "TCL Refrigerator Fridge TCL kWh" -> "TCL Refrigerator Fridge TCL").

## 0.13.0
- Reliability: tests that run the integration inside a real Home Assistant (pytest-homeassistant-custom-component, new CI job "HA tests": setup, sensors, Today Energy with an unavailable meter, reset button on a newer bill, summaries, Ft issue, diagnostics, config and options flows, panel no-cache).
- Diagnostics download; Repairs issues for a long-unavailable meter and an outdated Ft.
- Daily history backfilled from the recorder's daily statistics (up to 28 days).
- Service `electricity_bill.get_summary` (daily / weekly / cycle) returning a ready-made message; the billing-day event now carries a cycle summary message with a reminder.
- Python change: restart Home Assistant once after updating.

## 0.12.0
- Daily and weekly summaries: events `electricity_bill_daily_summary` (every day at `summary_hour`, default 21) and `electricity_bill_weekly_summary` (on `weekly_summary_day`, default Sunday), each with a ready-made `message` (Thai/English) and raw numbers; a rolling 70-day history of finished days is kept in the integration's storage.
- Python change: restart Home Assistant once after updating.

## 0.11.1
- Fix: after a Home Assistant restart `Today Energy` could show the whole cycle's energy, because the day-start record was taken while the main meter was still unavailable. The day is now only tracked while the meter has a value, and the old day records are dropped once (today's figure starts again from the current meter value).
- Python change: restart Home Assistant once after updating.

## 0.11.0
- Languages: Vietnamese, Malay, Indonesian and Russian added to the panel and to the configuration screens (with Thai and English). Translations were machine-written; native review of the new languages is welcome (panel texts in the `I18N` object of `frontend/panel.js`, config texts in `translations/*.json`).

## 0.10.0
- New sensors `Today Energy`, `Yesterday Energy`, `Daily Average Energy` (day start is tracked in the integration's own storage and survives restarts).
- Optional high-usage alert: option `high_usage_factor`, event `electricity_bill_high_usage` once per day.
- Panel: today tile (with yesterday) and a comparison with the previous cycle in the daily usage card when the recorder has the history.
- Python changes: restart Home Assistant once after updating.

## 0.9.0
- Panel: "Energy by device" card (stacked bar + list with kWh, estimated cost and share per sub-meter, plus the unmetered rest) and "Daily usage" card (kWh per day for the current cycle from the recorder's daily statistics, with the average line). Panel-only change: no Home Assistant restart needed after the update (from 0.8.2 on).

## 0.8.2
- The panel files are now served with `Cache-Control: no-cache` and an ETag, so a panel-only change shows after a page refresh and does not need a Home Assistant restart (code changes in the Python files still do).

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
