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
        key="last_bill_amount",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_THB,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("last_bill_amount"),
        attr_fn=lambda data: (
            {
                "period_start": (data.get("last_bill") or {}).get("period_start"),
                "period_end": (data.get("last_bill") or {}).get("period_end"),
                "kwh": (data.get("last_bill") or {}).get("kwh"),
                "rate": (data.get("last_bill") or {}).get("rate"),
                "note": (data.get("last_bill") or {}).get("note", ""),
            }
            if data.get("last_bill")
            else {
                "period_start": None,
                "period_end": None,
                "kwh": None,
                "rate": None,
                "note": "",
            }
        ),
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
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if self.entity_description.attr_fn is not None:
            return self.entity_description.attr_fn(self.coordinator.data)
        return {}
