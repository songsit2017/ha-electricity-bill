# SPEC v2: scan a bill photo and one-page UI for the `electricity_bill` integration

Read `SPEC.md` first (v1, already implemented and installed). This is an ADDITIVE change; do not break v1
services/entities. Everything runs inside Home Assistant (HA OS, Python 3.14, HA 2026.x).
The user's HA has NO vision model yet: the user will add the core "Anthropic" integration (creates an
`ai_task.*` entity) by themselves. Our code must degrade gracefully when no ai_task entity exists.

## Goal
One sidebar page "ค่าไฟ": the user takes/selects a photo of the electricity bill, the page uploads it, an AI
Task reads {period_end, kwh, amount}, the page shows the values in editable fields, the user presses save
(calls the existing `electricity_bill.add_bill`). Manual typing must also work with no AI at all.

## Backend (Python, files under custom_components/electricity_bill/)

### scan.py (new)
- `PROMPT` (Thai bill from MEA/PEA). Tell the model: extract (1) `period_end`: the end date of the billing
  period / date of the latest meter reading, as ISO `YYYY-MM-DD`, Gregorian calendar (if the year is Buddhist Era
  > 2400 subtract 543); (2) `kwh`: total units consumed this period (หน่วยที่ใช้); (3) `amount`: total amount to
  pay this month in THB including VAT (รวมเงินค่าไฟฟ้า / ยอดที่ต้องชำระเดือนนี้), NOT arrears, NOT a cumulative
  or previous balance; (4) `confidence`: low|medium|high; (5) `notes`: short string. Use null for anything not
  clearly readable. Never guess.
- `STRUCTURE`: dict used as the `structure` field of `ai_task.generate_data`:
  `{"period_end": {"description": ..., "selector": {"text": None}},
    "kwh": {"description": ..., "selector": {"number": {"min": 0, "max": 100000, "step": "any"}}},
    "amount": {...same...}, "confidence": {"selector": {"text": None}}, "notes": {"selector": {"text": None}}}`
  (all `required: False`).
- `async def async_scan_image(hass, entity_id, media_content_id, media_content_type) -> dict`:
  `await hass.services.async_call("ai_task", "generate_data", {"task_name": "Electricity bill scan",
   "entity_id": entity_id, "instructions": PROMPT, "structure": STRUCTURE,
   "attachments": [{"media_content_id": media_content_id, "media_content_type": media_content_type}]},
   blocking=True, return_response=True)`; the answer is `response["data"]`. Wrap errors in a
  `ScanError(translation_key)`.
- `def pick_ai_task_entity(hass, configured: str | None) -> str | None`: configured entity if it exists, else
  the first `ai_task.*` entity in `hass.states`, else None.
- Pure validation helper `validate_extraction(data, today)` in `calc.py` (no HA imports so it is unit-testable):
  returns `{"period_end": "YYYY-MM-DD"|None, "kwh": float|None, "amount": float|None, "confidence": str,
  "warnings": [codes]}`. Rules: parse date strictly, subtract 543 if year > 2400, reject future date > today+1
  (warning `date_in_future` and null the date); kwh must be 0 < v <= 5000 else null + `kwh_out_of_range`;
  amount 0 < v <= 100000 else null + `amount_out_of_range`; if both present and amount/kwh is outside
  1.5..12 THB/kWh add warning `rate_unusual`. Warnings are codes only (UI translates them to Thai).

### views.py (new) `ScanView(HomeAssistantView)`
- `url = "/api/electricity_bill/scan"`, `name = "api:electricity_bill:scan"`, `requires_auth = True`, POST.
- Read multipart field `file` with `await request.multipart()`, max 8 MiB (stop reading and return 413),
  accept only jpeg/png/webp by magic bytes (not by the client-declared type) else 415.
- Save the bytes into a media directory: `hass.config.media_dirs.get("local")` if configured, else `/media`;
  subfolder `electricity_bill_scans`; filename `<uuid4>.<ext>`; write with the executor (no blocking I/O in the
  loop). Media id: `media-source://media_source/local/electricity_bill_scans/<name>` (use the media dir key
  that actually matches). ALWAYS delete the file in a `finally` (executor) — bill images must not persist.
- If no ai_task entity: return 200 `{"ok": false, "error": "no_ai_task"}`.
- On success: `{"ok": true, "result": validate_extraction(...)}`; on `ScanError`: `{"ok": false, "error": code}`.
- Never log image bytes, never log the model response at INFO (DEBUG only, truncated).

### __init__.py
- Register the view once (guard with a flag in `hass.data[DOMAIN]`).
- Register the static path `/electricity_bill_panel` -> the `frontend/` folder next to the integration
  (`from homeassistant.components.http import StaticPathConfig`, `await hass.http.async_register_static_paths([...])`,
  `cache_headers=False`), only once.
- Register the panel with `homeassistant.components.panel_custom.async_register_panel(hass,
  webcomponent_name="electricity-bill-panel", frontend_url_path="electricity", module_url=
  "/electricity_bill_panel/panel.js", sidebar_title="ค่าไฟ", sidebar_icon="mdi:flash", require_admin=False,
  config={}, embed_iframe=False)` once; remove it on last-entry unload with
  `homeassistant.components.frontend.async_remove_panel(hass, "electricity")`. Catch/log (not raise) if the
  panel already exists.
- manifest.json: bump to `0.2.0`, `dependencies`: `["recorder", "http", "frontend", "panel_custom"]`,
  `after_dependencies`: `["ai_task", "media_source"]`.

### Options / config flow
- Add optional `ai_task_entity` (EntitySelector, domain `ai_task`, not required) to the options flow only;
  keep the config flow unchanged. Update strings.json + translations (en, th) for every new key, including the
  warning codes (not needed in strings, UI handles them) and the new option label.

### Pure-python tests (tests/test_calc.py additions or tests/test_validate.py)
Cases: BE year 2569 -> 2026; future date rejected; kwh/amount out of range -> None + warning; rate unusual
warning; all-null input; numeric strings with commas ("1,385.12").

## Frontend: custom_components/electricity_bill/frontend/panel.js (new, vanilla web component, no build step)
- `customElements.define("electricity-bill-panel", class extends HTMLElement {...})` with `set hass(h)`,
  `set narrow(v)`, `set panel(v)`; shadow DOM; use HA CSS variables for theming (dark/light) so it matches
  the HA theme; layout must work on a phone (single column < 700px) and desktop (two columns).
- Thai UI. Sections:
  1. **Status cards**: effective rate (`sensor.electricity_bill_effective_rate`), cycle kWh
     (`sensor.electricity_bill_cycle_energy`), cycle cost estimate (`..._cycle_cost_estimate`), last bill
     (`..._last_bill_amount`, `..._last_bill_energy`, `..._last_bill_unmetered_energy`). Read from `hass.states`;
     show "-" for unknown/unavailable.
  2. **Add bill**: big button "ถ่ายรูป/เลือกรูปบิล" -> `<input type="file" accept="image/*">` (also works with
     `capture` on phones; provide both a camera and a gallery option). Downscale client-side to max 1600 px on the
     long edge, JPEG q=0.85 via canvas before upload. POST via `hass.fetchWithAuth("/api/electricity_bill/scan",
     {method: "POST", body: formData})`. Show a spinner, then fill editable fields: วันสิ้นสุดรอบ (date input),
     หน่วย, ยอดเงิน, plus computed "บาท/หน่วย" live, confidence badge, and warning messages in Thai
     (`rate_unusual`, `date_in_future`, `kwh_out_of_range`, `amount_out_of_range`) and a clear message for
     `no_ai_task` ("ยังไม่ได้ตั้งค่า AI: Settings → Devices & services → Add integration → Anthropic;
     ระหว่างนี้พิมพ์ตัวเลขเองได้") and other errors. Fields are ALWAYS editable and also usable with no photo.
  3. **Save**: button disabled until date, kwh>0, amount>0. Calls `hass.callService("electricity_bill",
     "add_bill", {period_end, kwh, amount, note: "scan"|"manual"})`. If a bill with that date exists, ask
     "มีบิลวันที่นี้แล้ว แทนที่ไหม?" and call again with `replace: true`. Show success/failure toast text inline.
  4. **History**: table from `hass.states["sensor.electricity_bill_bill_history"].attributes.bills`
     (newest first): สิ้นสุดรอบ, หน่วย, บาท, บาท/หน่วย, and a delete button per row with a confirm dialog that calls
     `electricity_bill.remove_bill {period_end}`.
- Sanitise everything inserted into the DOM (use textContent / createElement, never innerHTML with data).
- No external network requests, no CDN scripts, no localStorage of bill data.

## Docs
- README: new "Scan a bill" section (Thai): add the Anthropic integration (Settings -> Devices & services ->
  Add integration -> Anthropic, paste API key, make sure an AI Task entity exists), privacy note (the photo is
  sent to the AI provider, the integration deletes its temporary copy immediately and stores no image),
  troubleshooting list.

## Acceptance criteria
1. `python -m compileall custom_components` clean; all JSON valid; strings/translations key parity.
2. `pytest tests` passes including the new validation tests (pure python, no HA import).
3. `panel.js` parses (`node --check` if available, else careful review) and uses no innerHTML with data.
4. v1 services and entities unchanged; existing config entries keep working without re-adding.
5. No secrets anywhere; no file written outside the media scan folder; scan file always deleted.

## Constraints
- Use only APIs that exist in current HA core: do NOT import constants you are not sure exist (v1 broke on
  `CURRENCY_THB` — use string literals instead). Prefer `hass.services.async_call` over importing integration
  internals. Do not touch anything outside `D:\HAOS\electricity_bill\`.
- Keep it small and boring: no build tooling, no npm packages, no extra Python dependencies.
