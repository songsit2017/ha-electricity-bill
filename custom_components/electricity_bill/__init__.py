"""Electricity Bill custom integration for Home Assistant."""
from __future__ import annotations
from collections.abc import Callable
from datetime import date, datetime, time
import logging
from typing import Any
import uuid
from zoneinfo import ZoneInfo

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .calc import (
    add_bill_record,
    calculate_cycle_cost,
    calculate_cycle_kwh,
    calculate_days_in_cycle,
    calculate_rate,
    calculate_unmetered_kwh,
    check_duplicate_period_end,
    format_bill_history,
    remove_bill_record,
)
from .const import (
    ATTR_AMOUNT,
    ATTR_ID,
    ATTR_KWH,
    ATTR_NOTE,
    ATTR_PERIOD_END,
    ATTR_REPLACE,
    CONF_FALLBACK_RATE,
    CONF_NAME,
    CONF_SOURCES,
    DEFAULT_FALLBACK_RATE,
    DEFAULT_NAME,
    DOMAIN,
    SERVICE_ADD_BILL,
    SERVICE_REMOVE_BILL,
    SERVICE_RESET_CYCLE,
)
from .store import ElectricityBillStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type ElectricityBillConfigEntry = ConfigEntry["ElectricityBillCoordinator"]

ADD_BILL_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_PERIOD_END): cv.date,
        vol.Required(ATTR_KWH): vol.Coerce(float),
        vol.Required(ATTR_AMOUNT): vol.Coerce(float),
        vol.Optional(ATTR_NOTE, default=""): cv.string,
        vol.Optional(ATTR_REPLACE, default=False): cv.boolean,
    }
)

REMOVE_BILL_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ID): cv.string,
        vol.Optional(ATTR_PERIOD_END): cv.date,
    }
)

RESET_CYCLE_SCHEMA = vol.Schema({})


class ElectricityBillCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator managing state, storage, and updates for Electricity Bill."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ElectricityBillConfigEntry,
        store: ElectricityBillStore,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.data.get(CONF_NAME, DEFAULT_NAME),
        )
        self.entry = entry
        self.store = store
        self.bills: list[dict[str, Any]] = []
        self.cycle_snapshot: dict[str, float] = {}
        self._unsub_track: Callable[[], None] | None = None

    @property
    def sources(self) -> list[str]:
        """Return the list of source energy sensor entity IDs."""
        return list(
            self.entry.options.get(
                CONF_SOURCES,
                self.entry.data.get(CONF_SOURCES, []),
            )
        )

    @property
    def fallback_rate(self) -> float:
        """Return the fallback rate in THB/kWh."""
        return float(
            self.entry.options.get(
                CONF_FALLBACK_RATE,
                self.entry.data.get(CONF_FALLBACK_RATE, DEFAULT_FALLBACK_RATE),
            )
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for Electricity Bill."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.entry.data.get(CONF_NAME, DEFAULT_NAME),
            manufacturer="Electricity Bill",
            model="Cost & Cycle Monitor",
            entry_type=None,
        )

    async def async_setup(self) -> None:
        """Load storage and start tracking source sensors."""
        stored = await self.store.async_load()
        self.bills = stored.get("bills", [])
        self.cycle_snapshot = stored.get("cycle_snapshot", {})

        # If baseline cycle snapshot is empty, initialize it from current states
        if not self.cycle_snapshot and self.sources:
            self.cycle_snapshot = self.get_current_snapshot()
            await self.store.async_save(
                {
                    "bills": self.bills,
                    "cycle_snapshot": self.cycle_snapshot,
                }
            )

        # Ensure any newly added sources have a baseline in cycle_snapshot
        missing_sources = [s for s in self.sources if s not in self.cycle_snapshot]
        if missing_sources:
            current_snap = self.get_current_snapshot()
            for s in missing_sources:
                self.cycle_snapshot[s] = current_snap.get(s, 0.0)
            await self.store.async_save(
                {
                    "bills": self.bills,
                    "cycle_snapshot": self.cycle_snapshot,
                }
            )

        self._update_internal_data()

        if self.sources:
            @callback
            def _async_on_source_change(event: Event) -> None:
                self._update_internal_data()
                self.async_update_listeners()

            self._unsub_track = async_track_state_change_event(
                self.hass,
                self.sources,
                _async_on_source_change,
            )

    def async_unload(self) -> None:
        """Unload coordinator listeners."""
        if self._unsub_track is not None:
            self._unsub_track()
            self._unsub_track = None

    def get_current_snapshot(self) -> dict[str, float]:
        """Read current values from source sensors."""
        snapshot: dict[str, float] = {}
        for source in self.sources:
            state = self.hass.states.get(source)
            if state is not None and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    snapshot[source] = round(float(state.state), 4)
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "Could not parse state '%s' of %s to float",
                        state.state,
                        source,
                    )
                    snapshot[source] = self.cycle_snapshot.get(source, 0.0)
            else:
                _LOGGER.warning(
                    "Source %s is currently unavailable or unknown; using baseline %s",
                    source,
                    self.cycle_snapshot.get(source, 0.0),
                )
                snapshot[source] = self.cycle_snapshot.get(source, 0.0)
        return snapshot

    async def async_get_snapshot_for_date(self, period_end_date: date) -> dict[str, float]:
        """Get source sensor snapshot for a given date.

        If period_end_date >= today, uses current source states.
        If in the past, queries recorder long-term statistics for the end of that day.
        Falls back to current state if statistics are missing for any source.
        """
        today = dt_util.now().date()
        if period_end_date >= today:
            return self.get_current_snapshot()

        try:
            tz = ZoneInfo(self.hass.config.time_zone)
        except Exception:
            tz = dt_util.DEFAULT_TIME_ZONE
        end_dt = datetime.combine(period_end_date, time(23, 59, 59), tzinfo=tz)
        start_dt = datetime.combine(period_end_date, time(0, 0, 0), tzinfo=tz)

        stats: dict[str, list[dict[str, Any]]] = {}
        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.statistics import statistics_during_period

            instance = get_instance(self.hass)
            stats = await instance.async_add_executor_job(
                statistics_during_period,
                self.hass,
                start_dt,
                end_dt,
                set(self.sources),
                "hour",
                None,
                {"state", "sum"},
            )
        except Exception as err:
            _LOGGER.warning(
                "Failed to query recorder statistics for %s: %s",
                period_end_date,
                err,
            )

        snapshot: dict[str, float] = {}
        current_snapshot = self.get_current_snapshot()

        for source in self.sources:
            source_stats = stats.get(source) if stats else None
            val: float | None = None

            if source_stats and isinstance(source_stats, list) and len(source_stats) > 0:
                last_stat = source_stats[-1]
                if last_stat.get("state") is not None:
                    try:
                        val = float(last_stat["state"])
                    except (ValueError, TypeError):
                        val = None
                if val is None and last_stat.get("sum") is not None:
                    try:
                        val = float(last_stat["sum"])
                    except (ValueError, TypeError):
                        val = None

            if val is not None:
                snapshot[source] = round(val, 4)
            else:
                _LOGGER.warning(
                    "Statistics missing for source %s on %s; falling back to current state",
                    source,
                    period_end_date,
                )
                snapshot[source] = current_snapshot.get(source, 0.0)

        return snapshot

    def _update_internal_data(self) -> None:
        """Recalculate internal entity data from current states and store."""
        current_snapshot = self.get_current_snapshot()
        cycle_kwh, per_source = calculate_cycle_kwh(current_snapshot, self.cycle_snapshot)

        latest_bill = self.bills[-1] if self.bills else None

        if latest_bill is not None:
            effective_rate = float(latest_bill.get("rate") or self.fallback_rate)
            rate_source = "bill"
            based_on_period_end = latest_bill.get("period_end")
            cycle_start = latest_bill.get("period_end")
            last_bill_amount = latest_bill.get("amount")
            last_bill_kwh = latest_bill.get("kwh")
            unmetered, share_metered = calculate_unmetered_kwh(
                last_bill_kwh,
                latest_bill.get("measured_kwh", 0.0),
            )
            last_bill_measured = latest_bill.get("measured_kwh")
        else:
            effective_rate = self.fallback_rate
            rate_source = "fallback"
            based_on_period_end = None
            cycle_start = None
            last_bill_amount = None
            last_bill_kwh = None
            unmetered = None
            share_metered = None
            last_bill_measured = None

        now_date_str = dt_util.now().date().isoformat()
        days_in_cycle = calculate_days_in_cycle(cycle_start, now_date_str)
        cycle_cost = calculate_cycle_cost(cycle_kwh, effective_rate)

        self.data = {
            "cycle_kwh": cycle_kwh,
            "per_source": per_source,
            "cycle_start": cycle_start,
            "days_in_cycle": days_in_cycle,
            "effective_rate": effective_rate,
            "rate_source": rate_source,
            "based_on_period_end": based_on_period_end,
            "cycle_cost_estimate": cycle_cost,
            "last_bill_amount": last_bill_amount,
            "last_bill_kwh": last_bill_kwh,
            "last_bill_unmetered_kwh": unmetered,
            "last_bill_measured_kwh": last_bill_measured,
            "share_metered_percent": share_metered,
            "last_bill": latest_bill,
            "bill_count": len(self.bills),
            "bill_history": format_bill_history(self.bills, max_items=24),
        }

    async def async_add_bill(
        self,
        period_end: date | str | None,
        kwh: float,
        amount: float,
        note: str = "",
        replace: bool = False,
    ) -> None:
        """Add a monthly electricity bill, compute rate/measured_kwh, and reset cycle baseline."""
        if kwh is None or float(kwh) <= 0:
            raise ServiceValidationError(
                "kWh must be greater than zero.",
                translation_domain=DOMAIN,
                translation_key="invalid_kwh",
            )

        if amount is None or float(amount) <= 0:
            raise ServiceValidationError(
                "Amount must be greater than zero.",
                translation_domain=DOMAIN,
                translation_key="invalid_amount",
            )

        if period_end is None:
            period_end_date = dt_util.now().date()
        elif isinstance(period_end, str):
            try:
                period_end_date = datetime.strptime(period_end, "%Y-%m-%d").date()
            except ValueError as err:
                raise ServiceValidationError(
                    f"Invalid date format for period_end: {period_end}",
                    translation_domain=DOMAIN,
                    translation_key="invalid_date",
                ) from err
        elif isinstance(period_end, datetime):
            period_end_date = period_end.date()
        elif isinstance(period_end, date):
            period_end_date = period_end
        else:
            period_end_date = dt_util.now().date()

        period_end_str = period_end_date.isoformat()

        if check_duplicate_period_end(self.bills, period_end_str, replace=replace):
            raise ServiceValidationError(
                f"A bill with period end {period_end_str} already exists. Pass replace: true to overwrite.",
                translation_domain=DOMAIN,
                translation_key="duplicate_period_end",
                translation_placeholders={"period_end": period_end_str},
            )

        snapshot = await self.async_get_snapshot_for_date(period_end_date)
        rate = calculate_rate(amount, kwh)

        new_bill = {
            "id": str(uuid.uuid4()),
            "period_start": None,
            "period_end": period_end_str,
            "kwh": float(kwh),
            "amount": float(amount),
            "rate": rate,
            "snapshot": snapshot,
            "measured_kwh": 0.0,
            "note": str(note or ""),
        }

        self.bills, _ = add_bill_record(self.bills, new_bill, replace=replace)
        if self.bills:
            self.cycle_snapshot = dict(self.bills[-1].get("snapshot", snapshot))
        else:
            self.cycle_snapshot = snapshot

        await self.store.async_save(
            {
                "bills": self.bills,
                "cycle_snapshot": self.cycle_snapshot,
            }
        )

        self._update_internal_data()
        self.async_update_listeners()

    async def async_remove_bill(
        self,
        bill_id: str | None = None,
        period_end: date | str | None = None,
    ) -> None:
        """Remove a bill by id or period_end, recompute deltas, and restore cycle baseline if needed."""
        if not bill_id and not period_end:
            raise ServiceValidationError(
                "Either id or period_end must be provided to remove a bill.",
                translation_domain=DOMAIN,
                translation_key="missing_bill_identifier",
            )

        period_end_str: str | None = None
        if period_end is not None:
            if isinstance(period_end, (date, datetime)):
                period_end_str = period_end.strftime("%Y-%m-%d")
            else:
                period_end_str = str(period_end)

        try:
            remaining, _, restored_snapshot = remove_bill_record(
                self.bills,
                bill_id=bill_id,
                period_end=period_end_str,
            )
        except ValueError as err:
            raise ServiceValidationError(
                "Bill with the specified ID or period end was not found.",
                translation_domain=DOMAIN,
                translation_key="bill_not_found",
            ) from err

        self.bills = remaining
        if restored_snapshot is not None:
            if not restored_snapshot and self.sources:
                self.cycle_snapshot = self.get_current_snapshot()
            else:
                self.cycle_snapshot = restored_snapshot

        await self.store.async_save(
            {
                "bills": self.bills,
                "cycle_snapshot": self.cycle_snapshot,
            }
        )

        self._update_internal_data()
        self.async_update_listeners()

    async def async_reset_cycle(self) -> None:
        """Reset current cycle snapshot to current source states without recording a bill."""
        self.cycle_snapshot = self.get_current_snapshot()
        await self.store.async_save(
            {
                "bills": self.bills,
                "cycle_snapshot": self.cycle_snapshot,
            }
        )
        self._update_internal_data()
        self.async_update_listeners()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectricityBillConfigEntry,
) -> bool:
    """Set up Electricity Bill from a config entry."""
    store = ElectricityBillStore(hass, entry.entry_id)
    coordinator = ElectricityBillCoordinator(hass, entry, store)
    await coordinator.async_setup()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ElectricityBillConfigEntry,
) -> bool:
    """Unload an Electricity Bill config entry."""
    coordinator = entry.runtime_data
    coordinator.async_unload()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # If this was the last entry, remove services
    entries = hass.config_entries.async_entries(DOMAIN)
    if len(entries) <= 1:
        if hass.services.has_service(DOMAIN, SERVICE_ADD_BILL):
            hass.services.async_remove(DOMAIN, SERVICE_ADD_BILL)
        if hass.services.has_service(DOMAIN, SERVICE_REMOVE_BILL):
            hass.services.async_remove(DOMAIN, SERVICE_REMOVE_BILL)
        if hass.services.has_service(DOMAIN, SERVICE_RESET_CYCLE):
            hass.services.async_remove(DOMAIN, SERVICE_RESET_CYCLE)

    return unload_ok


async def async_reload_entry(
    hass: HomeAssistant,
    entry: ElectricityBillConfigEntry,
) -> None:
    """Reload an Electricity Bill config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_ADD_BILL):
        return

    async def handle_add_bill(call: ServiceCall) -> None:
        entries: list[ElectricityBillConfigEntry] = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError(
                "No Electricity Bill integration configured.",
                translation_domain=DOMAIN,
                translation_key="no_energy_sources",
            )
        coordinator = entries[0].runtime_data
        await coordinator.async_add_bill(
            period_end=call.data.get(ATTR_PERIOD_END),
            kwh=call.data.get(ATTR_KWH),
            amount=call.data.get(ATTR_AMOUNT),
            note=call.data.get(ATTR_NOTE, ""),
            replace=call.data.get(ATTR_REPLACE, False),
        )

    async def handle_remove_bill(call: ServiceCall) -> None:
        entries: list[ElectricityBillConfigEntry] = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError(
                "No Electricity Bill integration configured.",
                translation_domain=DOMAIN,
                translation_key="no_energy_sources",
            )
        coordinator = entries[0].runtime_data
        await coordinator.async_remove_bill(
            bill_id=call.data.get(ATTR_ID),
            period_end=call.data.get(ATTR_PERIOD_END),
        )

    async def handle_reset_cycle(call: ServiceCall) -> None:
        entries: list[ElectricityBillConfigEntry] = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError(
                "No Electricity Bill integration configured.",
                translation_domain=DOMAIN,
                translation_key="no_energy_sources",
            )
        coordinator = entries[0].runtime_data
        await coordinator.async_reset_cycle()

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_BILL,
        handle_add_bill,
        schema=ADD_BILL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_BILL,
        handle_remove_bill,
        schema=REMOVE_BILL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_CYCLE,
        handle_reset_cycle,
        schema=RESET_CYCLE_SCHEMA,
    )
