"""Sensor platform for Electricity Bill integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ElectricityBillConfigEntry, ElectricityBillCoordinator

CURRENCY_THB = "THB"


def _last_bill_amount_attrs(data: dict[str, Any]) -> dict[str, Any]:
    """Return attributes for last_bill_amount sensor."""
    history = data.get("bill_history") or []
    latest = history[0] if history else None
    last_b = data.get("last_bill")

    if not latest and not last_b:
        return {
            "period_start": None,
            "period_end": None,
            "kwh": None,
            "rate": None,
            "days": None,
            "kwh_per_day": None,
            "baht_per_day": None,
            "amount_change_pct": None,
            "energy_charge": None,
            "ft_charge": None,
            "service_charge": None,
            "vat": None,
            "note": "",
        }

    return {
        "period_start": latest.get("period_start") if latest else (last_b or {}).get("period_start"),
        "period_end": latest.get("period_end") if latest else (last_b or {}).get("period_end"),
        "kwh": latest.get("kwh") if latest else (last_b or {}).get("kwh"),
        "rate": latest.get("rate") if latest else (last_b or {}).get("rate"),
        "days": latest.get("days") if latest else None,
        "kwh_per_day": latest.get("kwh_per_day") if latest else None,
        "baht_per_day": latest.get("baht_per_day") if latest else None,
        "amount_change_pct": latest.get("amount_change_pct") if latest else None,
        "energy_charge": latest.get("energy_charge") if latest else (last_b or {}).get("energy_charge"),
        "ft_charge": latest.get("ft_charge") if latest else (last_b or {}).get("ft_charge"),
        "service_charge": latest.get("service_charge") if latest else (last_b or {}).get("service_charge"),
        "vat": latest.get("vat") if latest else (last_b or {}).get("vat"),
        "note": latest.get("note", "") if latest else str((last_b or {}).get("note", "")),
    }


@dataclass(frozen=True, kw_only=True)
class ElectricityBillSensorEntityDescription(SensorEntityDescription):
    """Describes an Electricity Bill sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSOR_DESCRIPTIONS: tuple[ElectricityBillSensorEntityDescription, ...] = (
    ElectricityBillSensorEntityDescription(
        key="cycle_kwh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("cycle_kwh", 0.0),
        attr_fn=lambda data: {
            "per_source": data.get("per_source", {}),
            "cycle_start": data.get("cycle_start"),
            "days_in_cycle": data.get("days_in_cycle", 0),
        },
    ),
    ElectricityBillSensorEntityDescription(
        key="cycle_unmetered_kwh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("cycle_unmetered_kwh"),
        attr_fn=lambda data: {
            "main_meter": data.get("main_meter"),
            "submetered_kwh": data.get("cycle_submetered_kwh"),
        },
    ),
    ElectricityBillSensorEntityDescription(
        key="effective_rate",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=f"{CURRENCY_THB}/kWh",
        suggested_display_precision=4,
        value_fn=lambda data: data.get("effective_rate"),
        attr_fn=lambda data: {
            "source": data.get("rate_source", "fallback"),
            "based_on_period_end": data.get("based_on_period_end"),
        },
    ),
    ElectricityBillSensorEntityDescription(
        key="cycle_cost_estimate",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_THB,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("cycle_cost_estimate", 0.0),
        attr_fn=lambda data: {
            "rate_used": data.get("effective_rate"),
        },
    ),
    ElectricityBillSensorEntityDescription(
        key="today_kwh",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("today_kwh"),
    ),
    ElectricityBillSensorEntityDescription(
        key="yesterday_kwh",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("yesterday_kwh"),
    ),
    ElectricityBillSensorEntityDescription(
        key="daily_average_kwh",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("daily_average_kwh"),
    ),
    ElectricityBillSensorEntityDescription(
        key="cycle_bill_estimate",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_THB,
        suggested_display_precision=2,
        value_fn=lambda data: (data.get("cycle_bill_estimate") or {}).get("total"),
        attr_fn=lambda data: dict(data.get("cycle_bill_estimate") or {}),
    ),
    ElectricityBillSensorEntityDescription(
        key="forecast_bill",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_THB,
        suggested_display_precision=2,
        value_fn=lambda data: ((data.get("forecast") or {}).get("bill") or {}).get("total"),
        attr_fn=lambda data: {
            "forecast_kwh": (data.get("forecast") or {}).get("kwh"),
            "kwh_per_day": (data.get("forecast") or {}).get("kwh_per_day"),
            "cycle_days": (data.get("forecast") or {}).get("days"),
            "cutoff_date": data["next_cutoff"].isoformat() if data.get("next_cutoff") else None,
        },
    ),
    ElectricityBillSensorEntityDescription(
        key="next_cutoff_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda data: data.get("next_cutoff"),
    ),
    ElectricityBillSensorEntityDescription(
        key="last_bill_amount",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_THB,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("last_bill_amount"),
        attr_fn=_last_bill_amount_attrs,
    ),
    ElectricityBillSensorEntityDescription(
        key="last_bill_kwh",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("last_bill_kwh"),
        attr_fn=lambda data: {
            "period_end": (data.get("last_bill") or {}).get("period_end"),
        },
    ),
    ElectricityBillSensorEntityDescription(
        key="last_bill_unmetered_kwh",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("last_bill_unmetered_kwh"),
        attr_fn=lambda data: {
            "measured_kwh": data.get("last_bill_measured_kwh"),
            "share_metered_percent": data.get("share_metered_percent"),
        },
    ),
    ElectricityBillSensorEntityDescription(
        key="bill_history",
        value_fn=lambda data: data.get("bill_count", 0),
        attr_fn=lambda data: {
            "bills": data.get("bill_history", []),
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectricityBillConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Electricity Bill sensor entities based on a config entry."""
    coordinator = entry.runtime_data
    entities = [
        ElectricityBillSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
        if description.key != "cycle_unmetered_kwh" or coordinator.main_meter
    ]
    async_add_entities(entities)


class ElectricityBillSensor(CoordinatorEntity[ElectricityBillCoordinator], SensorEntity):
    """Representation of an Electricity Bill sensor."""

    entity_description: ElectricityBillSensorEntityDescription

    def __init__(
        self,
        coordinator: ElectricityBillCoordinator,
        description: ElectricityBillSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_translation_key = description.key
        self._attr_device_info = coordinator.device_info

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Monetary sensors follow the currency configured in Home Assistant."""
        unit = self.entity_description.native_unit_of_measurement
        if self.entity_description.device_class == SensorDeviceClass.MONETARY and unit:
            currency = getattr(self.hass.config, "currency", None) or CURRENCY_THB
            return f"{currency}/kWh" if str(unit).endswith("/kWh") else currency
        return unit

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if self.entity_description.attr_fn is not None:
            return self.entity_description.attr_fn(self.coordinator.data)
        return {}
