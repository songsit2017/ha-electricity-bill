"""Unit tests for calc.py math and data manipulation helpers."""
from datetime import date
from pathlib import Path
import sys
import pytest

# Ensure calc can be imported directly without requiring Home Assistant packages
PKG_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "electricity_bill"
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

import calc


def test_calculate_rate():
    """Test calculation of electricity rate (amount / kwh)."""
    # Standard bill: 1385.12 THB / 312.0 kWh
    rate = calc.calculate_rate(1385.12, 312.0)
    assert rate == 4.4395

    # Exact division
    assert calc.calculate_rate(1000.0, 200.0) == 5.0

    # Rate with custom decimals
    assert calc.calculate_rate(1385.12, 312.0, decimals=2) == 4.44

    # Invalid kWh (zero or negative)
    with pytest.raises(ValueError, match="kWh must be greater than 0"):
        calc.calculate_rate(100.0, 0.0)

    with pytest.raises(ValueError, match="kWh must be greater than 0"):
        calc.calculate_rate(100.0, -5.0)


def test_calculate_source_delta_and_meter_reset():
    """Test meter delta calculation including meter reset handling."""
    # Normal consumption increase
    assert calc.calculate_source_delta(120.5, 100.0) == 20.5
    assert calc.calculate_source_delta(50.0, 50.0) == 0.0

    # Meter reset: current < baseline (counter reset to 0, e.g. device replaced)
    # Baseline treated as 0, delta = current
    assert calc.calculate_source_delta(15.0, 100.0) == 15.0

    # Current reset to 0 exactly
    assert calc.calculate_source_delta(0.0, 100.0) == 0.0

    # Never produces negative values
    assert calc.calculate_source_delta(-5.0, 0.0) == 0.0


def test_calculate_snapshot_delta():
    """Test snapshot subtraction across multiple sensors."""
    prev_snapshot = {
        "sensor.pc_kwh": 100.0,
        "sensor.aircon_bedroom_kwh": 200.0,
        "sensor.water_pump_kwh": 50.0,
    }
    curr_snapshot = {
        "sensor.pc_kwh": 125.5,             # +25.5
        "sensor.aircon_bedroom_kwh": 310.0, # +110.0
        "sensor.water_pump_kwh": 10.0,      # reset: +10.0
        "sensor.speaker_kwh": 5.0,          # new sensor: +5.0 (prev was 0)
    }

    total, per_source = calc.calculate_snapshot_delta(curr_snapshot, prev_snapshot)
    assert total == 25.5 + 110.0 + 10.0 + 5.0
    assert per_source["sensor.pc_kwh"] == 25.5
    assert per_source["sensor.aircon_bedroom_kwh"] == 110.0
    assert per_source["sensor.water_pump_kwh"] == 10.0
    assert per_source["sensor.speaker_kwh"] == 5.0

    # No previous snapshot (first bill)
    total_none, per_source_none = calc.calculate_snapshot_delta(curr_snapshot, None)
    assert total_none == 0.0
    assert all(v == 0.0 for v in per_source_none.values())


def test_duplicate_period_end_detection():
    """Test duplicate period_end detection."""
    bills = [
        {"id": "b1", "period_end": "2026-08-25", "kwh": 250.0, "amount": 1100.0},
        {"id": "b2", "period_end": "2026-09-24", "kwh": 280.0, "amount": 1250.0},
    ]

    # Duplicate without replace=True -> True
    assert calc.check_duplicate_period_end(bills, "2026-09-24", replace=False) is True
    # Non-duplicate -> False
    assert calc.check_duplicate_period_end(bills, "2026-10-23", replace=False) is False
    # Duplicate with replace=True -> False
    assert calc.check_duplicate_period_end(bills, "2026-09-24", replace=True) is False


def test_add_bill_and_recompute_measured_kwh():
    """Test adding bills and verifying measured_kwh between consecutive snapshots."""
    bills = []

    # Bill 1: 2026-08-25
    bill1 = {
        "id": "1",
        "period_end": "2026-08-25",
        "kwh": 300.0,
        "amount": 1320.0,
        "rate": 4.40,
        "snapshot": {"sensor.pc_kwh": 100.0, "sensor.aircon_kwh": 200.0},
        "note": "First bill",
    }
    bills, added1 = calc.add_bill_record(bills, bill1)
    assert len(bills) == 1
    assert added1["period_start"] is None
    assert added1["measured_kwh"] == 0.0

    # Bill 2: 2026-09-23 (moving billing date: 29 days later)
    bill2 = {
        "id": "2",
        "period_end": "2026-09-23",
        "kwh": 310.0,
        "amount": 1380.0,
        "rate": 4.4516,
        "snapshot": {"sensor.pc_kwh": 140.0, "sensor.aircon_kwh": 320.0},
        "note": "Second bill",
    }
    bills, added2 = calc.add_bill_record(bills, bill2)
    assert len(bills) == 2
    assert bills[0]["period_end"] == "2026-08-25"
    assert bills[1]["period_end"] == "2026-09-23"
    assert bills[1]["period_start"] == "2026-08-25"
    # measured_kwh = (140 - 100) + (320 - 200) = 40 + 120 = 160.0
    assert bills[1]["measured_kwh"] == 160.0

    # Bill 3: 2026-10-25 (moving billing date)
    bill3 = {
        "id": "3",
        "period_end": "2026-10-25",
        "kwh": 320.0,
        "amount": 1420.0,
        "rate": 4.4375,
        "snapshot": {"sensor.pc_kwh": 190.0, "sensor.aircon_kwh": 450.0},
        "note": "Third bill",
    }
    bills, added3 = calc.add_bill_record(bills, bill3)
    assert len(bills) == 3
    assert bills[2]["period_start"] == "2026-09-23"
    # measured_kwh = (190 - 140) + (450 - 320) = 50 + 130 = 180.0
    assert bills[2]["measured_kwh"] == 180.0

    # Duplicate rejection
    dup_bill = {
        "id": "4",
        "period_end": "2026-09-23",
        "kwh": 315.0,
        "amount": 1390.0,
        "snapshot": {"sensor.pc_kwh": 145.0, "sensor.aircon_kwh": 325.0},
    }
    with pytest.raises(ValueError, match="Duplicate period_end: 2026-09-23"):
        calc.add_bill_record(bills, dup_bill, replace=False)

    # Replacing existing bill
    dup_bill["amount"] = 1400.0
    bills, replaced = calc.add_bill_record(bills, dup_bill, replace=True)
    assert len(bills) == 3
    assert bills[1]["amount"] == 1400.0
    assert bills[1]["id"] == "2"  # keeps original id if not changed


def test_add_bill_out_of_order_insertion():
    """Test adding an older bill; verifies list stays sorted and following bills are recomputed."""
    bill1 = {
        "id": "1",
        "period_end": "2026-07-25",
        "kwh": 200.0,
        "amount": 880.0,
        "rate": 4.40,
        "snapshot": {"sensor.pc_kwh": 100.0},
    }
    bill3 = {
        "id": "3",
        "period_end": "2026-09-25",
        "kwh": 200.0,
        "amount": 880.0,
        "rate": 4.40,
        "snapshot": {"sensor.pc_kwh": 300.0},
    }
    bills = [bill1, bill3]
    bills = calc.recompute_bills(bills)
    assert bills[1]["measured_kwh"] == 200.0  # 300 - 100

    # Insert bill2 for 2026-08-25
    bill2 = {
        "id": "2",
        "period_end": "2026-08-25",
        "kwh": 200.0,
        "amount": 880.0,
        "rate": 4.40,
        "snapshot": {"sensor.pc_kwh": 180.0},
    }
    bills, _ = calc.add_bill_record(bills, bill2)
    assert len(bills) == 3
    assert [b["period_end"] for b in bills] == ["2026-07-25", "2026-08-25", "2026-09-25"]
    assert bills[1]["measured_kwh"] == 80.0   # 180 - 100
    assert bills[2]["measured_kwh"] == 120.0  # 300 - 180
    assert bills[2]["period_start"] == "2026-08-25"


def test_remove_bill_and_restore_cycle_snapshot():
    """Test removing bills by id and period_end, restoring cycle_snapshot if latest bill."""
    bills = [
        {
            "id": "b1",
            "period_end": "2026-07-25",
            "kwh": 200.0,
            "amount": 880.0,
            "rate": 4.40,
            "snapshot": {"sensor.pc_kwh": 100.0},
        },
        {
            "id": "b2",
            "period_end": "2026-08-25",
            "kwh": 210.0,
            "amount": 920.0,
            "rate": 4.381,
            "snapshot": {"sensor.pc_kwh": 180.0},
        },
        {
            "id": "b3",
            "period_end": "2026-09-25",
            "kwh": 220.0,
            "amount": 960.0,
            "rate": 4.3636,
            "snapshot": {"sensor.pc_kwh": 290.0},
        },
    ]
    bills = calc.recompute_bills(bills)

    # 1. Remove the latest bill (b3) by id
    remaining, removed, restored = calc.remove_bill_record(bills, bill_id="b3")
    assert len(remaining) == 2
    assert removed["id"] == "b3"
    # Because b3 was the latest bill, cycle_snapshot is restored to b2's snapshot
    assert restored == {"sensor.pc_kwh": 180.0}

    # 2. Add b3 back, then remove the middle bill (b2) by period_end
    bills, _ = calc.add_bill_record(remaining, {
        "id": "b3",
        "period_end": "2026-09-25",
        "kwh": 220.0,
        "amount": 960.0,
        "rate": 4.3636,
        "snapshot": {"sensor.pc_kwh": 290.0},
    })
    assert len(bills) == 3

    remaining, removed, restored = calc.remove_bill_record(bills, period_end="2026-08-25")
    assert len(remaining) == 2
    assert removed["id"] == "b2"
    # b2 was NOT the latest bill, so restored is None (current cycle baseline unchanged)
    assert restored is None
    # Following bill (b3) has its measured_kwh recomputed against b1
    assert remaining[1]["period_start"] == "2026-07-25"
    assert remaining[1]["measured_kwh"] == 190.0  # 290 - 100

    # 3. Remove all remaining bills until empty
    remaining, _, restored = calc.remove_bill_record(remaining, bill_id="b3")
    assert restored == {"sensor.pc_kwh": 100.0}

    remaining, _, restored = calc.remove_bill_record(remaining, bill_id="b1")
    assert len(remaining) == 0
    # Last bill removed: cycle snapshot restored to empty dict
    assert restored == {}

    # 4. Error cases
    with pytest.raises(ValueError, match="Either id or period_end must be provided"):
        calc.remove_bill_record(bills)

    with pytest.raises(ValueError, match="Bill not found"):
        calc.remove_bill_record(bills, bill_id="non_existent")


def test_cycle_cost_and_unmetered():
    """Test cycle cost estimate and unmetered kWh calculations."""
    # Cycle cost
    assert calc.calculate_cycle_cost(100.0, 4.40) == 440.0
    assert calc.calculate_cycle_cost(123.456, 4.4395) == 548.08
    assert calc.calculate_cycle_cost(0.0, 4.40) == 0.0

    # Unmetered kWh
    unmetered, share = calc.calculate_unmetered_kwh(312.0, 178.1)
    assert unmetered == 133.9
    assert share == 57.1

    # Measured == bill
    unmetered, share = calc.calculate_unmetered_kwh(200.0, 200.0)
    assert unmetered == 0.0
    assert share == 100.0

    # Zero bill
    unmetered, share = calc.calculate_unmetered_kwh(0.0, 0.0)
    assert unmetered == 0.0
    assert share == 0.0


def test_days_in_cycle():
    """Test days in cycle calculation."""
    assert calc.calculate_days_in_cycle("2026-09-25", "2026-10-12") == 17
    assert calc.calculate_days_in_cycle("2026-09-25", "2026-09-25") == 0
    assert calc.calculate_days_in_cycle(None) == 0
    assert calc.calculate_days_in_cycle("invalid-date") == 0


def test_derive_period_start():
    """Test derive_period_start pure helper function."""
    # First bill: no period_start and no prev_period_end -> None
    assert calc.derive_period_start(None, None) is None
    assert calc.derive_period_start({}, {}) is None

    # Explicit period_start provided -> return explicit period_start
    assert calc.derive_period_start("2026-09-01", None) == "2026-09-01"
    assert calc.derive_period_start("2026-09-01", "2026-08-31") == "2026-09-01"
    assert calc.derive_period_start({"period_start_manual": "2026-09-01"}, {"period_end": "2026-08-31"}) == "2026-09-01"

    # Missing period_start: derives from previous bill's period_end + 1 day
    assert calc.derive_period_start(None, "2026-08-25") == "2026-08-26"
    assert calc.derive_period_start(None, "2026-08-31") == "2026-09-01"
    assert calc.derive_period_start(None, "2024-02-28") == "2024-02-29"  # leap year
    assert calc.derive_period_start(None, date(2026, 8, 25)) == "2026-08-26"
    assert calc.derive_period_start({}, {"period_end": "2026-08-25"}) == "2026-08-26"


    # Invalid prev_period_end returns None or explicit period_start
    assert calc.derive_period_start(None, "invalid-date") is None
    assert calc.derive_period_start("2026-09-01", "invalid-date") == "2026-09-01"


def test_calculate_days():
    """Test calculate_days pure helper function."""
    # Standard period: 30 days inclusive ((end - start).days + 1)
    assert calc.calculate_days("2026-09-01", "2026-09-30") == 30
    assert calc.calculate_days("2026-08-25", "2026-09-24") == 31

    # Same date: 1 day
    assert calc.calculate_days("2026-09-01", "2026-09-01") == 1

    # Leap year handling
    assert calc.calculate_days("2024-02-28", "2024-03-01") == 3

    # Date objects
    assert calc.calculate_days(date(2026, 9, 1), date(2026, 9, 30)) == 30

    # Start after end -> None
    assert calc.calculate_days("2026-09-30", "2026-09-01") is None

    # Missing or invalid dates -> None
    assert calc.calculate_days(None, "2026-09-30") is None
    assert calc.calculate_days("2026-09-01", None) is None
    assert calc.calculate_days(None, None) is None
    assert calc.calculate_days("not-a-date", "2026-09-30") is None
    assert calc.calculate_days("2026-09-01", "not-a-date") is None


def test_calculate_per_day():
    """Test calculate_per_day pure helper function."""
    # Standard calculations
    assert calc.calculate_per_day(300.0, 30) == 10.0
    assert calc.calculate_per_day(100.0, 3) == 33.33
    assert calc.calculate_per_day(100.0, 3, decimals=3) == 33.333
    assert calc.calculate_per_day(0.0, 30) == 0.0

    # Division by zero or negative days -> None
    assert calc.calculate_per_day(100.0, 0) is None
    assert calc.calculate_per_day(100.0, -5) is None

    # None values -> None
    assert calc.calculate_per_day(None, 30) is None
    assert calc.calculate_per_day(100.0, None) is None
    assert calc.calculate_per_day(None, None) is None

    # Invalid non-numeric inputs -> None
    assert calc.calculate_per_day("invalid", 30) is None
    assert calc.calculate_per_day(100.0, "invalid") is None


def test_calculate_change_pct():
    """Test calculate_change_pct pure helper function."""
    # Standard positive change: (110 - 100) / 100 * 100 = 10.0%
    assert calc.calculate_change_pct(110.0, 100.0) == 10.0

    # Negative change: (85 - 100) / 100 * 100 = -15.0%
    assert calc.calculate_change_pct(85.0, 100.0) == -15.0

    # No change: 0.0%
    assert calc.calculate_change_pct(100.0, 100.0) == 0.0

    # Decimal rounding: 1 decimal place by default
    assert calc.calculate_change_pct(105.56, 100.0) == 5.6

    # Division by zero (previous was 0.0) -> None
    assert calc.calculate_change_pct(100.0, 0.0) is None
    assert calc.calculate_change_pct(0.0, 0.0) is None

    # Current is 0, previous is positive -> -100.0%
    assert calc.calculate_change_pct(0.0, 100.0) == -100.0

    # None values -> None
    assert calc.calculate_change_pct(None, 100.0) is None
    assert calc.calculate_change_pct(100.0, None) is None
    assert calc.calculate_change_pct(None, None) is None


def test_items_sum_mismatch():
    """Test items_sum_mismatch pure helper function."""
    # All 4 items present and sum matches amount -> False (no mismatch)
    assert calc.items_sum_mismatch(
        amount=1000.0,
        energy_charge=800.0,
        ft_charge=100.0,
        service_charge=34.62,
        vat=65.38,
    ) is False

    # Negative Ft charge: 800 - 50 + 34.62 + 65.38 = 850.0 -> False
    assert calc.items_sum_mismatch(
        amount=850.0,
        energy_charge=800.0,
        ft_charge=-50.0,
        service_charge=34.62,
        vat=65.38,
    ) is False

    # Difference within tolerance (0.05) -> False
    assert calc.items_sum_mismatch(
        amount=1000.0,
        energy_charge=800.0,
        ft_charge=100.0,
        service_charge=34.62,
        vat=65.41,  # diff = 0.03
    ) is False

    # Difference exceeds tolerance (> 0.05) -> True (mismatch)
    assert calc.items_sum_mismatch(
        amount=1000.0,
        energy_charge=800.0,
        ft_charge=100.0,
        service_charge=34.62,
        vat=70.0,  # diff = 4.62
    ) is True

    # Negative Ft mismatch: amount=900, sum=850 -> diff=50 -> True
    assert calc.items_sum_mismatch(
        amount=900.0,
        energy_charge=800.0,
        ft_charge=-50.0,
        service_charge=34.62,
        vat=65.38,
    ) is True

    # Missing any item -> False (never flag mismatch on partial data)
    assert calc.items_sum_mismatch(None, 800.0, 100.0, 34.62, 65.38) is False
    assert calc.items_sum_mismatch(1000.0, None, 100.0, 34.62, 65.38) is False
    assert calc.items_sum_mismatch(1000.0, 800.0, None, 34.62, 65.38) is False
    assert calc.items_sum_mismatch(1000.0, 800.0, 100.0, None, 65.38) is False
    assert calc.items_sum_mismatch(1000.0, 800.0, 100.0, 34.62, None) is False


def test_format_bill_history():
    """Test format_bill_history with comprehensive bill scenarios."""
    bills = [
        # Bill 1: First bill (no previous bill, no period_start)
        {
            "id": "b1",
            "period_end": "2026-07-25",
            "kwh": 200.0,
            "amount": 880.0,
            "rate": 4.40,
            "note": "First bill",
        },
        # Bill 2: Missing period_start (derived from b1's period_end + 1 day: 2026-07-26)
        # Zero previous kWh test scenario setup: b2 has kwh = 0.0
        {
            "id": "b2",
            "period_end": "2026-08-25",
            "kwh": 0.0,
            "amount": 50.0,
            "rate": 0.0,
            "note": "Zero kWh bill",
        },
        # Bill 3: Previous bill (b2) had zero kWh -> kwh_change_pct must be None
        # Explicit period_start: "2026-08-26"
        # Negative Ft charge: ft_charge = -25.50
        # Mismatch false: 800 + (-25.50) + 38.22 + 56.89 = 869.61
        {
            "id": "b3",
            "period_start_manual": "2026-08-26",
            "period_end": "2026-09-25",
            "kwh": 210.0,
            "amount": 869.61,
            "rate": 4.141,
            "energy_charge": 800.0,
            "ft_charge": -25.50,
            "service_charge": 38.22,
            "vat": 56.89,
            "note": "Negative Ft bill",
        },
        # Bill 4: Items sum mismatch true
        # amount = 1000.0, charges sum = 800 + 100 + 38.22 + 50.0 = 988.22 (diff 11.78 > 0.05)
        {
            "id": "b4",
            "period_end": "2026-10-25",
            "kwh": 250.0,
            "amount": 1000.0,
            "rate": 4.0,
            "energy_charge": 800.0,
            "ft_charge": 100.0,
            "service_charge": 38.22,
            "vat": 50.0,
            "note": "Mismatch bill",
        },
    ]

    history = calc.format_bill_history(bills, max_items=10)
    assert len(history) == 4

    expected_keys = {
        "id",
        "period_start",
        "period_end",
        "days",
        "kwh",
        "amount",
        "rate",
        "kwh_per_day",
        "baht_per_day",
        "kwh_change_pct",
        "amount_change_pct",
        "energy_charge",
        "ft_charge",
        "service_charge",
        "vat",
        "items_mismatch",
        "note",
    }
    for item in history:
        assert set(item.keys()) == expected_keys

    # History is newest first: [b4, b3, b2, b1]
    h4, h3, h2, h1 = history[0], history[1], history[2], history[3]

    # Bill 4: mismatch true
    assert h4["id"] == "b4"
    assert h4["items_mismatch"] is True
    assert h4["period_start"] == "2026-09-26"  # derived from b3's period_end + 1
    assert h4["days"] == 30                    # 2026-09-26 to 2026-10-25
    assert h4["kwh_per_day"] == round(250.0 / 30, 2)
    assert h4["baht_per_day"] == round(1000.0 / 30, 2)
    assert h4["amount_change_pct"] == round(((1000.0 - 869.61) / 869.61) * 100, 1)

    # Bill 3: explicit start, negative Ft, mismatch false, prev bill b2 had zero kwh
    assert h3["id"] == "b3"
    assert h3["period_start"] == "2026-08-26"
    assert h3["ft_charge"] == -25.50
    assert h3["items_mismatch"] is False
    assert h3["kwh_change_pct"] is None  # prev kwh was 0.0 -> no division by zero error

    # Bill 2: derived start
    assert h2["id"] == "b2"
    assert h2["period_start"] == "2026-07-26"
    assert h2["days"] == 31  # 2026-07-26 to 2026-08-25

    # Bill 1: first bill -> period_start, days, change_pct are None
    assert h1["id"] == "b1"
    assert h1["period_start"] is None
    assert h1["days"] is None
    assert h1["kwh_per_day"] is None
    assert h1["baht_per_day"] is None
    assert h1["kwh_change_pct"] is None
    assert h1["amount_change_pct"] is None
    assert h1["items_mismatch"] is False


def test_format_bill_history_old_bills_backward_compatibility():
    """Test format_bill_history with legacy bills missing new keys."""
    old_bills = [
        {
            "id": "old_1",
            "period_end": "2026-05-20",
            "kwh": 220.0,
            "amount": 950.0,
            "rate": 4.3182,
            "snapshot": {"sensor.pc_kwh": 50.0},
            "measured_kwh": 0.0,
            "note": "Old bill without new fields",
        },
        {
            "id": "old_2",
            "period_end": "2026-06-20",
            "kwh": 240.0,
            "amount": 1050.0,
            "rate": 4.375,
            "snapshot": {"sensor.pc_kwh": 80.0},
            "measured_kwh": 30.0,
            "note": "Second old bill",
        },
    ]

    history = calc.format_bill_history(old_bills, max_items=5)
    assert len(history) == 2

    # Newest first
    latest = history[0]
    assert latest["id"] == "old_2"
    assert latest["period_start"] == "2026-05-21"  # derived from old_1 period_end + 1
    assert latest["days"] == 31
    assert latest["energy_charge"] is None
    assert latest["ft_charge"] is None
    assert latest["service_charge"] is None
    assert latest["vat"] is None
    assert latest["items_mismatch"] is False
    assert latest["kwh_change_pct"] == round(((240.0 - 220.0) / 220.0) * 100, 1)

    first = history[1]
    assert first["id"] == "old_1"
    assert first["period_start"] is None
    assert first["days"] is None
    assert first["energy_charge"] is None
    assert first["items_mismatch"] is False


def test_validate_extraction_be_year():
    """Test Buddhist Era year conversion: 2569 -> 2026."""
    today = date(2026, 10, 23)
    raw = {
        "period_end": "2569-10-20",
        "kwh": 312.0,
        "amount": 1385.12,
        "confidence": "high",
    }
    result = calc.validate_extraction(raw, today=today)
    assert result["period_end"] == "2026-10-20"
    assert result["kwh"] == 312.0
    assert result["amount"] == 1385.12
    assert result["confidence"] == "high"
    assert result["warnings"] == []


def test_validate_extraction_future_date_rejected():
    """Test rejection of future dates beyond today + 1."""
    today = date(2026, 10, 12)

    result_future = calc.validate_extraction({"period_end": "2026-10-15"}, today=today)
    assert result_future["period_end"] is None
    assert "date_in_future" in result_future["warnings"]

    result_tomorrow = calc.validate_extraction({"period_end": "2026-10-13"}, today=today)
    assert result_tomorrow["period_end"] == "2026-10-13"
    assert "date_in_future" not in result_tomorrow["warnings"]

    result_today = calc.validate_extraction({"period_end": "2026-10-12"}, today=today)
    assert result_today["period_end"] == "2026-10-12"
    assert "date_in_future" not in result_today["warnings"]

    result_past = calc.validate_extraction({"period_end": "2026-09-25"}, today=today)
    assert result_past["period_end"] == "2026-09-25"
    assert "date_in_future" not in result_past["warnings"]


def test_validate_extraction_kwh_out_of_range():
    """Test kwh validation: must be 0 < v <= 5000, else null + warning."""
    today = date(2026, 10, 12)

    res0 = calc.validate_extraction({"kwh": 0}, today=today)
    assert res0["kwh"] is None
    assert "kwh_out_of_range" in res0["warnings"]

    res_neg = calc.validate_extraction({"kwh": -15.5}, today=today)
    assert res_neg["kwh"] is None
    assert "kwh_out_of_range" in res_neg["warnings"]

    res_high = calc.validate_extraction({"kwh": 5000.1}, today=today)
    assert res_high["kwh"] is None
    assert "kwh_out_of_range" in res_high["warnings"]

    res_invalid = calc.validate_extraction({"kwh": "not-a-number"}, today=today)
    assert res_invalid["kwh"] is None
    assert "kwh_out_of_range" in res_invalid["warnings"]

    res_min = calc.validate_extraction({"kwh": 0.1}, today=today)
    assert res_min["kwh"] == 0.1
    assert "kwh_out_of_range" not in res_min["warnings"]

    res_max = calc.validate_extraction({"kwh": 5000}, today=today)
    assert res_max["kwh"] == 5000.0
    assert "kwh_out_of_range" not in res_max["warnings"]


def test_validate_extraction_amount_out_of_range():
    """Test amount validation: must be 0 < v <= 100000, else null + warning."""
    today = date(2026, 10, 12)

    res0 = calc.validate_extraction({"amount": 0}, today=today)
    assert res0["amount"] is None
    assert "amount_out_of_range" in res0["warnings"]

    res_neg = calc.validate_extraction({"amount": -50.0}, today=today)
    assert res_neg["amount"] is None
    assert "amount_out_of_range" in res_neg["warnings"]

    res_high = calc.validate_extraction({"amount": 100001.0}, today=today)
    assert res_high["amount"] is None
    assert "amount_out_of_range" in res_high["warnings"]

    res_invalid = calc.validate_extraction({"amount": "invalid-amount"}, today=today)
    assert res_invalid["amount"] is None
    assert "amount_out_of_range" in res_invalid["warnings"]

    res_min = calc.validate_extraction({"amount": 1.0}, today=today)
    assert res_min["amount"] == 1.0
    assert "amount_out_of_range" not in res_min["warnings"]

    res_max = calc.validate_extraction({"amount": 100000}, today=today)
    assert res_max["amount"] == 100000.0
    assert "amount_out_of_range" not in res_max["warnings"]


def test_validate_extraction_rate_unusual():
    """Test warning when effective rate is outside 1.5..12 THB/kWh."""
    today = date(2026, 10, 12)

    res_low = calc.validate_extraction({"kwh": 100.0, "amount": 100.0}, today=today)
    assert "rate_unusual" in res_low["warnings"]

    res_high = calc.validate_extraction({"kwh": 100.0, "amount": 1500.0}, today=today)
    assert "rate_unusual" in res_high["warnings"]

    res_normal = calc.validate_extraction({"kwh": 100.0, "amount": 440.0}, today=today)
    assert "rate_unusual" not in res_normal["warnings"]

    res_b1 = calc.validate_extraction({"kwh": 100.0, "amount": 150.0}, today=today)
    assert "rate_unusual" not in res_b1["warnings"]

    res_b2 = calc.validate_extraction({"kwh": 100.0, "amount": 1200.0}, today=today)
    assert "rate_unusual" not in res_b2["warnings"]


def test_validate_extraction_all_null():
    """Test that all-null input returns clean dict with nulls and no warnings."""
    today = date(2026, 10, 12)

    expected = {
        "period_start": None,
        "period_end": None,
        "kwh": None,
        "amount": None,
        "energy_charge": None,
        "ft_charge": None,
        "service_charge": None,
        "vat": None,
        "confidence": "low",
        "warnings": [],
    }

    assert calc.validate_extraction({}, today=today) == expected
    assert calc.validate_extraction(None, today=today) == expected
    assert calc.validate_extraction(
        {
            "period_start": None,
            "period_end": None,
            "kwh": None,
            "amount": None,
            "energy_charge": None,
            "ft_charge": None,
            "service_charge": None,
            "vat": None,
            "confidence": None,
        },
        today=today,
    ) == expected


def test_validate_extraction_numeric_strings_with_commas():
    """Test numeric strings with commas and whitespace."""
    today = date(2026, 10, 12)
    raw = {
        "kwh": " 1,385.12 ",
        "amount": "5,432.10",
        "confidence": "medium",
    }
    result = calc.validate_extraction(raw, today=today)
    assert result["kwh"] == 1385.12
    assert result["amount"] == 5432.1
    assert result["confidence"] == "medium"
    assert result["warnings"] == []


def test_validate_extraction_detailed_charges_and_period():
    """Test validation of period_start and four charges in validate_extraction."""
    today = date(2026, 10, 23)
    raw = {
        "period_start": "2569-09-21",  # BE year 2569 -> 2026
        "period_end": "2569-10-20",
        "kwh": "312.0",
        "amount": "1,385.12",
        "energy_charge": "1,150.50",
        "ft_charge": "-45.20",          # negative Ft allowed
        "service_charge": "38.22",
        "vat": "91.60",
        "confidence": "high",
    }
    result = calc.validate_extraction(raw, today=today)
    assert result["period_start"] == "2026-09-21"
    assert result["period_end"] == "2026-10-20"
    assert result["kwh"] == 312.0
    assert result["amount"] == 1385.12
    assert result["energy_charge"] == 1150.50
    assert result["ft_charge"] == -45.20
    assert result["service_charge"] == 38.22
    assert result["vat"] == 91.60
    assert result["confidence"] == "high"
    assert result["warnings"] == []

    # Negative energy_charge, service_charge, vat rejected (set to None)
    neg_raw = {
        "energy_charge": -10.0,
        "service_charge": -5.0,
        "vat": -2.0,
        "ft_charge": -50.0,  # Ft can be negative
    }
    res_neg = calc.validate_extraction(neg_raw, today=today)
    assert res_neg["energy_charge"] is None
    assert res_neg["service_charge"] is None
    assert res_neg["vat"] is None
    assert res_neg["ft_charge"] == -50.0

    # period_start > period_end -> warning 'invalid_period'
    res_inv_period = calc.validate_extraction(
        {"period_start": "2026-10-10", "period_end": "2026-10-05"},
        today=today,
    )
    assert "invalid_period" in res_inv_period["warnings"]
