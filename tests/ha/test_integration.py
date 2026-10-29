"""Integration tests against a real Home Assistant instance."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_mock_service,
)

from custom_components.electricity_bill.const import DOMAIN
from custom_components.electricity_bill.diagnostics import async_get_config_entry_diagnostics

MAIN = "sensor.main_meter"
AC = "sensor.ac_kwh"
RESET = "button.main_meter_reset"
ATTRS = {"device_class": "energy", "unit_of_measurement": "kWh", "state_class": "total_increasing"}


def _set(hass: HomeAssistant, entity_id: str, value) -> None:
    hass.states.async_set(entity_id, str(value), ATTRS)


async def _setup(hass: HomeAssistant, options: dict | None = None) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        title="Electricity Bill",
        data={"name": "Electricity Bill", "sources": [AC], "fallback_rate": 4.4},
        options=options or {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _state(hass: HomeAssistant, key: str) -> str | None:
    s = hass.states.get(f"sensor.electricity_bill_{key}")
    return s.state if s else None


async def test_setup_creates_sensors_and_services(recorder_mock, hass: HomeAssistant) -> None:
    _set(hass, MAIN, 10)
    _set(hass, AC, 2)
    await _setup(hass, {"main_meter": MAIN, "sources": [AC]})
    assert _state(hass, "cycle_energy") is not None
    assert float(_state(hass, "today_energy")) == 0.0
    assert _state(hass, "cycle_unmetered_energy") is not None
    for service in ("add_bill", "remove_bill", "reset_cycle", "set_baseline", "get_summary"):
        assert hass.services.has_service(DOMAIN, service), service


async def test_today_energy_waits_for_unavailable_main_meter(recorder_mock, hass: HomeAssistant) -> None:
    hass.states.async_set(MAIN, "unavailable", ATTRS)
    _set(hass, AC, 2)
    await _setup(hass, {"main_meter": MAIN, "sources": [AC]})
    assert _state(hass, "today_energy") == "unknown"
    _set(hass, MAIN, 100)
    await hass.async_block_till_done()
    assert float(_state(hass, "today_energy")) == 0.0
    _set(hass, MAIN, 102.5)
    await hass.async_block_till_done()
    assert float(_state(hass, "today_energy")) == 2.5


async def test_newer_bill_presses_reset_button(recorder_mock, hass: HomeAssistant) -> None:
    presses = async_mock_service(hass, "button", "press")
    _set(hass, MAIN, 50)
    _set(hass, AC, 5)
    await _setup(hass, {"main_meter": MAIN, "sources": [AC], "reset_button": RESET})
    today = dt_util.now().date()
    await hass.services.async_call(
        DOMAIN, "add_bill", {"period_end": today.isoformat(), "kwh": 300, "amount": 1300}, blocking=True
    )
    assert len(presses) == 0  # first bill: nothing older to compare with
    await hass.services.async_call(
        DOMAIN,
        "add_bill",
        {"period_end": (today + timedelta(days=1)).isoformat(), "kwh": 310, "amount": 1350},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert len(presses) == 1
    assert presses[0].data["entity_id"] == RESET


async def test_get_summary_service_returns_text(recorder_mock, hass: HomeAssistant) -> None:
    _set(hass, MAIN, 10)
    _set(hass, AC, 1)
    await _setup(hass, {"main_meter": MAIN, "sources": [AC]})
    _set(hass, MAIN, 13)
    _set(hass, AC, 2)
    await hass.async_block_till_done()
    for kind in ("daily", "weekly", "cycle"):
        result = await hass.services.async_call(
            DOMAIN, "get_summary", {"kind": kind}, blocking=True, return_response=True
        )
        assert result["kind"] == kind
        assert "kWh" in result["message"], result


async def test_daily_summary_event(recorder_mock, hass: HomeAssistant) -> None:
    events = async_capture_events(hass, "electricity_bill_daily_summary")
    _set(hass, MAIN, 10)
    _set(hass, AC, 1)
    entry = await _setup(hass, {"main_meter": MAIN, "sources": [AC]})
    _set(hass, MAIN, 14)
    await hass.async_block_till_done()
    entry.runtime_data._fire_summaries()
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["today_kwh"] == 4.0
    assert "4.0 kWh" in events[0].data["message"]


async def test_ft_issue_when_bill_ft_differs(recorder_mock, hass: HomeAssistant) -> None:
    _set(hass, MAIN, 10)
    _set(hass, AC, 1)
    await _setup(
        hass,
        {"main_meter": MAIN, "sources": [AC], "tariff_profile": "thailand_residential", "ft_rate": 0.15},
    )
    await hass.services.async_call(
        DOMAIN,
        "add_bill",
        {"period_end": dt_util.now().date().isoformat(), "kwh": 862, "amount": 3862.41, "ft_charge": 139.90},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, "ft_rate_outdated") is not None


async def test_diagnostics(recorder_mock, hass: HomeAssistant) -> None:
    _set(hass, MAIN, 10)
    _set(hass, AC, 1)
    entry = await _setup(hass, {"main_meter": MAIN, "sources": [AC]})
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["total_sources"] == [MAIN]
    assert MAIN in diag["source_states"]


async def test_config_flow_user(recorder_mock, hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Electricity Bill", "sources": [AC], "fallback_rate": 4.4}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_options_flow_two_pages(recorder_mock, hass: HomeAssistant) -> None:
    _set(hass, MAIN, 10)
    _set(hass, AC, 1)
    entry = await _setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"main_meter": MAIN, "sources": [AC], "fallback_rate": 4.4}
    )
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "tariff"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"tariff_profile": "thailand_residential", "ft_rate": 0.1623, "summary_hour": 20}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["ft_rate"] == 0.1623
    assert entry.options["main_meter"] == MAIN


async def test_device_cycle_sensors_and_reset_with_new_bill(recorder_mock, hass: HomeAssistant) -> None:
    hass.states.async_set(AC, "2", dict(ATTRS, friendly_name="aircon_bedroom_kwh"))
    _set(hass, MAIN, 10)
    await _setup(hass, {"main_meter": MAIN, "sources": [AC]})
    energy = "sensor.electricity_bill_aircon_bedroom_cycle_energy"
    cost = "sensor.electricity_bill_aircon_bedroom_cycle_cost"
    assert hass.states.get(energy) is not None, [s for s in hass.states.async_entity_ids("sensor")]
    hass.states.async_set(AC, "5", dict(ATTRS, friendly_name="aircon_bedroom_kwh"))
    _set(hass, MAIN, 16)
    await hass.async_block_till_done()
    assert float(hass.states.get(energy).state) == 3.0
    assert float(hass.states.get(cost).state) == round(3.0 * 4.4, 2)  # fallback rate, no bill yet
    await hass.services.async_call(
        DOMAIN, "add_bill", {"period_end": dt_util.now().date().isoformat(), "kwh": 300, "amount": 1350}, blocking=True
    )
    await hass.async_block_till_done()
    assert float(hass.states.get(energy).state) == 0.0  # new cycle
    assert float(hass.states.get(cost).state) == 0.0


async def test_cycle_starts_automatically_after_billing_day(recorder_mock, hass: HomeAssistant) -> None:
    _set(hass, MAIN, 10)
    _set(hass, AC, 1)
    entry = await _setup(
        hass, {"main_meter": MAIN, "sources": [AC], "cutoff_day_30": 24, "cutoff_day_31": 25, "cutoff_day_feb": 24}
    )
    _set(hass, MAIN, 25)
    await hass.async_block_till_done()
    assert float(_state(hass, "cycle_energy")) == 15.0
    coordinator = entry.runtime_data
    coordinator._maybe_start_cycle(today=dt_util.parse_date("2026-10-26"))  # day after the 31-day-month billing day
    coordinator._update_internal_data()
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert float(_state(hass, "cycle_energy")) == 0.0
    assert coordinator.data["cycle_start"] == "2026-10-25"


async def test_panel_file_is_served_no_cache(recorder_mock, hass: HomeAssistant, hass_client_no_auth) -> None:
    _set(hass, MAIN, 10)
    _set(hass, AC, 1)
    await _setup(hass, {"main_meter": MAIN, "sources": [AC]})
    client = await hass_client_no_auth()
    resp = await client.get("/electricity_bill_panel/panel.js")
    assert resp.status == 200
    assert resp.headers["Cache-Control"] == "no-cache"
    etag = resp.headers["ETag"]
    again = await client.get("/electricity_bill_panel/panel.js", headers={"If-None-Match": etag})
    assert again.status == 304
    missing = await client.get("/electricity_bill_panel/nothing.js")
    assert missing.status == 404
