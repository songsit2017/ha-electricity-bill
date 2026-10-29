"""Fixtures for the Home Assistant based tests."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Let Home Assistant load custom_components/electricity_bill.

    The integration depends on the recorder, which must be set up before the hass fixture.
    """
    yield
