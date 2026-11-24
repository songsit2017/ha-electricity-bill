"""Local per-meter discovery and abnormal energy usage monitoring."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import math
from statistics import median
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EVENT_DEVICE_HIGH_USAGE

WINDOW = timedelta(minutes=15)
HISTORY_DAYS = 28
MIN_DAYS = 7
MIN_EXCESS_KWH = 0.025
ENERGY_FACTORS = {"Wh": 0.001, "kWh": 1.0, "MWh": 1000.0}
POWER_FACTORS = {"W": 0.001, "kW": 1.0}


@dataclass(frozen=True)
class Meter:
    entity_id: str
    name: str
    kind: str
    factor: float

    def reading(self, hass: HomeAssistant) -> float | None:
        state = hass.states.get(self.entity_id)
        if state is None:
            return None
        try:
            value = float(state.state) * self.factor
        except ValueError:
            return None
        return value if math.isfinite(value) and value >= 0 else None


def usage_threshold(samples: list[float]) -> tuple[float, float] | None:
    """Return the baseline and threshold once enough comparable days exist."""
    if len(samples) < MIN_DAYS:
        return None
    baseline = median(samples)
    deviation = median(abs(sample - baseline) for sample in samples)
    return baseline, baseline + max(3 * 1.4826 * deviation, baseline * 0.5, MIN_EXCESS_KWH)


class DeviceEnergyMonitor:
    """Discover and monitor meters independently of the configured bill sources."""

    def __init__(
        self, hass: HomeAssistant, entry_id: str, sources: list[str], main_meter: str | None
    ) -> None:
        self.hass = hass
        self.sources = set(sources) - {main_meter}
        self.main_meter = main_meter
        self.store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}_device_usage_{entry_id}")
        self.records: dict[str, Any] = {}
        self.muted: set[str] = set()
        self.selected: dict[str, str] = {}
        self.status: dict[str, dict[str, Any]] = {}
        self.previous: dict[str, tuple[Meter, datetime, float]] = {}
        self.streak: dict[str, int] = {}
        self.power_samples: dict[str, dict[int, float]] = {}

    async def async_load(self) -> None:
        data = await self.store.async_load() or {}
        self.records = data.get("records", {})
        self.muted = set(data.get("muted", []))
        self.selected = data.get("selected", {})

    @callback
    def async_save(self) -> None:
        self.store.async_delay_save(
            lambda: {"records": self.records, "muted": sorted(self.muted), "selected": self.selected},
            5,
        )

    @callback
    def async_set_alerts(self, key: str, enabled: bool) -> None:
        if enabled:
            self.muted.discard(key)
        else:
            self.muted.add(key)
        self.status = {**self.status, key: {**self.status[key], "alerts_enabled": enabled}}
        self.streak.pop(key, None)
        self.async_save()

    @callback
    def async_select_meter(self, key: str, entity_id: str) -> None:
        self.selected[key] = entity_id
        self.streak.pop(key, None)
        self.previous.pop(key, None)
        self.power_samples.pop(key, None)
        self.async_save()

    @callback
    def async_sample_power(self, now: datetime) -> None:
        """Sample power in the middle of each minute of the window."""
        minute = int(now.timestamp() // 60)
        for key, (meter, _, _) in self.previous.items():
            if meter.kind != "power":
                continue
            value = meter.reading(self.hass)
            if value is not None:
                self.power_samples.setdefault(key, {})[minute] = value

    @callback
    def async_sample(self, now: datetime, rate: float | None) -> None:
        """Sample aligned windows. Missing intervals never produce usage."""
        now = dt_util.as_local(now)
        groups = self._discover()
        status = {}
        previous = {}
        for key, meters in groups.items():
            selection = self.selected.get(key)
            meter = (
                next((item for item in meters if item.entity_id == selection), None)
                if selection else self._select(meters)
            )
            candidates = sorted(item.entity_id for item in meters)
            if meter is None:
                self.streak.pop(key, None)
                status[key] = {
                    "name": meters[0].name,
                    "state": "ambiguous",
                    "candidates": candidates,
                }
                continue

            value = meter.reading(self.hass)
            record = self.records.get(key)
            signature = [meter.entity_id, meter.kind, meter.factor]
            if record is None or record["meter"] != signature:
                record = self.records[key] = {
                    "meter": signature,
                    "windows": {},
                    "last_alert": record.get("last_alert") if record else None,
                }
                self.streak.pop(key, None)
            prior = self.previous.get(key)
            state = "learning" if value is not None else "unavailable"
            if value is not None:
                previous[key] = (meter, now, value)
            if (
                value is not None and prior and prior[0] == meter
                and abs((now.timestamp() - prior[1].timestamp()) - WINDOW.total_seconds()) < 60
            ):
                if meter.kind == "power":
                    samples = self.power_samples.get(key, {})
                    end_minute = int(now.timestamp() // 60)
                    values = [samples[index] for index in range(end_minute - 15, end_minute) if index in samples]
                    usage = sum(values) / 60 if len(values) == 15 else None
                else:
                    usage = value - prior[2]
                if usage is not None and usage >= 0 and math.isfinite(usage):
                    state = self._record_window(key, meter, record, prior[1], usage, rate)
                else:
                    self.streak.pop(key, None)
            else:
                self.streak.pop(key, None)

            status[key] = {
                "name": meter.name,
                "entity_id": meter.entity_id,
                "candidates": candidates,
                "state": state,
                "estimated": meter.kind == "power",
                "alerts_enabled": key not in self.muted,
            }

        cutoff = (now.date() - timedelta(days=HISTORY_DAYS)).isoformat()
        for key, record in list(self.records.items()):
            record["windows"] = {
                day: windows for day, windows in record["windows"].items() if day >= cutoff
            }
            if key not in groups and not record["windows"]:
                del self.records[key]
                self.streak.pop(key, None)
        self.status = status
        self.previous = previous
        self.power_samples.clear()
        self.async_save()

    def _discover(self) -> dict[str, list[Meter]]:
        registry = er.async_get(self.hass)
        main = registry.async_get(self.main_meter) if self.main_meter else None
        main_device = main.device_id if main else None
        groups: dict[str, list[Meter]] = {}
        for state in self.hass.states.async_all("sensor"):
            entity_id = state.entity_id
            if entity_id == self.main_meter:
                continue
            entry = registry.async_get(entity_id)
            if entry is not None and (entry.disabled or entry.platform == DOMAIN):
                continue
            device_id = entry.device_id if entry else None
            if entity_id not in self.sources and (
                not device_id or entry.platform in {"utility_meter", "integration", "template"}
            ):
                continue
            attrs = state.attributes
            kind = attrs.get("device_class")
            unit = attrs.get("unit_of_measurement")
            state_class = attrs.get("state_class")
            if kind == "energy" and unit in ENERGY_FACTORS and (
                state_class == "total_increasing"
                or (entity_id in self.sources and state_class == "total")
            ):
                factor = ENERGY_FACTORS[unit]
            elif kind == "power" and unit in POWER_FACTORS and state_class == "measurement":
                factor = POWER_FACTORS[unit]
            else:
                continue
            # Associate a configured Integral helper with its physical source.
            if not device_id and entry and entry.platform == "integration" and entry.config_entry_id:
                config = self.hass.config_entries.async_get_entry(entry.config_entry_id)
                if config:
                    source = config.options.get("source") or config.data.get("source")
                    upstream = registry.async_get(source) if isinstance(source, str) else None
                    if upstream:
                        device_id = upstream.device_id
            if main_device and device_id == main_device:
                continue
            key = device_id or entity_id
            groups.setdefault(key, []).append(Meter(entity_id, state.name, kind, factor))
        return groups

    def _select(self, meters: list[Meter]) -> Meter | None:
        preferred = [meter for meter in meters if meter.entity_id in self.sources]
        if preferred:
            return preferred[0] if len(preferred) == 1 else None
        energy = [meter for meter in meters if meter.kind == "energy"]
        power = [meter for meter in meters if meter.kind == "power"]
        if len(energy) > 1 or len(power) > 1:
            return None
        if energy and (not power or (energy[0].reading(self.hass) or 0) > 0):
            return energy[0]
        return power[0] if power else None

    def _record_window(
        self, key: str, meter: Meter, record: dict[str, Any], start: datetime,
        usage: float, rate: float | None,
    ) -> str:
        day = start.date().isoformat()
        slot = f"{start.hour:02}:{start.minute // 15}"
        oldest = (start.date() - timedelta(days=HISTORY_DAYS)).isoformat()
        windows = record["windows"]
        samples = [slots[slot] for date, slots in windows.items() if oldest <= date < day and slot in slots]
        threshold = usage_threshold(samples)
        windows.setdefault(day, {})[slot] = round(usage, 5)
        if threshold is None:
            self.streak.pop(key, None)
            return "learning"
        baseline, limit = threshold
        if usage <= limit or key in self.muted:
            self.streak.pop(key, None)
            return "monitoring"
        self.streak[key] = self.streak.get(key, 0) + 1
        # Limit to one alert per local day, including across HA restarts.
        if self.streak[key] == 2 and record.get("last_alert") != day:
            record["last_alert"] = day
            extra_cost = round((usage - baseline) * rate, 2) if rate is not None else None
            self.hass.bus.async_fire(EVENT_DEVICE_HIGH_USAGE, {
                "entity_id": meter.entity_id,
                "device_name": meter.name,
                "window_start": start.isoformat(),
                "window_minutes": 15,
                "kwh": round(usage, 3),
                "baseline_kwh": round(baseline, 3),
                "excess_cost": extra_cost,
                "estimated": meter.kind == "power",
            })
            if self.hass.services.has_service("persistent_notification", "create"):
                self.hass.async_create_task(self.hass.services.async_call(
                    "persistent_notification", "create", {
                        "notification_id": f"{DOMAIN}_high_usage_{key}",
                        "title": f"{meter.name}: high electricity usage",
                        "message": (
                            f"Last 15 min: {usage:.3f} kWh (typical: {baseline:.3f} kWh)."
                            + (f" Estimated extra cost: {extra_cost:.2f}." if extra_cost is not None else "")
                            + (" Energy estimated from power readings." if meter.kind == "power" else "")
                        ),
                    },
                ))
        return "high_usage"
