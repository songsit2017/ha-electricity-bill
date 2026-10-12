# SPEC: Home Assistant custom integration `electricity_bill` (HACS-installable)

## Goal
Record each monthly electricity bill (kWh + baht + the date the billing period ended) and, from it, give the
user the REAL cost per unit and a running estimate of the current cycle. The billing cut-off date is NOT fixed:
it moves a few days each month depending on when the bill arrives, so every bill carries its own period end date.
Runs entirely inside Home Assistant (no external machine, no cloud, no extra pip dependencies).

## Context (facts about the user's HA, do not ask)
- HA 2025.x, Thai household, currency THB, timezone Asia/Bangkok, UI language Thai (provide th + en translations).
- HACS is already installed. Repo will be added as a HACS "custom repository" (type: Integration).
- Existing cumulative energy sensors (device_class energy, state_class total/total_increasing, kWh):
  `sensor.aircon_bedroom_kwh`, `sensor.aircon_workroom_kwh`, `sensor.speaker_kwh`, `sensor.water_pump_kwh`,
  `sensor.pc_kwh`, `sensor.outdoor_light_kwh`. They are the default suggestions in the config flow; the user picks
  any number of energy sensors via an entity selector (multiple=True, device_class energy).
- Today's flat price 4.40 THB/kWh is hard-coded elsewhere; this integration replaces that guess with
  amount / kWh from the latest bill. Fallback rate before the first bill = 4.40 (configurable).

## Scope (files, all under `D:\HAOS\electricity_bill\`)
```
custom_components/electricity_bill/
  __init__.py        setup/unload entry, register services, load Store
  manifest.json      domain electricity_bill, version 0.1.0, config_flow true, iot_class calculated,
                     dependencies ["recorder"], no requirements, codeowners []
  const.py
  config_flow.py     user step + options flow (same fields)
  store.py           thin wrapper over homeassistant.helpers.storage.Store (version 1)
  sensor.py
  services.yaml
  strings.json
  translations/en.json
  translations/th.json
hacs.json            {"name": "Electricity Bill", "render_readme": true}
README.md            install via HACS, setup, services, dashboard YAML example, how to point an existing
                     template sensor at sensor.<name>_effective_rate
tests/test_calc.py   pure-python tests for the calculation helpers (no HA import needed; keep the maths in
                     a separate module `calc.py` so it is testable without HA)
```

## Config (config flow + options)
- `name` (default "Electricity Bill")
- `sources`: list of entity ids (energy sensors)
- `fallback_rate`: float THB/kWh, default 4.40
Single instance allowed.

## Data model (Store, JSON)
```
{
  "bills": [   # sorted by period_end ascending
    {"id": "<uuid>", "period_start": "YYYY-MM-DD"|null, "period_end": "YYYY-MM-DD",
     "kwh": 312.0, "amount": 1385.12, "rate": 4.44,        # rate = amount / kwh
     "snapshot": {"sensor.pc_kwh": 123.456, ...},          # source totals at end of period_end
     "measured_kwh": 178.1,                                # sum(snapshot - previous snapshot)
     "note": ""}
  ],
  "cycle_snapshot": {"sensor.pc_kwh": 123.456, ...}        # baseline of the CURRENT cycle
}
```

## Services (domain `electricity_bill`)
1. `add_bill`
   - `period_end` (date, default today) : last day of the billing period the bill covers
   - `kwh` (number > 0), `amount` (number > 0 THB), `note` (optional text)
   - Snapshot rule: if period_end >= today use current source states. If period_end is in the past, read the
     source total at the end of that day from recorder long-term statistics
     (`recorder.statistics.statistics_during_period`, hour period, use the last `state` or `sum` on/before
     end of day). If statistics are missing for a source, fall back to the current state and log a warning;
     never raise because of one missing sensor.
   - Computes `rate = amount / kwh`, `measured_kwh = Σ(max(snapshot - previous_snapshot, 0))`.
   - Sets `cycle_snapshot` = the new snapshot (new cycle starts after period_end), stores, refreshes entities.
   - Reject duplicate period_end (raise ServiceValidationError) unless `replace: true` is passed.
2. `remove_bill` (`id` or `period_end`): delete a bill; recompute `measured_kwh` of the following bill;
   if it was the latest bill, restore `cycle_snapshot` to the previous bill's snapshot.
3. `reset_cycle`: set `cycle_snapshot` to current states without recording a bill.
All services return nothing; use `ServiceValidationError` with translated messages for bad input.

## Entities (sensor platform, one device "Electricity Bill")
Meter reset handling: if a source's current value < its snapshot treat the snapshot as 0 for that source
(counter was reset); never produce negative kWh.
| entity | state | unit / class | attributes |
|---|---|---|---|
| `cycle_kwh` | Σ(current − cycle_snapshot) over sources | kWh, energy, state_class total | per_source dict, cycle_start (period_end of last bill or null), days_in_cycle |
| `effective_rate` | latest bill amount/kWh, else fallback_rate | THB/kWh, monetary | source: "bill"/"fallback", based_on_period_end |
| `cycle_cost_estimate` | cycle_kwh * effective_rate, 2 dp | THB, monetary, state_class total | rate_used |
| `last_bill_amount` | latest amount | THB, monetary | period_start, period_end, kwh, rate, note |
| `last_bill_kwh` | latest kwh | kWh, energy | period_end |
| `last_bill_unmetered_kwh` | bill kwh − measured_kwh of that bill | kWh, energy | measured_kwh, share_metered_percent |
| `bill_history` | number of stored bills | none | `bills`: list (newest first, max 24) of {period_end, kwh, amount, rate} |
Entities update on state changes of the source sensors (async_track_state_change_event) and after any service
call. unique_id = f"{entry_id}_{key}". Use `has_entity_name` and translation keys (th + en names).

## Acceptance criteria
1. `python -m pytest tests` passes for `calc.py` (rate, measured kWh with meter reset, snapshot subtraction,
   duplicate detection, removing a bill).
2. All `.py` files import-clean (`python -m compileall custom_components`), no missing keys between
   strings.json / translations, valid JSON in manifest/hacs.json/translations.
3. Config flow creates an entry with only a `sources` list; options flow edits it; no YAML required.
4. Calling `add_bill` twice with different period_end values produces two history rows and the second bill's
   `measured_kwh` only counts consumption between the two snapshots.
5. Bill date moving (e.g. period_end 2026-09-25 then 2026-10-23) works; nothing assumes day-of-month 24.
6. No secrets, no network calls, no blocking I/O in the event loop (Store and recorder via async APIs;
   `get_instance(hass).async_add_executor_job` for statistics).
7. README shows the dashboard YAML (entities card + a tile/button that opens a more-info/service call with
   fields) and Thai usage instructions.

## Constraints
- Match current HA conventions: `ConfigEntry.runtime_data` pattern, `async_setup_entry`, typed code,
  Python 3.12/3.13, no deprecated APIs. Do not touch anything outside `D:\HAOS\electricity_bill\`.
- Do NOT change the existing helpers/utility_meters in the user's HA; only add the integration.
- Keep it small: no panels, no custom Lovelace card, no OCR.
