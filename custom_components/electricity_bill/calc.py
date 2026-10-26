"""Pure-Python calculation helpers for electricity_bill.

This module contains all math and data manipulation logic without any Home Assistant
dependencies, allowing it to be tested in any standard Python environment.
"""
from __future__ import annotations

from collections.abc import Iterable

from datetime import date, datetime, timedelta
import math
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
    only: Iterable[str] | None = None,
) -> tuple[float, dict[str, float]]:
    """Calculate measured kWh across sources between two snapshots.

    Returns (total_measured_kwh, per_source_delta).
    If previous_snapshot is None, returns 0.0 total.
    If ``only`` is given, only those sources are summed into the total; every
    source still appears in the per-source dict (used when a whole-house main
    meter is the total and the other sources are sub-meters for breakdown).
    A baseline may be negative: it carries energy that was used before the
    counter was reset to 0.
    """
    only_set = set(only) if only is not None else None
    if previous_snapshot is None:
        per_source = {s: 0.0 for s in current_snapshot}
        return 0.0, per_source

    total = 0.0
    per_source: dict[str, float] = {}

    for source, curr_val in current_snapshot.items():
        prev_val = previous_snapshot.get(source, 0.0)
        delta = calculate_source_delta(curr_val, prev_val)
        per_source[source] = delta
        if only_set is None or source in only_set:
            total += delta

    return round(total, 4), per_source


def calculate_cycle_kwh(
    current_states: dict[str, float],
    cycle_snapshot: dict[str, float],
    only: Iterable[str] | None = None,
) -> tuple[float, dict[str, float]]:
    """Calculate consumption in the current cycle from baseline snapshot to current states.

    Returns (total_cycle_kwh, per_source_dict). ``only`` limits the total to the
    given sources (see calculate_snapshot_delta).
    """
    return calculate_snapshot_delta(current_states, cycle_snapshot, only=only)


def calculate_cycle_unmetered_kwh(
    main_kwh: float,
    per_source: dict[str, float],
    main_meter: str,
) -> tuple[float, float]:
    """Return (submetered_kwh, unmetered_kwh) for a cycle with a main meter.

    submetered = sum of every other source's cycle energy;
    unmetered = main - submetered, never negative.
    """
    sub_total = round(sum(v for k, v in per_source.items() if k != main_meter), 4)
    return sub_total, round(max(0.0, float(main_kwh) - sub_total), 4)


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


def derive_period_start(
    manual_start: Any,
    prev_period_end: Any = None,
) -> str | None:
    """Return the period start to display.

    manual_start (the start the user typed or the scan read, stored as `period_start_manual`) wins;
    otherwise previous bill's period_end + 1 day; otherwise None. Accepts a bill dict as first argument.
    """
    if isinstance(manual_start, dict):
        manual_start = manual_start.get("period_start_manual")
    if isinstance(prev_period_end, dict):
        prev_period_end = prev_period_end.get("period_end")
    if manual_start:
        return str(manual_start)
    if not prev_period_end:
        return None
    try:
        prev_date = (
            datetime.strptime(str(prev_period_end), "%Y-%m-%d").date()
            if isinstance(prev_period_end, str)
            else prev_period_end
        )
        return (prev_date + timedelta(days=1)).isoformat()
    except (ValueError, TypeError):
        return None


def calculate_days(
    period_start: str | date | None,
    period_end: str | date | None,
) -> int | None:
    """Calculate number of days in billing period ((period_end - period_start).days + 1).

    Returns None if either date is None or invalid, or if start > end.
    """
    if not period_start or not period_end:
        return None

    try:
        s_date = (
            datetime.strptime(str(period_start), "%Y-%m-%d").date()
            if isinstance(period_start, str)
            else period_start
        )
        e_date = (
            datetime.strptime(str(period_end), "%Y-%m-%d").date()
            if isinstance(period_end, str)
            else period_end
        )
        if s_date > e_date:
            return None
        return (e_date - s_date).days + 1
    except (ValueError, TypeError):
        return None


def calculate_per_day(
    val: float | None,
    days: int | None,
    decimals: int = 2,
) -> float | None:
    """Calculate value per day rounded to decimals. Returns None on division by zero or invalid inputs."""
    if val is None or days is None:
        return None
    try:
        d = int(days)
        if d <= 0:
            return None
        return round(float(val) / float(d), decimals)
    except (ZeroDivisionError, ValueError, TypeError):
        return None


def calculate_change_pct(
    current: float | None,
    previous: float | None,
    decimals: int = 1,
) -> float | None:
    """Calculate percentage change ((current - previous) / previous * 100).

    Returns None on division by zero or when either value is None.
    """
    if current is None or previous is None:
        return None
    try:
        prev_val = float(previous)
        if prev_val == 0.0:
            return None
        curr_val = float(current)
        pct = ((curr_val - prev_val) / prev_val) * 100.0
        return round(pct, decimals)
    except (ZeroDivisionError, ValueError, TypeError):
        return None


def items_sum_mismatch(
    amount: float | None,
    energy_charge: float | None,
    ft_charge: float | None,
    service_charge: float | None,
    vat: float | None,
    tolerance: float = 0.05,
) -> bool:
    """Return True if all four charge items are present and |sum - amount| > tolerance."""
    if (
        amount is None
        or energy_charge is None
        or ft_charge is None
        or service_charge is None
        or vat is None
    ):
        return False
    try:
        total = float(energy_charge) + float(ft_charge) + float(service_charge) + float(vat)
        return abs(total - float(amount)) > tolerance
    except (ValueError, TypeError):
        return False


def recompute_bills(
    bills: list[dict[str, Any]],
    only: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
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
                only=only,
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
    only: Iterable[str] | None = None,
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

    recomputed = recompute_bills(new_list, only=only)
    _, added = find_bill(recomputed, period_end=period_end)
    if added is None:
        added = bill_to_insert

    return recomputed, added


def remove_bill_record(
    bills: list[dict[str, Any]],
    bill_id: str | None = None,
    period_end: str | None = None,
    only: Iterable[str] | None = None,
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
    remaining = recompute_bills(sorted_bills, only=only)

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
    """Format bill history for attribute display: newest first, max items, rich derived fields."""
    sorted_asc = sorted(bills, key=lambda b: str(b.get("period_end", "")))
    formatted_asc: list[dict[str, Any]] = []

    for idx, bill in enumerate(sorted_asc):
        prev_bill = sorted_asc[idx - 1] if idx > 0 else None
        p_start = derive_period_start(
            bill.get("period_start_manual"),
            prev_bill.get("period_end") if prev_bill else None,
        )
        p_end = bill.get("period_end")
        days = calculate_days(p_start, p_end)

        kwh = bill.get("kwh")
        amount = bill.get("amount")
        rate = bill.get("rate")

        kwh_per_day = calculate_per_day(kwh, days)
        baht_per_day = calculate_per_day(amount, days)

        prev_kwh = prev_bill.get("kwh") if prev_bill else None
        prev_amount = prev_bill.get("amount") if prev_bill else None

        kwh_change_pct = calculate_change_pct(kwh, prev_kwh)
        amount_change_pct = calculate_change_pct(amount, prev_amount)

        energy_charge = bill.get("energy_charge")
        ft_charge = bill.get("ft_charge")
        service_charge = bill.get("service_charge")
        vat = bill.get("vat")

        mismatch = items_sum_mismatch(amount, energy_charge, ft_charge, service_charge, vat)

        formatted_asc.append({
            "id": bill.get("id"),
            "period_start": p_start,
            "period_end": p_end,
            "days": days,
            "kwh": kwh,
            "amount": amount,
            "rate": rate,
            "kwh_per_day": kwh_per_day,
            "baht_per_day": baht_per_day,
            "kwh_change_pct": kwh_change_pct,
            "amount_change_pct": amount_change_pct,
            "energy_charge": energy_charge,
            "ft_charge": ft_charge,
            "service_charge": service_charge,
            "vat": vat,
            "items_mismatch": mismatch,
            "note": str(bill.get("note", "")),
        })

    return list(reversed(formatted_asc))[:max_items]


def validate_extraction(
    data: dict[str, Any] | None,
    today: date | None = None,
) -> dict[str, Any]:
    """Validate and normalize bill data extracted by AI task.

    Pure validation helper with no Home Assistant dependencies.
    Rules:
    - parse period_end strictly, subtract 543 if year > 2400, reject future date > today+1
      (warning 'date_in_future' and null the date)
    - parse period_start strictly, subtract 543 if year > 2400, reject future date > today+1
      (warning 'date_in_future' and null the date)
    - if period_start and period_end both valid and period_start > period_end -> warning 'invalid_period'
    - kwh must be 0 < v <= 5000 else null + warning 'kwh_out_of_range'
    - amount must be 0 < v <= 100000 else null + warning 'amount_out_of_range'
    - energy_charge must be finite and >= 0 else null
    - ft_charge must be finite (may be negative) else null
    - service_charge must be finite and >= 0 else null
    - vat must be finite and >= 0 else null
    - if both kwh and amount present and amount/kwh is outside 1.5..12 THB/kWh add warning 'rate_unusual'
    - handles numeric strings with commas (e.g. '1,385.12')
    - handles all-null input
    """
    if today is None:
        today = date.today()

    input_data = data if isinstance(data, dict) else {}
    warnings: list[str] = []

    def _parse_date(raw_date: Any) -> tuple[str | None, bool]:
        if raw_date is None:
            return None, False

        parsed: date | None = None
        if isinstance(raw_date, datetime):
            parsed = raw_date.date()
        elif isinstance(raw_date, date):
            parsed = raw_date
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
                    parsed = date(y, mon, d)
                except ValueError:
                    parsed = None

        if parsed is not None and parsed.year > 2400:
            try:
                parsed = date(parsed.year - 543, parsed.month, parsed.day)
            except ValueError:
                parsed = None

        if parsed is not None:
            if parsed > today + timedelta(days=1):
                return None, True
            return parsed.isoformat(), False
        return None, False

    # 1. Parse dates
    period_end, end_future = _parse_date(input_data.get("period_end"))
    if end_future and "date_in_future" not in warnings:
        warnings.append("date_in_future")

    period_start, start_future = _parse_date(input_data.get("period_start"))
    if start_future and "date_in_future" not in warnings:
        warnings.append("date_in_future")

    if period_start and period_end and period_start > period_end:
        warnings.append("invalid_period")

    # Helper for numeric parsing
    def _parse_num(val: Any) -> float | None:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            f = float(val)
            return f if math.isfinite(f) else None
        if isinstance(val, str):
            clean = val.replace(",", "").strip()
            if not clean:
                return None
            try:
                f = float(clean)
                return f if math.isfinite(f) else None
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

    # 4. Parse charge items
    def _parse_charge(raw: Any, allow_negative: bool = False) -> float | None:
        if raw is None or str(raw).strip() == "":
            return None
        num_val = _parse_num(raw)
        if num_val is None:
            return None
        if not allow_negative and num_val < 0:
            return None
        return round(num_val, 2)

    energy_charge = _parse_charge(input_data.get("energy_charge"), allow_negative=False)
    ft_charge = _parse_charge(input_data.get("ft_charge"), allow_negative=True)
    service_charge = _parse_charge(input_data.get("service_charge"), allow_negative=False)
    vat = _parse_charge(input_data.get("vat"), allow_negative=False)

    # 5. Unusual rate warning: 1.5 <= rate <= 12.0
    if kwh is not None and amount is not None and kwh > 0:
        rate = amount / kwh
        if rate < 1.5 or rate > 12.0:
            warnings.append("rate_unusual")

    # 6. Confidence
    raw_conf = input_data.get("confidence")
    if isinstance(raw_conf, str) and raw_conf.strip().lower() in ("low", "medium", "high"):
        confidence = raw_conf.strip().lower()
    else:
        confidence = "low"

    return {
        "period_start": period_start,
        "period_end": period_end,
        "kwh": kwh,
        "amount": amount,
        "energy_charge": energy_charge,
        "ft_charge": ft_charge,
        "service_charge": service_charge,
        "vat": vat,
        "confidence": confidence,
        "warnings": warnings,
    }


def calculate_progressive_energy_charge(
    kwh: float,
    tiers: Iterable[tuple[float | None, float]],
) -> float:
    """Energy charge for ``kwh`` units using stepped (progressive) tiers.

    Each tier is (cumulative upper limit or None, baht per kWh); only the units
    inside a tier are charged at that tier's rate.
    """
    remaining = max(0.0, float(kwh))
    lower = 0.0
    charge = 0.0
    for upper, rate in tiers:
        if remaining <= 0:
            break
        width = remaining if upper is None else min(remaining, float(upper) - lower)
        if width > 0:
            charge += width * float(rate)
            remaining -= width
        if upper is not None:
            lower = float(upper)
    return round(charge, 2)


def estimate_bill(
    kwh: float,
    tiers_over_150: Iterable[tuple[float | None, float]],
    tiers_up_to_150: Iterable[tuple[float | None, float]],
    small_user_limit: float,
    ft_rate: float,
    service_charge: float,
    vat_percent: float,
) -> dict[str, float]:
    """Estimate a residential bill for ``kwh`` units.

    Returns energy_charge, ft_charge, service_charge, subtotal, vat and total (baht).
    Users of ``small_user_limit`` kWh or less use the small-user tier table.
    """
    kwh = max(0.0, float(kwh))
    tiers = tiers_up_to_150 if kwh <= small_user_limit else tiers_over_150
    energy = calculate_progressive_energy_charge(kwh, tiers)
    ft = round(kwh * float(ft_rate), 2)
    service = round(float(service_charge), 2) if kwh > 0 else 0.0
    subtotal = round(energy + ft + service, 2)
    vat = round(subtotal * float(vat_percent) / 100.0, 2)
    return {
        "energy_charge": energy,
        "ft_charge": ft,
        "service_charge": service,
        "subtotal": subtotal,
        "vat": vat,
        "total": round(subtotal + vat, 2),
    }


def cutoff_day_for_month(
    year: int,
    month: int,
    cutoff_day_30: int,
    cutoff_day_31: int,
    cutoff_day_feb: int,
) -> date:
    """Meter-reading (cut-off) date of a month: by month length (30 / 31 / February)."""
    if month == 2:
        day = cutoff_day_feb
    elif month in (4, 6, 9, 11):
        day = cutoff_day_30
    else:
        day = cutoff_day_31
    return date(year, month, int(day))


def next_cutoff_date(
    today: date,
    cutoff_day_30: int,
    cutoff_day_31: int,
    cutoff_day_feb: int,
) -> date:
    """First cut-off date on or after ``today``."""
    this_month = cutoff_day_for_month(
        today.year, today.month, cutoff_day_30, cutoff_day_31, cutoff_day_feb
    )
    if this_month >= today:
        return this_month
    year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    return cutoff_day_for_month(year, month, cutoff_day_30, cutoff_day_31, cutoff_day_feb)


def forecast_cycle_kwh(
    cycle_kwh: float,
    cycle_start: str | None,
    today: date,
    cutoff: date,
) -> tuple[float, float, int] | None:
    """Project the cycle's energy to the cut-off date.

    Returns (kwh_per_day, forecast_kwh, total_days) or None when there is no
    cycle start. Uses the average daily energy so far (at least one day elapsed).
    """
    if not cycle_start:
        return None
    try:
        start = datetime.strptime(cycle_start, "%Y-%m-%d").date()
    except ValueError:
        return None
    total_days = (cutoff - start).days
    if total_days <= 0:
        return None
    elapsed = max(1, (today - start).days)
    per_day = max(0.0, float(cycle_kwh)) / elapsed
    forecast = max(float(cycle_kwh), per_day * total_days)
    return round(per_day, 4), round(forecast, 3), total_days


def parse_tariff_tiers(text: str) -> tuple[tuple[float | None, float], ...]:
    """Parse custom tiers like "200:3.0, 400:4.1584, 4.3583".

    Each comma-separated item is "<cumulative upper limit kWh>:<rate per kWh>"; the
    last item may omit the limit ("4.3583" or ":4.3583") and is always open-ended.
    Raises ValueError on bad input (non-increasing limits, negative numbers, empty).
    """
    items = [i.strip() for i in str(text or "").replace(";", ",").split(",") if i.strip()]
    if not items:
        raise ValueError("no tiers")
    tiers: list[tuple[float | None, float]] = []
    last_limit = 0.0
    for idx, item in enumerate(items):
        if ":" in item:
            limit_txt, rate_txt = item.split(":", 1)
        else:
            limit_txt, rate_txt = "", item
        rate = float(rate_txt)
        if rate < 0:
            raise ValueError("rate must not be negative")
        limit_txt = limit_txt.strip()
        is_last = idx == len(items) - 1
        if is_last:
            tiers.append((None, rate))
            break
        if not limit_txt:
            raise ValueError("only the last tier may omit its limit")
        limit = float(limit_txt)
        if limit <= last_limit:
            raise ValueError("limits must be increasing")
        tiers.append((limit, rate))
        last_limit = limit
    return tuple(tiers)


PANEL_ASSET_TYPES = {
    ".js": "text/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".png": "image/png",
}


def panel_asset_content_type(filename: str) -> str | None:
    """Content type for a panel asset name, or None when the name is not allowed.

    Only plain file names with a known extension are allowed (no path separators,
    no leading dot), so a request can never leave the panel folder.
    """
    if not filename or "/" in filename or "\\" in filename or filename.startswith("."):
        return None
    dot = filename.rfind(".")
    if dot <= 0:
        return None
    return PANEL_ASSET_TYPES.get(filename[dot:].lower())


def panel_asset_etag(mtime_ns: int, size: int) -> str:
    """Strong-enough ETag for a panel asset from its modification time and size."""
    return f'"{mtime_ns:x}-{size:x}"'
