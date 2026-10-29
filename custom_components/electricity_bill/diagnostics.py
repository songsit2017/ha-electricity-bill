"""Diagnostics for Electricity Bill (Settings -> Devices & services -> Download diagnostics)."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import ElectricityBillConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ElectricityBillConfigEntry
) -> dict[str, Any]:
    """Return configuration and current state; bills keep their numbers but not their notes."""
    coordinator = entry.runtime_data
    data = dict(coordinator.data or {})
    data.pop("bill_history", None)
    data.pop("last_bill", None)
    return {
        "options": dict(entry.options),
        "data_config": {k: v for k, v in entry.data.items() if k != "name"},
        "sources": coordinator.sources,
        "total_sources": coordinator.total_sources,
        "source_states": {
            s: (hass.states.get(s).state if hass.states.get(s) else None) for s in coordinator.sources
        },
        "cycle_snapshot": coordinator.cycle_snapshot,
        "day": coordinator._day,
        "history_days": len(coordinator._history),
        "history_last": coordinator._history[-3:],
        "bills": [
            {k: b.get(k) for k in ("period_start", "period_end", "kwh", "amount", "rate", "measured_kwh", "ft_charge")}
            for b in coordinator.bills
        ],
        "data": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in data.items()},
        "active_issues": sorted(coordinator._active_issues),
    }
