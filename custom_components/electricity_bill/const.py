"""Constants for the Electricity Bill integration."""
from __future__ import annotations

DOMAIN = "electricity_bill"

# Configuration options
CONF_NAME = "name"
CONF_SOURCES = "sources"
CONF_FALLBACK_RATE = "fallback_rate"
CONF_AI_TASK_ENTITY = "ai_task_entity"
CONF_MAIN_METER = "main_meter"
CONF_RESET_BUTTON = "reset_button"
CONF_FT_RATE = "ft_rate"
CONF_SERVICE_CHARGE = "service_charge"
CONF_VAT_PERCENT = "vat_percent"
CONF_CUTOFF_DAY_30 = "cutoff_day_30"
CONF_CUTOFF_DAY_31 = "cutoff_day_31"
CONF_CUTOFF_DAY_FEB = "cutoff_day_feb"
CONF_BUDGET_THRESHOLD = "budget_threshold"
CONF_TARIFF_PROFILE = "tariff_profile"
CONF_HIGH_USAGE_FACTOR = "high_usage_factor"
CONF_SUMMARY_HOUR = "summary_hour"
CONF_WEEKLY_DAY = "weekly_summary_day"
CONF_TARIFF_TIERS = "tariff_tiers"

# Tariff profiles. "none" (default) keeps the generic behaviour: estimates use the
# effective rate of the last bill. "thailand_residential" uses the Thai PEA/MEA
# residential tiers below. "custom" uses CONF_TARIFF_TIERS.
PROFILE_NONE = "none"
PROFILE_THAILAND = "thailand_residential"
PROFILE_CUSTOM = "custom"
TARIFF_PROFILES = [PROFILE_NONE, PROFILE_THAILAND, PROFILE_CUSTOM]
DEFAULT_TARIFF_PROFILE = PROFILE_NONE

# Thai residential tariff (PEA/MEA) in force from the September 2026 bill.
# Each tier is (cumulative upper limit in kWh or None for "and above", baht per kWh).
TARIFF_TIERS_OVER_150 = ((200, 3.0), (400, 4.1584), (None, 4.3583))
TARIFF_TIERS_UP_TO_150 = (
    (15, 2.3488),
    (25, 2.9882),
    (200, 3.0),
    (400, 4.1584),
    (None, 4.3583),
)
TARIFF_SMALL_USER_LIMIT_KWH = 150

# Defaults of the Thailand profile only (other profiles start at 0 / not set)
THAILAND_FT_RATE = 0.1623
THAILAND_SERVICE_CHARGE = 24.62
THAILAND_VAT_PERCENT = 7.0
THAILAND_CUTOFF_DAY_30 = 24
THAILAND_CUTOFF_DAY_31 = 25
THAILAND_CUTOFF_DAY_FEB = 24

# Events fired on the HA bus (build automations / notifications on them)
EVENT_CUTOFF_DAY = "electricity_bill_cutoff_day"
EVENT_BUDGET_EXCEEDED = "electricity_bill_budget_exceeded"
EVENT_HIGH_USAGE = "electricity_bill_high_usage"
HIGH_USAGE_MIN_KWH = 2.0
DAY_RECORD_VERSION = 2
EVENT_DAILY_SUMMARY = "electricity_bill_daily_summary"
EVENT_WEEKLY_SUMMARY = "electricity_bill_weekly_summary"
DEFAULT_SUMMARY_HOUR = 21
DEFAULT_WEEKLY_DAY = 6  # 0 = Monday ... 6 = Sunday
HISTORY_MAX_DAYS = 70

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
