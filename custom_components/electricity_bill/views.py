"""HTTP API view for electricity bill scanning."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import uuid

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .calc import validate_extraction
from .const import CONF_AI_TASK_ENTITY, DOMAIN
from .scan import ScanError, async_scan_image, pick_ai_task_entity

_LOGGER = logging.getLogger(__name__)

MAX_FILE_SIZE = 8 * 1024 * 1024  # 8 MiB


def detect_image_format(data: bytes) -> tuple[str, str] | None:
    """Validate image magic bytes and return (extension, mime_type) or None."""
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "jpg", "image/jpeg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png", "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


class ScanView(HomeAssistantView):
    """View to handle electricity bill photo uploads and AI scan."""

    url = "/api/electricity_bill/scan"
    name = "api:electricity_bill:scan"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Handle image upload, invoke AI task, and return validated extraction."""
        hass: HomeAssistant = request.app["hass"]

        if not request.content_type.startswith("multipart/"):
            return self.json({"ok": False, "error": "invalid_content_type"}, status_code=400)

        reader = await request.multipart()
        file_bytes = bytearray()
        found_file = False

        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == "file":
                found_file = True
                while True:
                    chunk = await part.read_chunk()
                    if not chunk:
                        break
                    file_bytes.extend(chunk)
                    if len(file_bytes) > MAX_FILE_SIZE:
                        return self.json({"ok": False, "error": "file_too_large"}, status_code=413)
                break

        if not found_file or not file_bytes:
            return self.json({"ok": False, "error": "missing_file"}, status_code=400)

        img_format = detect_image_format(bytes(file_bytes[:16]))
        if img_format is None:
            return self.json({"ok": False, "error": "unsupported_media_type"}, status_code=415)

        ext, mime = img_format

        # Pick ai_task entity
        entries = hass.config_entries.async_entries(DOMAIN)
        configured_ai_task = None
        if entries:
            configured_ai_task = entries[0].options.get(
                CONF_AI_TASK_ENTITY,
                entries[0].data.get(CONF_AI_TASK_ENTITY),
            )

        ai_task_entity = pick_ai_task_entity(hass, configured_ai_task)
        if not ai_task_entity:
            return self.json({"ok": False, "error": "no_ai_task"}, status_code=200)

        # Determine media storage directory
        media_dirs = getattr(hass.config, "media_dirs", None) or {}
        if "local" in media_dirs:
            media_dir_key = "local"
            base_dir = media_dirs["local"]
        elif media_dirs:
            media_dir_key = next(iter(media_dirs.keys()))
            base_dir = media_dirs[media_dir_key]
        else:
            media_dir_key = "local"
            base_dir = "/media"

        subfolder = "electricity_bill_scans"
        filename = f"{uuid.uuid4().hex}.{ext}"
        target_dir = Path(base_dir) / subfolder
        target_path = target_dir / filename
        media_content_id = f"media-source://media_source/{media_dir_key}/{subfolder}/{filename}"

        def _write_temp_file() -> None:
            target_dir.mkdir(parents=True, exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(file_bytes)

        def _delete_temp_file() -> None:
            try:
                if target_path.exists():
                    target_path.unlink()
            except OSError as err:
                _LOGGER.warning("Failed to remove temporary scan file %s: %s", target_path, err)

        try:
            await hass.async_add_executor_job(_write_temp_file)
            raw_data = await async_scan_image(hass, ai_task_entity, media_content_id, mime)
            validated = validate_extraction(raw_data, today=dt_util.now().date())
            return self.json({"ok": True, "result": validated}, status_code=200)
        except ScanError as err:
            return self.json({"ok": False, "error": err.code}, status_code=200)
        except Exception as err:
            _LOGGER.exception("Unexpected error during bill scan: %s", err)
            return self.json({"ok": False, "error": "scan_failed"}, status_code=200)
        finally:
            await hass.async_add_executor_job(_delete_temp_file)
