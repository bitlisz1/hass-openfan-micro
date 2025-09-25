"""Low-level HTTP API client for OpenFAN Micro.

Handles:
- JSON parsing & logging
- Firmware compatibility (new/legacy endpoints)
- Status payload shape differences (top-level vs nested under 'data')
"""
from __future__ import annotations
from typing import Any, Tuple, Optional

import logging
import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)


class OpenFanApi:
    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        self._host = host
        self._session = session

    async def _get_json(self, path: str) -> dict:
        """HTTP GET -> JSON dict (logs raw on error)."""
        url = f"http://{self._host}{path}"
        async with async_timeout.timeout(5):
            async with self._session.get(url) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    _LOGGER.error(
                        "OpenFAN Micro %s HTTP %s on %s: %s",
                        self._host, resp.status, path, text
                    )
                    resp.raise_for_status()
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    _LOGGER.error(
                        "OpenFAN Micro %s non-JSON on %s: %s",
                        self._host, path, text
                    )
                    raise
        if not isinstance(data, dict):
            data = {}
        _LOGGER.debug("OpenFAN Micro %s GET %s -> %s", self._host, path, data)
        return data

    def _parse_status_payload(self, data: dict) -> Tuple[int, int]:
        """Accept both top-level and nested ('data') formats. Returns (rpm, pwm%)."""
        container: dict = data or {}
        if not ("rpm" in container or "pwm_percent" in container):
            container = data.get("data", {}) or {}

        rpm_raw = container.get("rpm", 0)
        pwm_raw = container.get("pwm_percent", container.get("pwm", container.get("pwm_value", 0)))

        try:
            rpm = int(float(rpm_raw))
        except Exception:
            rpm = 0
        try:
            pwm = int(float(pwm_raw))
        except Exception:
            pwm = 0

        rpm = max(0, rpm)
        pwm = max(0, min(100, pwm))
        return rpm, pwm

    async def set_pwm(self, value: int) -> dict[str, Any]:
        """Set PWM 0..100; tries new (fan/0/set) and old (fan/set) endpoints."""
        value = max(0, min(100, int(value)))
        paths = [
            f"/api/v0/fan/0/set?value={value}",  # new FW (107c190)
            f"/api/v0/fan/set?value={value}",    # legacy fallback
        ]
        last_exc: Optional[Exception] = None
        for p in paths:
            try:
                data = await self._get_json(p)
                status = str(data.get("status", "")).lower()
                if status not in ("ok", "success", ""):
                    msg = data.get("message", "unknown error")
                    raise RuntimeError(f"API status != ok for {p}: {msg}")
                return data
            except Exception as exc:
                last_exc = exc
                _LOGGER.debug("OpenFAN Micro %s: set_pwm via %s failed: %r", self._host, p, exc)
                continue
        assert last_exc is not None
        raise last_exc

    async def get_status(self) -> Tuple[int, int]:
        """Return (rpm, pwm_percent). Accepts top-level and nested formats."""
        paths = [
            "/api/v0/fan/status",    # documented Micro endpoint
            "/api/v0/fan/0/status",  # defensive fallback
        ]
        last_exc: Optional[Exception] = None
        for p in paths:
            try:
                data = await self._get_json(p)
                status = str(data.get("status", "ok")).lower()
                if status not in ("ok", "success"):
                    msg = data.get("message", "unknown error")
                    raise RuntimeError(f"API status != ok for {p}: {msg}")

                rpm, pwm = self._parse_status_payload(data)
                _LOGGER.debug("OpenFAN Micro %s parsed status -> rpm=%s pwm=%s", self._host, rpm, pwm)
                return rpm, pwm
            except Exception as exc:
                last_exc = exc
                _LOGGER.debug("OpenFAN Micro %s: get_status via %s failed: %r", self._host, p, exc)
                continue
        assert last_exc is not None
        raise last_exc
