"""Constants for the Electricity Bill integration."""
from __future__ import annotations

DOMAIN = "electricity_bill"

# Configuration options
CONF_NAME = "name"
CONF_SOURCES = "sources"
CONF_FALLBACK_RATE = "fallback_rate"
CONF_AI_TASK_ENTITY = "ai_task_entity"

# Defaults
DEFAULT_NAME = "Electricity Bill"
DEFAULT_FALLBACK_RATE = 4.40
DEFAULT_SOURCES = [
    "sensor.aircon_bedroom_kwh",
    "sensor.aircon_workroom_kwh",
    "sensor.speaker_kwh",
    "sensor.water_pump_kwh",
    "sensor.pc_kwh",
    "sensor.outdoor_light_kwh",
]

# Storage
STORAGE_KEY = "electricity_bill"
STORAGE_VERSION = 1

# Services
SERVICE_ADD_BILL = "add_bill"
SERVICE_REMOVE_BILL = "remove_bill"
SERVICE_RESET_CYCLE = "reset_cycle"
SERVICE_SET_BASELINE = "set_baseline"

# Service Attributes
ATTR_PERIOD_START = "period_start"
ATTR_PERIOD_END = "period_end"
ATTR_KWH = "kwh"
ATTR_AMOUNT = "amount"
ATTR_NOTE = "note"
ATTR_REPLACE = "replace"
ATTR_ID = "id"
ATTR_ENERGY_CHARGE = "energy_charge"
ATTR_FT_CHARGE = "ft_charge"
ATTR_SERVICE_CHARGE = "service_charge"
ATTR_VAT = "vat"
