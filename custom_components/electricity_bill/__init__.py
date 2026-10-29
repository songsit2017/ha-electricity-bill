"""Electricity Bill custom integration for Home Assistant."""
from __future__ import annotations
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
import logging
import math
from typing import Any
import uuid
from zoneinfo import ZoneInfo

from pathlib import Path
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .views import PanelAssetView, ScanView

from .calc import (
    add_bill_record,
    calculate_cycle_cost,
    calculate_cycle_kwh,
    calculate_cycle_unmetered_kwh,
    calculate_daily_average,
    format_summary,
    history_from_daily_changes,
    implied_ft_rate,
    merge_history,
    summarize_period,
    is_high_usage,
    roll_day,
    estimate_bill,
    forecast_cycle_kwh,
    next_cutoff_date,
    parse_tariff_tiers,
    calculate_source_delta,
    calculate_days_in_cycle,
    calculate_rate,
    calculate_unmetered_kwh,
    check_duplicate_period_end,
    format_bill_history,
    remove_bill_record,
)
from .const import (
    ATTR_AMOUNT,
    ATTR_ENERGY_CHARGE,
    ATTR_FT_CHARGE,
    ATTR_ID,
    ATTR_KWH,
    ATTR_NOTE,
    ATTR_PERIOD_END,
    ATTR_PERIOD_START,
    ATTR_REPLACE,
    ATTR_SERVICE_CHARGE,
    ATTR_VAT,
    CONF_BUDGET_THRESHOLD,
    CONF_CUTOFF_DAY_30,
    CONF_CUTOFF_DAY_31,
    CONF_CUTOFF_DAY_FEB,
    CONF_FALLBACK_RATE,
    CONF_FT_RATE,
    CONF_HIGH_USAGE_FACTOR,
    CONF_SUMMARY_HOUR,
    CONF_WEEKLY_DAY,
    CONF_MAIN_METER,
    CONF_TARIFF_PROFILE,
    CONF_TARIFF_TIERS,
    CONF_NAME,
    CONF_RESET_BUTTON,
    CONF_SERVICE_CHARGE,
    CONF_SOURCES,
    CONF_VAT_PERCENT,
    DEFAULT_TARIFF_PROFILE,
    PROFILE_CUSTOM,
    PROFILE_NONE,
    PROFILE_THAILAND,
    THAILAND_CUTOFF_DAY_30,
    THAILAND_CUTOFF_DAY_31,
    THAILAND_CUTOFF_DAY_FEB,
    THAILAND_FT_RATE,
    THAILAND_SERVICE_CHARGE,
    THAILAND_VAT_PERCENT,
    EVENT_BUDGET_EXCEEDED,
    EVENT_CUTOFF_DAY,
    EVENT_HIGH_USAGE,
    HIGH_USAGE_MIN_KWH,
    DAY_RECORD_VERSION,
    DEFAULT_SUMMARY_HOUR,
    DEFAULT_WEEKLY_DAY,
    EVENT_DAILY_SUMMARY,
    EVENT_WEEKLY_SUMMARY,
    HISTORY_MAX_DAYS,
    TARIFF_SMALL_USER_LIMIT_KWH,
    TARIFF_TIERS_OVER_150,
    TARIFF_TIERS_UP_TO_150,
    DEFAULT_FALLBACK_RATE,
    DEFAULT_NAME,
    DOMAIN,
    SERVICE_ADD_BILL,
    SERVICE_REMOVE_BILL,
    SERVICE_RESET_CYCLE,
    SERVICE_SET_BASELINE,
    SERVICE_GET_SUMMARY,
    SUMMARY_KINDS,
    ISSUE_SOURCE_UNAVAILABLE,
    ISSUE_FT_OUTDATED,
    SOURCE_UNAVAILABLE_ISSUE_AFTER,
    BACKFILL_DAYS,
)
from .store import ElectricityBillStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type ElectricityBillConfigEntry = ConfigEntry["ElectricityBillCoordinator"]

ADD_BILL_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_PERIOD_START): cv.date,
        vol.Optional(ATTR_PERIOD_END): cv.date,
        vol.Required(ATTR_KWH): vol.Coerce(float),
        vol.Required(ATTR_AMOUNT): vol.Coerce(float),
        vol.Optional(ATTR_ENERGY_CHARGE): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0))),
        vol.Optional(ATTR_FT_CHARGE): vol.Any(None, vol.Coerce(float)),
        vol.Optional(ATTR_SERVICE_CHARGE): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0))),
        vol.Optional(ATTR_VAT): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0))),
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

SET_BASELINE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("value", default=0.0): vol.Coerce(float),
    }
)


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
        self._unsub_reset_watch: Callable[[], None] | None = None
        self._unsub_time: list[Callable[[], None]] = []
        self._budget_notified: str | None = None
        self._day: dict[str, Any] | None = None
        self._yesterday_kwh: float | None = None
        self._high_usage_notified: str | None = None
        self._history: list[dict[str, Any]] = []
        self._source_missing_since: datetime | None = None
        self._active_issues: set[str] = set()

    def _opt(self, key: str, default: Any) -> Any:
        value = self.entry.options.get(key, self.entry.data.get(key))
        return default if value is None else value

    @property
    def tariff_profile(self) -> str:
        profile = self._opt(CONF_TARIFF_PROFILE, DEFAULT_TARIFF_PROFILE)
        return profile if profile in (PROFILE_NONE, PROFILE_THAILAND, PROFILE_CUSTOM) else PROFILE_NONE

    def _profile_default(self, thailand_value: Any, other_value: Any) -> Any:
        return thailand_value if self.tariff_profile == PROFILE_THAILAND else other_value

    @property
    def ft_rate(self) -> float:
        return float(self._opt(CONF_FT_RATE, self._profile_default(THAILAND_FT_RATE, 0.0)))

    @property
    def service_charge(self) -> float:
        return float(self._opt(CONF_SERVICE_CHARGE, self._profile_default(THAILAND_SERVICE_CHARGE, 0.0)))

    @property
    def vat_percent(self) -> float:
        return float(self._opt(CONF_VAT_PERCENT, self._profile_default(THAILAND_VAT_PERCENT, 0.0)))

    @property
    def cutoff_days(self) -> tuple[int, int, int] | None:
        """Billing day by month length (30-day, 31-day, February), or None when not set."""
        d30 = self._opt(CONF_CUTOFF_DAY_30, self._profile_default(THAILAND_CUTOFF_DAY_30, None))
        d31 = self._opt(CONF_CUTOFF_DAY_31, self._profile_default(THAILAND_CUTOFF_DAY_31, None))
        dfeb = self._opt(CONF_CUTOFF_DAY_FEB, self._profile_default(THAILAND_CUTOFF_DAY_FEB, None))
        if d30 is None or d31 is None:
            return None
        return int(d30), int(d31), int(dfeb if dfeb is not None else d30)

    @property
    def high_usage_factor(self) -> float | None:
        value = self._opt(CONF_HIGH_USAGE_FACTOR, None)
        try:
            value = float(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None
        return value if value and value > 0 else None

    @property
    def summary_hour(self) -> int:
        try:
            return min(23, max(0, int(self._opt(CONF_SUMMARY_HOUR, DEFAULT_SUMMARY_HOUR))))
        except (TypeError, ValueError):
            return DEFAULT_SUMMARY_HOUR

    @property
    def weekly_day(self) -> int:
        try:
            return min(6, max(0, int(self._opt(CONF_WEEKLY_DAY, DEFAULT_WEEKLY_DAY))))
        except (TypeError, ValueError):
            return DEFAULT_WEEKLY_DAY

    @property
    def budget_threshold(self) -> float | None:
        value = self._opt(CONF_BUDGET_THRESHOLD, None)
        try:
            value = float(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None
        return value if value and value > 0 else None

    def _tiers(self) -> tuple[Any, Any, float] | None:
        """Return (tiers_over, tiers_up_to, small_user_limit) of the profile, None without tiers."""
        profile = self.tariff_profile
        if profile == PROFILE_THAILAND:
            return TARIFF_TIERS_OVER_150, TARIFF_TIERS_UP_TO_150, TARIFF_SMALL_USER_LIMIT_KWH
        if profile == PROFILE_CUSTOM:
            try:
                tiers = parse_tariff_tiers(self._opt(CONF_TARIFF_TIERS, ""))
            except ValueError:
                _LOGGER.warning("Invalid custom tariff tiers; falling back to the effective rate")
                return None
            return tiers, tiers, 0.0
        return None

    def _estimate(self, kwh: float) -> dict[str, float]:
        """Estimate a bill for ``kwh``: tiered tariff when configured, else effective rate."""
        tiers = self._tiers()
        if tiers is None:
            latest = self.bills[-1] if self.bills else None
            rate = float(latest.get("rate") or self.fallback_rate) if latest else self.fallback_rate
            total = round(max(0.0, float(kwh)) * rate, 2)
            return {
                "energy_charge": total,
                "ft_charge": 0.0,
                "service_charge": 0.0,
                "subtotal": total,
                "vat": 0.0,
                "total": total,
            }
        over, up_to, small_limit = tiers
        return estimate_bill(
            kwh, over, up_to, small_limit, self.ft_rate, self.service_charge, self.vat_percent
        )

    @property
    def configured_sources(self) -> list[str]:
        """Return the configured source sensors (sub-meters when a main meter is set)."""
        return list(
            self.entry.options.get(
                CONF_SOURCES,
                self.entry.data.get(CONF_SOURCES, []),
            )
        )

    @property
    def main_meter(self) -> str | None:
        """Return the whole-house main meter entity id, if configured."""
        return self.entry.options.get(
            CONF_MAIN_METER, self.entry.data.get(CONF_MAIN_METER)
        ) or None

    @property
    def reset_button(self) -> str | None:
        """Return the button entity that resets the main meter, if configured."""
        return self.entry.options.get(
            CONF_RESET_BUTTON, self.entry.data.get(CONF_RESET_BUTTON)
        ) or None

    @property
    def sources(self) -> list[str]:
        """Return every tracked sensor: the main meter first, then the other sources."""
        main = self.main_meter
        result: list[str] = [main] if main else []
        for source in self.configured_sources:
            if source not in result:
                result.append(source)
        return result

    @property
    def total_sources(self) -> list[str]:
        """Return the sensors whose energy forms the total (main meter alone, else all sources)."""
        main = self.main_meter
        return [main] if main else self.configured_sources

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
        self._budget_notified = stored.get("budget_notified")
        stored_day = stored.get("day")
        self._day = stored_day if stored_day and stored_day.get("v") == DAY_RECORD_VERSION else None
        self._yesterday_kwh = stored.get("yesterday_kwh")
        self._high_usage_notified = stored.get("high_usage_notified")
        self._history = list(stored.get("daily_history") or [])

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

        @callback
        def _midnight(_now: datetime) -> None:
            self._update_internal_data()
            self.async_update_listeners()

        @callback
        def _noon(_now: datetime) -> None:
            self._fire_cutoff_event()

        @callback
        def _summary(_now: datetime) -> None:
            self._fire_summaries()

        self._unsub_time = [
            async_track_time_change(self.hass, _midnight, hour=0, minute=0, second=5),
            async_track_time_change(self.hass, _noon, hour=12, minute=0, second=0),
            async_track_time_change(self.hass, _summary, hour=self.summary_hour, minute=0, second=30),
        ]

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

        if len(self._history) < 14 and self.sources:
            self.entry.async_create_background_task(
                self.hass, self._async_backfill_history(), "electricity_bill_backfill"
            )

    def async_unload(self) -> None:
        """Unload coordinator listeners."""
        if self._unsub_track is not None:
            self._unsub_track()
            self._unsub_track = None
        if self._unsub_reset_watch is not None:
            self._unsub_reset_watch()
            self._unsub_reset_watch = None
        for unsub in self._unsub_time:
            unsub()
        self._unsub_time = []

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
        cycle_kwh, per_source = calculate_cycle_kwh(
            current_snapshot, self.cycle_snapshot, only=self.total_sources
        )
        today_kwh: float | None = None
        if self._total_sources_ready():
            today_date = dt_util.now().date()
            previous_day = self._day
            record, rolled_yesterday, changed = roll_day(
                self._day,
                today_date.isoformat(),
                (today_date - timedelta(days=1)).isoformat(),
                current_snapshot,
                only=self.total_sources,
            )
            if changed:
                new_day = self._day is None or self._day.get("date") != record["date"]
                record["v"] = DAY_RECORD_VERSION
                self._day = record
                if new_day:
                    self._yesterday_kwh = (
                        round(rolled_yesterday, 3) if rolled_yesterday is not None else None
                    )
                    if rolled_yesterday is not None and previous_day is not None:
                        self._append_history(previous_day, current_snapshot, rolled_yesterday)
                self.hass.async_create_task(self._async_save_day())
            today_kwh, _ = calculate_cycle_kwh(
                current_snapshot, self._day.get("snapshot", {}), only=self.total_sources
            )

        main_meter = self.main_meter
        if main_meter:
            submetered_kwh, cycle_unmetered_kwh = calculate_cycle_unmetered_kwh(
                cycle_kwh, per_source, main_meter
            )
        else:
            submetered_kwh, cycle_unmetered_kwh = None, None

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

        today = dt_util.now().date()
        cutoff_days = self.cutoff_days
        cutoff = next_cutoff_date(today, *cutoff_days) if cutoff_days else None
        bill_estimate = self._estimate(cycle_kwh)
        forecast = (
            forecast_cycle_kwh(cycle_kwh, cycle_start, today, cutoff) if cutoff else None
        )
        if forecast is not None:
            kwh_per_day, forecast_kwh, forecast_days = forecast
            forecast_bill = self._estimate(forecast_kwh)
        else:
            kwh_per_day = forecast_kwh = forecast_days = None
            forecast_bill = None

        self.data = {
            "cycle_kwh": cycle_kwh,
            "per_source": per_source,
            "main_meter": main_meter,
            "cycle_submetered_kwh": submetered_kwh,
            "cycle_unmetered_kwh": cycle_unmetered_kwh,
            "cycle_start": cycle_start,
            "days_in_cycle": days_in_cycle,
            "today_kwh": round(today_kwh, 3) if today_kwh is not None else None,
            "yesterday_kwh": self._yesterday_kwh,
            "daily_average_kwh": calculate_daily_average(cycle_kwh, days_in_cycle),
            "effective_rate": effective_rate,
            "rate_source": rate_source,
            "based_on_period_end": based_on_period_end,
            "cycle_cost_estimate": cycle_cost,
            "cycle_bill_estimate": bill_estimate,
            "next_cutoff": cutoff,
            "forecast": (
                {
                    "kwh_per_day": kwh_per_day,
                    "kwh": forecast_kwh,
                    "days": forecast_days,
                    "bill": forecast_bill,
                }
                if forecast_bill is not None
                else None
            ),
            "last_bill_amount": last_bill_amount,
            "last_bill_kwh": last_bill_kwh,
            "last_bill_unmetered_kwh": unmetered,
            "last_bill_measured_kwh": last_bill_measured,
            "share_metered_percent": share_metered,
            "last_bill": latest_bill,
            "bill_count": len(self.bills),
            "bill_history": format_bill_history(self.bills, max_items=24),
        }
        self._check_budget()
        self._check_high_usage()
        self._check_issues()

    @callback
    def _check_budget(self) -> None:
        """Fire a one-off event per cycle when the estimated bill reaches the budget."""
        threshold = self.budget_threshold
        if threshold is None or not self.data:
            return
        total = (self.data.get("cycle_bill_estimate") or {}).get("total", 0.0)
        cycle_key = self.data.get("cycle_start") or "none"
        if total < threshold or self._budget_notified == cycle_key:
            return
        self._budget_notified = cycle_key
        self.hass.bus.async_fire(
            EVENT_BUDGET_EXCEEDED,
            {
                "threshold": threshold,
                "bill_estimate": total,
                "cycle_kwh": self.data.get("cycle_kwh"),
                "cycle_start": self.data.get("cycle_start"),
            },
        )
        self.hass.async_create_task(
            self.store.async_set_extra("budget_notified", cycle_key)
        )

    def _total_sources_ready(self) -> bool:
        """True when every source forming the total has a numeric state."""
        for source in self.total_sources:
            state = self.hass.states.get(source)
            if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                return False
            try:
                float(state.state)
            except (TypeError, ValueError):
                return False
        return bool(self.total_sources)

    @callback
    def _append_history(
        self,
        previous_day: dict[str, Any],
        current_snapshot: dict[str, float],
        total_kwh: float,
    ) -> None:
        """Remember the finished day (its date, total and per-source energy) for the weekly summary."""
        _, per_source = calculate_cycle_kwh(current_snapshot, previous_day.get("snapshot", {}))
        entry = {
            "date": previous_day.get("date"),
            "kwh": round(total_kwh, 3),
            "per_source": {k: round(v, 3) for k, v in per_source.items()},
        }
        self._history = [h for h in self._history if h.get("date") != entry["date"]]
        self._history.append(entry)
        self._history = sorted(self._history, key=lambda h: str(h.get("date")))[-HISTORY_MAX_DAYS:]

    def _device_list(self, per_source: dict[str, float]) -> list[tuple[str, float]]:
        """Sub-meter energy by device name, biggest first (the main meter itself is left out)."""
        main = self.main_meter
        devices = []
        for entity_id, kwh in per_source.items():
            if entity_id == main:
                continue
            state = self.hass.states.get(entity_id)
            name = (state.attributes.get("friendly_name") if state else None) or entity_id
            devices.append((str(name).replace("_kwh", "").replace("_", " ").strip(), float(kwh)))
        return sorted(devices, key=lambda x: x[1], reverse=True)

    def _summary_payload(self, kind: str) -> dict[str, Any] | None:
        """Data and ready-made text for a daily, weekly or cycle summary (None without data)."""
        if not self.data:
            return None
        today = dt_util.now().date()
        lang = (self.hass.config.language or "en").split("-")[0].lower()
        currency = {"THB": "฿"}.get(self.hass.config.currency, f"{self.hass.config.currency} ")
        rate = float(self.data.get("effective_rate") or 0.0)
        forecast = (self.data.get("forecast") or {}).get("bill") or {}
        base: dict[str, Any] = {
            "currency": currency,
            "rate": rate,
            "cycle_kwh": self.data.get("cycle_kwh"),
            "cycle_bill": (self.data.get("cycle_bill_estimate") or {}).get("total"),
            "forecast_bill": forecast.get("total"),
        }
        if kind == "cycle":
            cutoff = self.data.get("next_cutoff")
            start = self.data.get("cycle_start") or today.isoformat()
            fields = dict(
                base,
                start=start,
                end=today.isoformat(),
                days=self.data.get("days_in_cycle") or 0,
                avg_kwh=self.data.get("daily_average_kwh"),
                devices=self._device_list(self.data.get("per_source") or {}),
                last_bill_kwh=self.data.get("last_bill_kwh"),
                last_bill_amount=self.data.get("last_bill_amount"),
                next_cutoff=cutoff.isoformat() if cutoff else None,
                reminder=cutoff == today,
            )
            return {
                "kind": "cycle",
                "start": start,
                "end": today.isoformat(),
                "cycle_kwh": self.data.get("cycle_kwh"),
                "bill_estimate": base["cycle_bill"],
                "forecast_bill": base["forecast_bill"],
                "devices": [{"name": n, "kwh": round(k, 3)} for n, k in fields["devices"]],
                "message": format_summary("cycle", lang, fields),
            }
        today_kwh = self.data.get("today_kwh")
        if today_kwh is None or not self._day:
            return None
        current_snapshot = self.get_current_snapshot()
        _, today_per_source = calculate_cycle_kwh(current_snapshot, self._day.get("snapshot", {}))
        if kind == "daily":
            fields = dict(
                base,
                date=today.isoformat(),
                today_kwh=today_kwh,
                yesterday_kwh=self._yesterday_kwh,
                avg_kwh=self.data.get("daily_average_kwh"),
                devices=self._device_list(today_per_source),
            )
            return {
                "kind": "daily",
                "date": today.isoformat(),
                "today_kwh": today_kwh,
                "yesterday_kwh": self._yesterday_kwh,
                "daily_average_kwh": self.data.get("daily_average_kwh"),
                "cost_estimate": round(today_kwh * rate, 2),
                "devices": [{"name": n, "kwh": round(k, 3)} for n, k in fields["devices"]],
                "message": format_summary("daily", lang, fields),
            }
        week = summarize_period(self._history, today, today_kwh, today_per_source, days=7)
        fields = dict(
            base,
            start=week["start"],
            end=week["end"],
            kwh=week["kwh"],
            avg_per_day=week["avg_per_day"],
            known_days=week["known_days"],
            peak=week["peak"],
            change_pct=week["change_pct"],
            devices=self._device_list(week["per_source"]),
        )
        return {
            "kind": "weekly",
            "start": week["start"],
            "end": week["end"],
            "kwh": week["kwh"],
            "avg_per_day": week["avg_per_day"],
            "known_days": week["known_days"],
            "cost_estimate": round(week["kwh"] * rate, 2),
            "change_pct": week["change_pct"],
            "peak": week["peak"],
            "devices": [{"name": n, "kwh": round(k, 3)} for n, k in fields["devices"]],
            "message": format_summary("weekly", lang, fields),
        }

    @callback
    def _fire_summaries(self) -> None:
        """At the summary hour fire the daily summary and, on the weekly day, the weekly one."""
        daily = self._summary_payload("daily")
        if daily is None:
            return
        self.hass.bus.async_fire(EVENT_DAILY_SUMMARY, daily)
        if dt_util.now().date().weekday() == self.weekly_day:
            weekly = self._summary_payload("weekly")
            if weekly is not None:
                self.hass.bus.async_fire(EVENT_WEEKLY_SUMMARY, weekly)

    async def _async_backfill_history(self) -> None:
        """Fill missing finished days of the daily history from the recorder's daily statistics."""
        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.statistics import statistics_during_period

            today = dt_util.now().date()
            start_dt = dt_util.start_of_local_day(today - timedelta(days=BACKFILL_DAYS))
            end_dt = dt_util.start_of_local_day(today)
            stats = await get_instance(self.hass).async_add_executor_job(
                statistics_during_period,
                self.hass,
                start_dt,
                end_dt,
                set(self.sources),
                "day",
                None,
                {"change"},
            )
        except Exception as err:  # noqa: BLE001 - backfill is best effort
            _LOGGER.debug("Daily history backfill skipped: %s", err)
            return
        changes: dict[str, dict[str, float]] = {}
        for source, rows in (stats or {}).items():
            for row in rows or []:
                change = row.get("change")
                start = row.get("start")
                if change is None or start is None:
                    continue
                if isinstance(start, (int, float)):
                    start = dt_util.utc_from_timestamp(start)
                day = dt_util.as_local(start).date().isoformat()
                changes.setdefault(day, {})[source] = float(change)
        extra = history_from_daily_changes(changes, self.total_sources)
        merged = merge_history(self._history, extra, HISTORY_MAX_DAYS)
        if len(merged) != len(self._history):
            _LOGGER.debug("Backfilled %s day(s) of history", len(merged) - len(self._history))
            self._history = merged
            await self.store.async_set_extra("daily_history", self._history)

    @callback
    def _check_issues(self) -> None:
        """Raise or clear Repairs issues: a total source unavailable for long, an outdated Ft."""
        # 1. total source unavailable for more than SOURCE_UNAVAILABLE_ISSUE_AFTER seconds
        if self._total_sources_ready():
            self._source_missing_since = None
            self._set_issue(ISSUE_SOURCE_UNAVAILABLE, False)
        else:
            now = dt_util.utcnow()
            if self._source_missing_since is None:
                self._source_missing_since = now
            elif (now - self._source_missing_since).total_seconds() > SOURCE_UNAVAILABLE_ISSUE_AFTER:
                self._set_issue(
                    ISSUE_SOURCE_UNAVAILABLE,
                    True,
                    {"entities": ", ".join(self.total_sources)},
                )
        # 2. Ft from the latest bill differs from the configured Ft (tariff profiles only)
        implied = implied_ft_rate(self.bills[-1] if self.bills else None)
        outdated = (
            self._tiers() is not None
            and implied is not None
            and abs(implied - self.ft_rate) > 0.0006
        )
        self._set_issue(
            ISSUE_FT_OUTDATED,
            outdated,
            {"bill_ft": f"{implied:.4f}" if implied is not None else "-", "configured_ft": f"{self.ft_rate:.4f}"},
        )

    def _set_issue(self, issue_id: str, active: bool, placeholders: dict[str, str] | None = None) -> None:
        if active and issue_id not in self._active_issues:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=issue_id,
                translation_placeholders=placeholders or {},
            )
            self._active_issues.add(issue_id)
        elif not active and issue_id in self._active_issues:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            self._active_issues.discard(issue_id)

    async def _async_save_day(self) -> None:
        """Persist the day-start record and yesterday's total (extra keys of the store)."""
        await self.store.async_set_extra("day", self._day)
        await self.store.async_set_extra("yesterday_kwh", self._yesterday_kwh)
        await self.store.async_set_extra("daily_history", self._history)

    @callback
    def _check_high_usage(self) -> None:
        """Fire a one-off event per day when today's energy is far above the cycle average."""
        factor = self.high_usage_factor
        if factor is None or not self.data or not self._day:
            return
        today_kwh = self.data.get("today_kwh")
        if today_kwh is None:
            return
        average = self.data.get("daily_average_kwh") or 0.0
        day = self._day.get("date")
        if self._high_usage_notified == day or not is_high_usage(
            today_kwh, average, factor, HIGH_USAGE_MIN_KWH
        ):
            return
        self._high_usage_notified = day
        self.hass.bus.async_fire(
            EVENT_HIGH_USAGE,
            {
                "date": day,
                "today_kwh": today_kwh,
                "daily_average_kwh": average,
                "factor": factor,
            },
        )
        self.hass.async_create_task(self.store.async_set_extra("high_usage_notified", day))

    @callback
    def _fire_cutoff_event(self) -> None:
        """At noon on a cut-off day fire an event with the cycle summary."""
        if not self.data:
            return
        today = dt_util.now().date()
        cutoff = self.data.get("next_cutoff")
        if cutoff != today:
            return
        forecast = self.data.get("forecast") or {}
        self.hass.bus.async_fire(
            EVENT_CUTOFF_DAY,
            {
                "cutoff_date": today.isoformat(),
                "cycle_kwh": self.data.get("cycle_kwh"),
                "bill_estimate": (self.data.get("cycle_bill_estimate") or {}).get("total"),
                "forecast_bill": (forecast.get("bill") or {}).get("total"),
                "message": (self._summary_payload("cycle") or {}).get("message"),
            },
        )

    async def async_add_bill(
        self,
        period_end: date | str | None,
        kwh: float,
        amount: float,
        note: str = "",
        replace: bool = False,
        period_start: date | str | None = None,
        energy_charge: float | None = None,
        ft_charge: float | None = None,
        service_charge: float | None = None,
        vat: float | None = None,
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

        # Parse and validate period_start if provided
        period_start_date: date | None = None
        if period_start is not None and str(period_start).strip() != "":
            if isinstance(period_start, str):
                try:
                    period_start_date = datetime.strptime(period_start.strip(), "%Y-%m-%d").date()
                except ValueError as err:
                    raise ServiceValidationError(
                        f"Invalid date format for period_start: {period_start}",
                        translation_domain=DOMAIN,
                        translation_key="invalid_date",
                    ) from err
            elif isinstance(period_start, datetime):
                period_start_date = period_start.date()
            elif isinstance(period_start, date):
                period_start_date = period_start

        if period_start_date is not None and period_start_date > period_end_date:
            raise ServiceValidationError(
                "Period start date must be before or equal to period end date.",
                translation_domain=DOMAIN,
                translation_key="invalid_period",
            )

        period_start_str = period_start_date.isoformat() if period_start_date is not None else None

        # Validate charge amounts
        def _validate_charge(val: Any, name: str, allow_negative: bool = False) -> float | None:
            if val is None or str(val).strip() == "":
                return None
            try:
                f_val = float(val)
            except (ValueError, TypeError) as err:
                raise ServiceValidationError(
                    f"{name} must be a valid number.",
                    translation_domain=DOMAIN,
                    translation_key="invalid_charge",
                ) from err
            if not math.isfinite(f_val):
                raise ServiceValidationError(
                    f"{name} must be a finite number.",
                    translation_domain=DOMAIN,
                    translation_key="invalid_charge",
                )
            if not allow_negative and f_val < 0:
                raise ServiceValidationError(
                    f"{name} cannot be negative.",
                    translation_domain=DOMAIN,
                    translation_key="invalid_charge",
                )
            return round(f_val, 2)

        valid_energy = _validate_charge(energy_charge, "Energy charge", allow_negative=False)
        valid_ft = _validate_charge(ft_charge, "Ft charge", allow_negative=True)
        valid_service = _validate_charge(service_charge, "Service charge", allow_negative=False)
        valid_vat = _validate_charge(vat, "VAT", allow_negative=False)

        if check_duplicate_period_end(self.bills, period_end_str, replace=replace):
            raise ServiceValidationError(
                f"A bill with period end {period_end_str} already exists. Pass replace: true to overwrite.",
                translation_domain=DOMAIN,
                translation_key="duplicate_period_end",
                translation_placeholders={"period_end": period_end_str},
            )

        previous_newest = max((str(b.get("period_end", "")) for b in self.bills), default="")
        snapshot = await self.async_get_snapshot_for_date(period_end_date)
        rate = calculate_rate(amount, kwh)

        new_bill = {
            "id": str(uuid.uuid4()),
            "period_start": None,
            "period_start_manual": period_start_str,
            "period_end": period_end_str,
            "kwh": float(kwh),
            "amount": float(amount),
            "rate": rate,
            "snapshot": snapshot,
            "measured_kwh": 0.0,
            "note": str(note or ""),
            "energy_charge": valid_energy,
            "ft_charge": valid_ft,
            "service_charge": valid_service,
            "vat": valid_vat,
        }

        self.bills, _ = add_bill_record(
            self.bills, new_bill, replace=replace, only=self.total_sources
        )
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

        if previous_newest and period_end_str > previous_newest:
            await self._async_reset_main_meter_after_bill()

    async def _async_reset_main_meter_after_bill(self) -> None:
        """Press the main meter's reset button once and keep the energy used since period_end.

        The bill baseline for the main meter holds the meter value at period_end. When the
        counter drops back to 0 the baseline is rewritten to -carry, where carry is the energy
        used between period_end and the reset, so cycle energy = carry + new counter value.
        """
        main = self.main_meter
        button = self.reset_button
        if not main or not button:
            return
        state = self.hass.states.get(main)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.warning("Main meter %s unavailable; not pressing %s", main, button)
            return
        try:
            old_value = float(state.state)
        except (ValueError, TypeError):
            return
        carry = calculate_source_delta(old_value, self.cycle_snapshot.get(main, 0.0))

        if self._unsub_reset_watch is not None:
            self._unsub_reset_watch()
            self._unsub_reset_watch = None

        @callback
        def _on_main_change(event: Event) -> None:
            new_state = event.data.get("new_state")
            if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                return
            try:
                new_value = float(new_state.state)
            except (ValueError, TypeError):
                return
            if new_value >= old_value - 0.0005:
                return
            if self._unsub_reset_watch is not None:
                self._unsub_reset_watch()
                self._unsub_reset_watch = None
            baseline = -round(carry, 4) if carry > 0 else 0.0
            self.cycle_snapshot[main] = baseline
            if self.bills:
                self.bills[-1].setdefault("snapshot", {})[main] = baseline
            self.hass.async_create_task(self._async_save_and_refresh())

        self._unsub_reset_watch = async_track_state_change_event(
            self.hass, [main], _on_main_change
        )
        try:
            await self.hass.services.async_call(
                "button", "press", {"entity_id": button}, blocking=True
            )
        except Exception:  # noqa: BLE001 - a failed press must not fail add_bill
            _LOGGER.exception("Could not press reset button %s", button)
            if self._unsub_reset_watch is not None:
                self._unsub_reset_watch()
                self._unsub_reset_watch = None

    async def _async_save_and_refresh(self) -> None:
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
                only=self.total_sources,
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

    async def async_set_baseline(self, entity_id: str, value: float) -> None:
        """Set the cycle baseline of one source to an explicit meter value (cycle = current - value)."""
        if entity_id not in self.sources:
            raise ServiceValidationError(
                f"{entity_id} is not one of the configured source sensors.",
                translation_domain=DOMAIN,
                translation_key="unknown_source",
                translation_placeholders={"entity_id": entity_id},
            )
        self.cycle_snapshot[entity_id] = round(float(value), 4)
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

    hass.data.setdefault(DOMAIN, {})

    # Register API scan view once
    if not hass.data[DOMAIN].get("view_registered"):
        hass.http.register_view(ScanView)
        hass.data[DOMAIN]["view_registered"] = True

    # Register static path for custom panel once
    if not hass.data[DOMAIN].get("static_path_registered"):
        frontend_path = Path(__file__).parent / "frontend"
        hass.http.register_view(PanelAssetView(frontend_path))
        hass.data[DOMAIN]["static_path_registered"] = True

    # Register custom panel once
    if not hass.data[DOMAIN].get("panel_registered"):
        try:
            from homeassistant.components.panel_custom import async_register_panel
            from homeassistant.loader import async_get_integration

            # The version in the URL makes browsers (and the HA app) fetch the new panel.js
            # after an update instead of showing the cached old one.
            integration = await async_get_integration(hass, DOMAIN)

            await async_register_panel(
                hass,
                webcomponent_name="electricity-bill-panel",
                frontend_url_path="electricity",
                module_url=f"/electricity_bill_panel/panel.js?v={integration.version}",
                sidebar_title="ค่าไฟ",
                sidebar_icon="mdi:flash",
                require_admin=False,
                config={},
                embed_iframe=False,
            )
            hass.data[DOMAIN]["panel_registered"] = True
        except Exception as err:
            _LOGGER.warning("Could not register electricity panel: %s", err)

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

    # If this was the last entry, remove services and panel
    entries = hass.config_entries.async_entries(DOMAIN)
    if len(entries) <= 1:
        if hass.services.has_service(DOMAIN, SERVICE_ADD_BILL):
            hass.services.async_remove(DOMAIN, SERVICE_ADD_BILL)
        if hass.services.has_service(DOMAIN, SERVICE_REMOVE_BILL):
            hass.services.async_remove(DOMAIN, SERVICE_REMOVE_BILL)
        if hass.services.has_service(DOMAIN, SERVICE_RESET_CYCLE):
            hass.services.async_remove(DOMAIN, SERVICE_RESET_CYCLE)
        if hass.services.has_service(DOMAIN, SERVICE_SET_BASELINE):
            hass.services.async_remove(DOMAIN, SERVICE_SET_BASELINE)
        if hass.services.has_service(DOMAIN, SERVICE_GET_SUMMARY):
            hass.services.async_remove(DOMAIN, SERVICE_GET_SUMMARY)

        try:
            from homeassistant.components.frontend import async_remove_panel

            async_remove_panel(hass, "electricity")
            if DOMAIN in hass.data:
                hass.data[DOMAIN]["panel_registered"] = False
        except Exception as err:
            _LOGGER.warning("Could not remove electricity panel: %s", err)

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
            period_start=call.data.get(ATTR_PERIOD_START),
            energy_charge=call.data.get(ATTR_ENERGY_CHARGE),
            ft_charge=call.data.get(ATTR_FT_CHARGE),
            service_charge=call.data.get(ATTR_SERVICE_CHARGE),
            vat=call.data.get(ATTR_VAT),
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

    async def handle_get_summary(call: ServiceCall) -> ServiceResponse:
        entries: list[ElectricityBillConfigEntry] = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError(
                "No Electricity Bill integration configured.",
                translation_domain=DOMAIN,
                translation_key="no_energy_sources",
            )
        coordinator = entries[0].runtime_data
        payload = coordinator._summary_payload(call.data.get("kind", "daily"))
        if payload is None:
            return {"kind": call.data.get("kind", "daily"), "message": None}
        return payload

    async def handle_set_baseline(call: ServiceCall) -> None:
        entries: list[ElectricityBillConfigEntry] = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError(
                "No Electricity Bill integration configured.",
                translation_domain=DOMAIN,
                translation_key="no_energy_sources",
            )
        coordinator = entries[0].runtime_data
        await coordinator.async_set_baseline(call.data["entity_id"], call.data["value"])

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
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BASELINE,
        handle_set_baseline,
        schema=SET_BASELINE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SUMMARY,
        handle_get_summary,
        schema=vol.Schema({vol.Optional("kind", default="daily"): vol.In(SUMMARY_KINDS)}),
        supports_response=SupportsResponse.ONLY,
    )
