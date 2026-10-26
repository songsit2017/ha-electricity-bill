# Changelog

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
