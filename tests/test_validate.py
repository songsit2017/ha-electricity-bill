"""Unit tests for AI bill scan extraction validation."""
from datetime import date
from pathlib import Path
import sys
import pytest

# Ensure calc can be imported directly without requiring Home Assistant packages
PKG_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "electricity_bill"
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

from calc import validate_extraction


def test_validate_extraction_be_year():
    """Test Buddhist Era year conversion: 2569 -> 2026."""
    today = date(2026, 10, 23)
    raw = {
        "period_end": "2569-10-20",
        "kwh": 312.0,
        "amount": 1385.12,
        "confidence": "high",
    }
    result = validate_extraction(raw, today=today)
    assert result["period_end"] == "2026-10-20"
    assert result["kwh"] == 312.0
    assert result["amount"] == 1385.12
    assert result["confidence"] == "high"
    assert result["warnings"] == []


def test_validate_extraction_future_date_rejected():
    """Test rejection of future dates beyond today + 1."""
    today = date(2026, 10, 12)

    # Future date > today + 1 is rejected and nulled with warning
    result_future = validate_extraction({"period_end": "2026-10-15"}, today=today)
    assert result_future["period_end"] is None
    assert "date_in_future" in result_future["warnings"]

    # Boundary: today + 1 is allowed
    result_tomorrow = validate_extraction({"period_end": "2026-10-13"}, today=today)
    assert result_tomorrow["period_end"] == "2026-10-13"
    assert "date_in_future" not in result_tomorrow["warnings"]

    # Today is allowed
    result_today = validate_extraction({"period_end": "2026-10-12"}, today=today)
    assert result_today["period_end"] == "2026-10-12"
    assert "date_in_future" not in result_today["warnings"]

    # Past date is allowed
    result_past = validate_extraction({"period_end": "2026-09-25"}, today=today)
    assert result_past["period_end"] == "2026-09-25"
    assert "date_in_future" not in result_past["warnings"]


def test_validate_extraction_kwh_out_of_range():
    """Test kwh validation: must be 0 < v <= 5000, else null + warning."""
    today = date(2026, 10, 12)

    # 0 or negative
    res0 = validate_extraction({"kwh": 0}, today=today)
    assert res0["kwh"] is None
    assert "kwh_out_of_range" in res0["warnings"]

    res_neg = validate_extraction({"kwh": -15.5}, today=today)
    assert res_neg["kwh"] is None
    assert "kwh_out_of_range" in res_neg["warnings"]

    # Greater than 5000
    res_high = validate_extraction({"kwh": 5000.1}, today=today)
    assert res_high["kwh"] is None
    assert "kwh_out_of_range" in res_high["warnings"]

    # Non-numeric string
    res_invalid = validate_extraction({"kwh": "not-a-number"}, today=today)
    assert res_invalid["kwh"] is None
    assert "kwh_out_of_range" in res_invalid["warnings"]

    # Valid boundaries
    res_min = validate_extraction({"kwh": 0.1}, today=today)
    assert res_min["kwh"] == 0.1
    assert "kwh_out_of_range" not in res_min["warnings"]

    res_max = validate_extraction({"kwh": 5000}, today=today)
    assert res_max["kwh"] == 5000.0
    assert "kwh_out_of_range" not in res_max["warnings"]


def test_validate_extraction_amount_out_of_range():
    """Test amount validation: must be 0 < v <= 100000, else null + warning."""
    today = date(2026, 10, 12)

    # 0 or negative
    res0 = validate_extraction({"amount": 0}, today=today)
    assert res0["amount"] is None
    assert "amount_out_of_range" in res0["warnings"]

    res_neg = validate_extraction({"amount": -50.0}, today=today)
    assert res_neg["amount"] is None
    assert "amount_out_of_range" in res_neg["warnings"]

    # Greater than 100000
    res_high = validate_extraction({"amount": 100001.0}, today=today)
    assert res_high["amount"] is None
    assert "amount_out_of_range" in res_high["warnings"]

    # Non-numeric string
    res_invalid = validate_extraction({"amount": "invalid-amount"}, today=today)
    assert res_invalid["amount"] is None
    assert "amount_out_of_range" in res_invalid["warnings"]

    # Valid boundaries
    res_min = validate_extraction({"amount": 1.0}, today=today)
    assert res_min["amount"] == 1.0
    assert "amount_out_of_range" not in res_min["warnings"]

    res_max = validate_extraction({"amount": 100000}, today=today)
    assert res_max["amount"] == 100000.0
    assert "amount_out_of_range" not in res_max["warnings"]


def test_validate_extraction_rate_unusual():
    """Test warning when effective rate is outside 1.5..12 THB/kWh."""
    today = date(2026, 10, 12)

    # Rate below 1.5 (100 THB / 100 kWh = 1.0 THB/kWh)
    res_low = validate_extraction({"kwh": 100.0, "amount": 100.0}, today=today)
    assert "rate_unusual" in res_low["warnings"]

    # Rate above 12.0 (1500 THB / 100 kWh = 15.0 THB/kWh)
    res_high = validate_extraction({"kwh": 100.0, "amount": 1500.0}, today=today)
    assert "rate_unusual" in res_high["warnings"]

    # Normal rate (440 THB / 100 kWh = 4.4 THB/kWh)
    res_normal = validate_extraction({"kwh": 100.0, "amount": 440.0}, today=today)
    assert "rate_unusual" not in res_normal["warnings"]

    # Boundaries: 1.5 and 12.0 are acceptable
    res_b1 = validate_extraction({"kwh": 100.0, "amount": 150.0}, today=today)
    assert "rate_unusual" not in res_b1["warnings"]

    res_b2 = validate_extraction({"kwh": 100.0, "amount": 1200.0}, today=today)
    assert "rate_unusual" not in res_b2["warnings"]


def test_validate_extraction_all_null():
    """Test that all-null input returns clean dict with nulls and no warnings."""
    today = date(2026, 10, 12)

    expected = {
        "period_end": None,
        "kwh": None,
        "amount": None,
        "confidence": "low",
        "warnings": [],
    }

    assert validate_extraction({}, today=today) == expected
    assert validate_extraction(None, today=today) == expected
    assert validate_extraction(
        {"period_end": None, "kwh": None, "amount": None, "confidence": None},
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
    result = validate_extraction(raw, today=today)
    assert result["kwh"] == 1385.12
    assert result["amount"] == 5432.1
    assert result["confidence"] == "medium"
    assert result["warnings"] == []
