"""AI scan service and prompt definition for electricity bills."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

PROMPT = (
    "Extract data from this Thai electricity bill (MEA / PEA):\n"
    "1. period_start: The start date of the billing period as ISO YYYY-MM-DD in Gregorian calendar. "
    "If the bill uses Buddhist Era (BE year > 2400), subtract 543 to convert to Gregorian (e.g., 2567 -> 2024, 2568 -> 2025, 2569 -> 2026).\n"
    "2. period_end: The end date of the billing period or the date of the latest meter reading, "
    "formatted as ISO YYYY-MM-DD in the Gregorian calendar. If BE year > 2400, subtract 543.\n"
    "3. kwh: Total units consumed this billing period in kWh (หน่วยที่ใช้ / จำนวนหน่วย).\n"
    "4. amount: Total amount to pay this month in THB including VAT (รวมเงินค่าไฟฟ้า / ยอดที่ต้องชำระเดือนนี้). "
    "Do NOT include arrears, unpaid prior balances, or cumulative balances.\n"
    "5. energy_charge: Base electricity / energy charge in THB (ค่าไฟฟ้าฐาน / ค่าพลังงานไฟฟ้า).\n"
    "6. ft_charge: Fuel adjustment charge (Ft) in THB (ค่าไฟฟ้าผันแปร / ค่า Ft, may be negative).\n"
    "7. service_charge: Monthly service charge in THB (ค่าบริการรายเดือน).\n"
    "8. vat: 7% VAT in THB (ภาษีมูลค่าเพิ่ม 7%).\n"
    "9. confidence: Assessment of extraction confidence: 'low', 'medium', or 'high'.\n"
    "10. notes: Short explanation or notes if anything is ambiguous or blurry.\n\n"
    "Use null for any field that is not clearly readable. Never guess or hallucinate values."
)

STRUCTURE: dict[str, Any] = {
    "period_start": {
        "description": "Start date of billing period as YYYY-MM-DD (Gregorian)",
        "required": False,
        "selector": {"text": None},
    },
    "period_end": {
        "description": "End date of billing period or meter reading date as YYYY-MM-DD (Gregorian)",
        "required": False,
        "selector": {"text": None},
    },
    "kwh": {
        "description": "Total units consumed this period in kWh (หน่วยที่ใช้)",
        "required": False,
        "selector": {"number": {"min": 0, "max": 100000, "step": "any"}},
    },
    "amount": {
        "description": "Total amount to pay this month in THB including VAT (รวมเงินค่าไฟฟ้า / ยอดที่ต้องชำระเดือนนี้)",
        "required": False,
        "selector": {"number": {"min": 0, "max": 100000, "step": "any"}},
    },
    "energy_charge": {
        "description": "Base energy charge in THB (ค่าไฟฟ้าฐาน / ค่าพลังงานไฟฟ้า)",
        "required": False,
        "selector": {"number": {"min": 0, "max": 100000, "step": "any"}},
    },
    "ft_charge": {
        "description": "Fuel adjustment charge (Ft) in THB, may be negative (ค่าไฟฟ้าผันแปร / ค่า Ft)",
        "required": False,
        "selector": {"number": {"min": -100000, "max": 100000, "step": "any"}},
    },
    "service_charge": {
        "description": "Monthly service charge in THB (ค่าบริการรายเดือน)",
        "required": False,
        "selector": {"number": {"min": 0, "max": 100000, "step": "any"}},
    },
    "vat": {
        "description": "7% VAT in THB (ภาษีมูลค่าเพิ่ม 7%)",
        "required": False,
        "selector": {"number": {"min": 0, "max": 100000, "step": "any"}},
    },
    "confidence": {
        "description": "Extraction confidence level: low, medium, or high",
        "required": False,
        "selector": {"text": None},
    },
    "notes": {
        "description": "Short remarks or reason if values could not be read clearly",
        "required": False,
        "selector": {"text": None},
    },
}


class ScanError(HomeAssistantError):
    """Exception raised when bill scanning fails."""

    def __init__(self, translation_key: str) -> None:
        """Initialize scan error with translation key / error code."""
        super().__init__(translation_key)
        self.translation_key = translation_key
        self.code = translation_key


def pick_ai_task_entity(hass: HomeAssistant, configured: str | None) -> str | None:
    """Return the configured ai_task entity if valid, else the first ai_task entity in states, else None."""
    if configured and hass.states.get(configured) is not None:
        return configured

    ai_tasks = hass.states.async_entity_ids("ai_task")
    if ai_tasks:
        return ai_tasks[0]

    return None


async def async_scan_image(
    hass: HomeAssistant,
    entity_id: str,
    media_content_id: str,
    media_content_type: str,
) -> dict[str, Any]:
    """Call ai_task generate_data service to extract bill fields from image."""
    try:
        response = await hass.services.async_call(
            "ai_task",
            "generate_data",
            {
                "task_name": "Electricity bill scan",
                "entity_id": entity_id,
                "instructions": PROMPT,
                "structure": STRUCTURE,
                "attachments": [
                    {
                        "media_content_id": media_content_id,
                        "media_content_type": media_content_type,
                    }
                ],
            },
            blocking=True,
            return_response=True,
        )
    except Exception as err:
        _LOGGER.warning("ai_task generate_data call failed: %s", err)
        raise ScanError("ai_task_failed") from err

    if not response or not isinstance(response, dict) or "data" not in response:
        _LOGGER.warning("ai_task returned unexpected response format")
        raise ScanError("invalid_ai_response")

    data = response["data"]
    if not isinstance(data, dict):
        _LOGGER.warning("ai_task returned non-dict response data")
        raise ScanError("invalid_ai_response")

    _LOGGER.debug("ai_task scan result: %s", str(data)[:200])
    return data
