"""Pure-Python calculation helpers for electricity_bill.

This module contains all math and data manipulation logic without any Home Assistant
dependencies, allowing it to be tested in any standard Python environment.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import re
from typing import Any


def calculate_rate(amount: float, kwh: float, decimals: int = 4) -> float:
    """Calculate electricity rate (amount / kwh) rounded to specified decimals.

    Raises ValueError if kwh is less than or equal to 0.
    """
    if kwh <= 0:
        raise ValueError("kWh must be greater than 0")
    return round(float(amount) / float(kwh), decimals)


def calculate_source_delta(current: float, baseline: float) -> float:
    """Calculate consumption delta for a single energy source.

    Meter reset handling:
    If current < baseline, the counter was reset; baseline is treated as 0.
    Negative kWh is never produced.
    """
    curr = float(current) if current is not None else 0.0
    base = float(baseline) if baseline is not None else 0.0

    if curr < base:
        # Counter was reset; treat baseline as 0 for this source
        delta = curr
    else:
        delta = curr - base

    return max(0.0, round(delta, 4))


def calculate_snapshot_delta(
    current_snapshot: dict[str, float],
    previous_snapshot: dict[str, float] | None,
) -> tuple[float, dict[str, float]]:
    """Calculate measured kWh across sources between two snapshots.

    Returns (total_measured_kwh, per_source_delta).
    If previous_snapshot is None, returns 0.0 total.
    """
    if previous_snapshot is None:
        per_source = {s: 0.0 for s in current_snapshot}
        return 0.0, per_source

    total = 0.0
    per_source: dict[str, float] = {}

    for source, curr_val in current_snapshot.items():
        prev_val = previous_snapshot.get(source, 0.0)
        delta = calculate_source_delta(curr_val, prev_val)
        per_source[source] = delta
        total += delta

    return round(total, 4), per_source


def calculate_cycle_kwh(
    current_states: dict[str, float],
    cycle_snapshot: dict[str, float],
) -> tuple[float, dict[str, float]]:
    """Calculate consumption in the current cycle from baseline snapshot to current states.

    Returns (total_cycle_kwh, per_source_dict).
    """
    return calculate_snapshot_delta(current_states, cycle_snapshot)


def calculate_cycle_cost(cycle_kwh: float, effective_rate: float) -> float:
    """Calculate estimated cost for the current cycle rounded to 2 decimal places."""
    return round(max(0.0, float(cycle_kwh)) * float(effective_rate), 2)


def calculate_unmetered_kwh(
    bill_kwh: float,
    measured_kwh: float,
) -> tuple[float, float]:
    """Calculate unmetered kWh and percentage of bill measured.

    Returns (unmetered_kwh, share_metered_percent).
    """
    b_kwh = float(bill_kwh) if bill_kwh is not None else 0.0
    m_kwh = float(measured_kwh) if measured_kwh is not None else 0.0

    unmetered = round(b_kwh - m_kwh, 4)
    if b_kwh > 0:
        share_metered = round((m_kwh / b_kwh) * 100.0, 1)
    else:
        share_metered = 0.0

    return unmetered, share_metered


def calculate_days_in_cycle(
    cycle_start: str | None,
    current_date_str: str | None = None,
) -> int:
    """Calculate number of days elapsed in the current cycle.

    cycle_start is the period_end date of the last bill (YYYY-MM-DD).
    If cycle_start is None or invalid, returns 0.
    """
    if not cycle_start:
        return 0

    try:
        start_date = (
            datetime.strptime(cycle_start, "%Y-%m-%d").date()
            if isinstance(cycle_start, str)
            else cycle_start
        )
        if current_date_str:
            curr_date = (
                datetime.strptime(current_date_str, "%Y-%m-%d").date()
                if isinstance(current_date_str, str)
                else current_date_str
            )
        else:
            curr_date = date.today()

        return max(0, (curr_date - start_date).days)
    except (ValueError, TypeError):
        return 0


def recompute_bills(bills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort bills chronologically by period_end and recompute period_start and measured_kwh.

    Returns a new list of updated bill dictionaries.
    """
    sorted_bills = [dict(b) for b in sorted(bills, key=lambda b: str(b.get("period_end", "")))]

    for idx, bill in enumerate(sorted_bills):
        if idx == 0:
            bill["period_start"] = None
            bill["measured_kwh"] = 0.0
        else:
            prev_bill = sorted_bills[idx - 1]
            bill["period_start"] = prev_bill.get("period_end")
            delta, _ = calculate_snapshot_delta(
                bill.get("snapshot", {}),
                prev_bill.get("snapshot", {}),
            )
            bill["measured_kwh"] = delta

    return sorted_bills


def find_bill(
    bills: list[dict[str, Any]],
    bill_id: str | None = None,
    period_end: str | None = None,
) -> tuple[int | None, dict[str, Any] | None]:
    """Find a bill by id or period_end.

    Returns (index, bill) or (None, None).
    """
    for idx, bill in enumerate(bills):
        if bill_id is not None and bill.get("id") == bill_id:
            return idx, bill
        if period_end is not None and bill.get("period_end") == period_end:
            return idx, bill
    return None, None


def check_duplicate_period_end(
    bills: list[dict[str, Any]],
    period_end: str,
    replace: bool = False,
) -> bool:
    """Return True if a bill with period_end already exists and replace is False."""
    if replace:
        return False
    return any(b.get("period_end") == period_end for b in bills)


def add_bill_record(
    bills: list[dict[str, Any]],
    new_bill: dict[str, Any],
    replace: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Add or replace a bill in the list, keeping it sorted and recomputing deltas.

    Returns (updated_bills, added_or_updated_bill).
    Raises ValueError if duplicate period_end and replace is False.
    """
    period_end = new_bill.get("period_end")
    if not period_end:
        raise ValueError("Bill must include period_end")

    if check_duplicate_period_end(bills, period_end, replace=replace):
        raise ValueError(f"Duplicate period_end: {period_end}")

    new_list = [dict(b) for b in bills]
    bill_to_insert = dict(new_bill)

    if replace:
        existing_idx, existing_bill = find_bill(new_list, period_end=period_end)
        if existing_idx is not None and existing_bill is not None:
            if existing_bill.get("id"):
                bill_to_insert["id"] = existing_bill["id"]
            new_list[existing_idx] = bill_to_insert
        else:
            new_list.append(bill_to_insert)
    else:
        new_list.append(bill_to_insert)

    recomputed = recompute_bills(new_list)
    _, added = find_bill(recomputed, period_end=period_end)
    if added is None:
        added = bill_to_insert

    return recomputed, added


def remove_bill_record(
    bills: list[dict[str, Any]],
    bill_id: str | None = None,
    period_end: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, float] | None]:
    """Remove a bill by id or period_end.

    Returns (remaining_bills, removed_bill, restored_cycle_snapshot).
    If the removed bill was the latest bill, restored_cycle_snapshot is the new latest
    bill's snapshot (or {} if no bills remain).
    If it was not the latest bill, restored_cycle_snapshot is None.

    Raises ValueError if neither identifier provided or bill not found.
    """
    if not bill_id and not period_end:
        raise ValueError("Either id or period_end must be provided")

    sorted_bills = [dict(b) for b in sorted(bills, key=lambda b: str(b.get("period_end", "")))]
    idx, target_bill = find_bill(sorted_bills, bill_id=bill_id, period_end=period_end)

    if idx is None or target_bill is None:
        raise ValueError("Bill not found")

    was_latest = idx == len(sorted_bills) - 1
    removed = sorted_bills.pop(idx)
    remaining = recompute_bills(sorted_bills)

    restored_snapshot: dict[str, float] | None = None
    if was_latest:
        if remaining:
            restored_snapshot = dict(remaining[-1].get("snapshot", {}))
        else:
            restored_snapshot = {}

    return remaining, removed, restored_snapshot


def format_bill_history(
    bills: list[dict[str, Any]],
    max_items: int = 24,
) -> list[dict[str, Any]]:
    """Format bill history for attribute display: newest first, max items, specific keys."""
    sorted_desc = sorted(bills, key=lambda b: str(b.get("period_end", "")), reverse=True)
    history: list[dict[str, Any]] = []

    for bill in sorted_desc[:max_items]:
        history.append({
            "period_end": bill.get("period_end"),
            "kwh": bill.get("kwh"),
            "amount": bill.get("amount"),
            "rate": bill.get("rate"),
        })

    return history


def validate_extraction(
    data: dict[str, Any] | None,
    today: date | None = None,
) -> dict[str, Any]:
    """Validate and normalize bill data extracted by AI task.

    Pure validation helper with no Home Assistant dependencies.
    Rules:
    - parse date strictly, subtract 543 if year > 2400, reject future date > today+1
      (warning 'date_in_future' and null the date)
    - kwh must be 0 < v <= 5000 else null + warning 'kwh_out_of_range'
    - amount must be 0 < v <= 100000 else null + warning 'amount_out_of_range'
    - if both present and amount/kwh is outside 1.5..12 THB/kWh add warning 'rate_unusual'
    - handles numeric strings with commas (e.g. '1,385.12')
    - handles all-null input
    """
    if today is None:
        today = date.today()

    input_data = data if isinstance(data, dict) else {}
    warnings: list[str] = []

    # 1. Parse date
    period_end: str | None = None
    raw_date = input_data.get("period_end")

    parsed_date: date | None = None
    if isinstance(raw_date, datetime):
        parsed_date = raw_date.date()
    elif isinstance(raw_date, date):
        parsed_date = raw_date
    elif isinstance(raw_date, str) and raw_date.strip():
        s = raw_date.strip()
        m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
        if m:
            try:
                y = int(m.group(1))
                mon = int(m.group(2))
                d = int(m.group(3))
                if y > 2400:
                    y -= 543
                parsed_date = date(y, mon, d)
            except ValueError:
                parsed_date = None

    if parsed_date is not None and parsed_date.year > 2400:
        try:
            parsed_date = date(parsed_date.year - 543, parsed_date.month, parsed_date.day)
        except ValueError:
            parsed_date = None

    if parsed_date is not None:
        if parsed_date > today + timedelta(days=1):
            period_end = None
            warnings.append("date_in_future")
        else:
            period_end = parsed_date.isoformat()
    else:
        period_end = None

    # Helper for numeric parsing
    def _parse_num(val: Any) -> float | None:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            clean = val.replace(",", "").strip()
            if not clean:
                return None
            try:
                return float(clean)
            except (ValueError, TypeError):
                return None
        return None

    # 2. Parse kwh (0 < v <= 5000)
    kwh: float | None = None
    raw_kwh = input_data.get("kwh")
    if raw_kwh is not None and str(raw_kwh).strip() != "":
        num_kwh = _parse_num(raw_kwh)
        if num_kwh is not None and 0 < num_kwh <= 5000:
            kwh = round(num_kwh, 4)
        else:
            kwh = None
            warnings.append("kwh_out_of_range")
    else:
        kwh = None

    # 3. Parse amount (0 < v <= 100000)
    amount: float | None = None
    raw_amount = input_data.get("amount")
    if raw_amount is not None and str(raw_amount).strip() != "":
        num_amount = _parse_num(raw_amount)
        if num_amount is not None and 0 < num_amount <= 100000:
            amount = round(num_amount, 2)
        else:
            amount = None
            warnings.append("amount_out_of_range")
    else:
        amount = None

    # 4. Unusual rate warning: 1.5 <= rate <= 12.0
    if kwh is not None and amount is not None and kwh > 0:
        rate = amount / kwh
        if rate < 1.5 or rate > 12.0:
            warnings.append("rate_unusual")

    # 5. Confidence
    raw_conf = input_data.get("confidence")
    if isinstance(raw_conf, str) and raw_conf.strip().lower() in ("low", "medium", "high"):
        confidence = raw_conf.strip().lower()
    else:
        confidence = "low"

    return {
        "period_end": period_end,
        "kwh": kwh,
        "amount": amount,
        "confidence": confidence,
        "warnings": warnings,
    }
