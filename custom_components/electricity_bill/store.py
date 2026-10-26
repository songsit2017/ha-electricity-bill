"""Thin storage wrapper over Home Assistant Store for Electricity Bill."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class ElectricityBillStore:
    """Thin wrapper over Home Assistant Store (version 1)."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the storage helper."""
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_{entry_id}",
        )
        self._data: dict[str, Any] | None = None

    async def async_load(self) -> dict[str, Any]:
        """Load stored electricity bill data.

        Returns a dictionary with 'bills' and 'cycle_snapshot'.
        """
        if self._data is None:
            data = await self._store.async_load()
            if not data or not isinstance(data, dict):
                data = {
                    "bills": [],
                    "cycle_snapshot": {},
                }
            else:
                data.setdefault("bills", [])
                data.setdefault("cycle_snapshot", {})
            self._data = data
        return self._data

    async def async_save(self, data: dict[str, Any]) -> None:
        """Save electricity bill data to storage."""
        # keep extra keys (e.g. "budget_notified") that callers of async_save do not pass
        merged = {k: v for k, v in (self._data or {}).items() if k not in data}
        merged.update(data)
        self._data = merged
        await self._store.async_save(merged)

    async def async_set_extra(self, key: str, value: Any) -> None:
        """Persist one extra key next to bills and cycle_snapshot."""
        data = dict(await self.async_load())
        data[key] = value
        self._data = data
        await self._store.async_save(data)
