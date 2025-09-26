"""Setup & services for OpenFAN Micro (Pro Pack with temp control & smoothing)."""
from __future__ import annotations

import logging
import asyncio
import time
from typing import Any, Tuple, Optional
from collections import deque
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from ._device import Device
from .options_flow import OptionsFlowHandler

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create device runtime, forward platforms, wire temperature controller & services."""
    host = entry.data.get("host")
    name = entry.data.get("name")
    mac = entry.data.get("mac")
    if not host:
        _LOGGER.error("%s: missing 'host' in config entry", DOMAIN)
        return False

    dev = Device(hass, host, name, mac=mac)

    # Apply options to API/coordinator tunables
    opts = entry.options or {}
    dev.api._poll_interval = int(opts.get("poll_interval", 5))
    dev.api._min_pwm = int(opts.get("min_pwm", 0))
    dev.api._failure_threshold = int(opts.get("failure_threshold", 3))
    dev.api._stall_consecutive = int(opts.get("stall_consecutive", 3))

    await dev.async_first_refresh()
    entry.runtime_data = dev

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # --- Temperature controller wiring (piecewise-linear + smoothing) ---
    initial_temp_entity = (opts.get("temp_entity") or "").strip()
    temp_curve_default = (opts.get("temp_curve") or "").strip()
    integrate_s = int(opts.get("temp_integrate_seconds", 30))
    min_interval_s = int(opts.get("temp_update_min_interval", 10))
    deadband = int(opts.get("temp_deadband_pct", 3))

    # Expose controller state for fan extra attributes and diagnostics
    dev.ctrl_state = {
        "active": False,
        "temp_entity": initial_temp_entity,
        "temp_curve": temp_curve_default,
        "temp_integrate_seconds": integrate_s,
        "temp_update_min_interval": min_interval_s,
        "temp_deadband_pct": deadband,
        "temp_avg": None,
        "last_target_pwm": None,
        "last_applied_pwm": None,
        "last_apply_ts": 0.0,
        "min_pwm": dev.api._min_pwm,
        "min_pwm_calibrated": bool(opts.get("min_pwm_calibrated", False)),
    }

    # Temperature sample buffer: (monotonic_ts, value)
    temp_buf: deque[tuple[float, float]] = deque(maxlen=512)

    # Runtime subscription state for temp entity; we may rebind via service
    current_temp_entity: str = initial_temp_entity
    unsub_temp = None  # callback to unsubscribe

    def parse_curve(txt: str):
        pts = []
        for part in [p.strip() for p in txt.split(",") if p.strip()]:
            if "=" in part:
                t, pct = part.split("=", 1)
                try:
                    pts.append((float(t.strip()), max(0, min(100, int(pct.strip())))))
                except Exception:
                    continue
        pts.sort(key=lambda x: x[0])
        return pts

    def averaged_temp(now: float) -> Optional[float]:
        """Return avg temp over integration window; prune old samples."""
        cutoff = now - max(5, int(entry.options.get("temp_integrate_seconds", integrate_s)))
        while temp_buf and temp_buf[0][0] < cutoff:
            temp_buf.popleft()
        if not temp_buf:
            return None
        return sum(val for _, val in temp_buf) / len(temp_buf)

    async def apply_from_temp(trigger: str):
        """Compute target PWM from temperature and apply with deadband/min-interval, clamped by min PWM."""
        # Gate: calibration + config present
        min_pwm = int(entry.options.get("min_pwm", 0))
        min_cal_ok = bool(entry.options.get("min_pwm_calibrated", False)) and min_pwm > 0
        te = (entry.options.get("temp_entity") or "").strip()
        pts = parse_curve(entry.options.get("temp_curve", temp_curve_default))
        dev.ctrl_state.update(
            {
                "min_pwm": min_pwm,
                "min_pwm_calibrated": bool(entry.options.get("min_pwm_calibrated", False)),
                "temp_entity": te,
                "temp_curve": entry.options.get("temp_curve", temp_curve_default),
                "temp_integrate_seconds": int(entry.options.get("temp_integrate_seconds", integrate_s)),
                "temp_update_min_interval": int(entry.options.get("temp_update_min_interval", min_interval_s)),
                "temp_deadband_pct": int(entry.options.get("temp_deadband_pct", deadband)),
            }
        )
        if not (min_cal_ok and te and pts):
            dev.ctrl_state["active"] = False
            _LOGGER.debug(
                "OpenFAN %s temp-control gated (cal=%s, temp_entity=%s, pts=%d, trig=%s)",
                host,
                min_cal_ok,
                bool(te),
                len(pts),
                trigger,
            )
            return
        dev.ctrl_state["active"] = True

        now = time.monotonic()
        temp = averaged_temp(now)
        if temp is None:
            st = hass.states.get(te)
            if st and st.state not in ("unknown", "unavailable", ""):
                try:
                    val = float(st.state)
                    temp_buf.append((now, val))
                    temp = averaged_temp(now)
                except Exception:
                    temp = None
        if temp is None:
            _LOGGER.debug("OpenFAN %s temp-control: no temp sample yet (trigger=%s)", host, trigger)
            return

        # Piecewise-linear interpolation on averaged temp
        if temp <= pts[0][0]:
            target = pts[0][1]
        elif temp >= pts[-1][0]:
            target = pts[-1][1]
        else:
            target = pts[0][1]
            for (t1, p1), (t2, p2) in zip(pts, pts[1:]):
                if t1 <= temp <= t2:
                    if t2 == t1:
                        target = max(p1, p2)
                    else:
                        ratio = (temp - t1) / (t2 - t1)
                        target = int(round(p1 + (p2 - p1) * ratio))
                    break

        # Clamp by min (except allow 0 to turn off)
        target = 0 if target == 0 else max(min_pwm, int(target))
        target = max(0, min(100, int(target)))

        last_applied = dev.ctrl_state.get("last_applied_pwm")
        last_ts = float(dev.ctrl_state.get("last_apply_ts") or 0.0)
        dead = int(entry.options.get("temp_deadband_pct", deadband))
        min_iv = int(entry.options.get("temp_update_min_interval", min_interval_s))

        # Deadband
        if last_applied is not None and abs(int(target) - int(last_applied)) < max(0, dead):
            dev.ctrl_state.update({"temp_avg": temp, "last_target_pwm": int(target)})
            return

        # Minimum interval between changes
        if (now - last_ts) < max(1, min_iv):
            dev.ctrl_state.update({"temp_avg": temp, "last_target_pwm": int(target)})
            return

        await dev.api.set_pwm(int(target))
        await dev.coordinator.async_request_refresh()
        dev.ctrl_state.update(
            {
                "temp_avg": temp,
                "last_target_pwm": int(target),
                "last_applied_pwm": int(target),
                "last_apply_ts": now,
            }
        )
        _LOGGER.debug(
            "OpenFAN %s temp-control APPLY: temp=%.1f°C target=%s%% (min=%s%%, trig=%s)",
            host,
            temp,
            target,
            min_pwm,
            trigger,
        )

    # Subscribe to temp entity initially (if set)
    if current_temp_entity:
        @callback
        def _on_temp(ev):
            new = ev.data.get("new_state")
            if not new or new.state in (None, "", "unknown", "unavailable"):
                return
            try:
                val = float(new.state)
            except Exception:
                return
            temp_buf.append((time.monotonic(), val))
            hass.async_create_task(apply_from_temp("state_change"))

        unsub_temp = async_track_state_change_event(hass, [current_temp_entity], _on_temp)
        entry.async_on_unload(unsub_temp)
        hass.async_create_task(apply_from_temp("startup"))

    # Periodic re-evaluation, so we react even if the temperature entity doesn't change state
    async def _periodic(now):
        await apply_from_temp("periodic")

    unsub_tick = async_track_time_interval(
        hass, _periodic, timedelta(seconds=max(5, min_interval_s))
    )
    entry.async_on_unload(unsub_tick)

    # -------- Helpers to resolve devices/entries and update options --------

    def _entity_owner_entry_id(entity_id: str) -> Optional[str]:
        registry = er.async_get(hass)
        ent = registry.async_get(entity_id)
        return ent.config_entry_id if ent else None

    def _get_entry_by_id(entry_id: str) -> Optional[ConfigEntry]:
        for ce in hass.config_entries.async_entries(DOMAIN):
            if ce.entry_id == entry_id:
                return ce
        return None

    async def _resolve_dev(entity_id: str) -> Tuple[Optional[Device], Optional[str]]:
        """Return (Device, owner_config_entry_id) for the given entity_id."""
        owner_id = _entity_owner_entry_id(entity_id)
        if not owner_id:
            _LOGGER.error("openfan_micro: entity_id %s not found in registry", entity_id)
            return None, None
        if owner_id == entry.entry_id:
            return entry.runtime_data, owner_id
        ce = _get_entry_by_id(owner_id)
        dev_rt = getattr(ce, "runtime_data", None) if ce else None
        if dev_rt is None:
            _LOGGER.error("openfan_micro: runtime_data not ready for entry_id=%s", owner_id)
        return dev_rt, owner_id

    def _update_options(update: dict[str, Any], target_entry_id: Optional[str] = None) -> None:
        """Write options to the *owner* entry (not necessarily 'entry')."""
        ce = _get_entry_by_id(target_entry_id) if target_entry_id else entry
        if not ce:
            _LOGGER.error("openfan_micro: target entry not found for options update")
            return
        new_opts = dict(ce.options or {})
        new_opts.update(update)
        hass.config_entries.async_update_entry(ce, options=new_opts)
        # Keep ctrl_state in sync if we updated our own entry
        if ce.entry_id == entry.entry_id:
            dev.ctrl_state.update(
                {
                    "min_pwm": int(new_opts.get("min_pwm", dev.ctrl_state["min_pwm"])),
                    "min_pwm_calibrated": bool(
                        new_opts.get(
                            "min_pwm_calibrated", dev.ctrl_state["min_pwm_calibrated"]
                        )
                    ),
                    "temp_entity": (new_opts.get("temp_entity") or "").strip(),
                    "temp_curve": new_opts.get("temp_curve", ""),
                    "temp_integrate_seconds": int(
                        new_opts.get("temp_integrate_seconds", integrate_s)
                    ),
                    "temp_update_min_interval": int(
                        new_opts.get("temp_update_min_interval", min_interval_s)
                    ),
                    "temp_deadband_pct": int(
                        new_opts.get("temp_deadband_pct", deadband)
                    ),
                }
            )

    # ------------------- Services (LED / voltage / calibration) -------------------

    async def svc_led_set(call):
        devx, owner_id = await _resolve_dev(call.data.get("entity_id", ""))
        if not devx:
            return
        await devx.api.led_set(bool(call.data["enabled"]))

    async def svc_set_voltage(call):
        devx, owner_id = await _resolve_dev(call.data.get("entity_id", ""))
        if not devx:
            return
        volts = int(call.data["volts"])
        await devx.api.set_voltage_12v(True if volts == 12 else False)

    async def svc_calibrate_min(call):
        devx, owner_id = await _resolve_dev(call.data.get("entity_id", ""))
        if not devx or not owner_id:
            _LOGGER.error(
                "openfan_micro.calibrate_min: could not resolve device from entity_id"
            )
            return
        from_pct = int(call.data.get("from_pct", 10))
        to_pct = int(call.data.get("to_pct", 40))
        step = int(call.data.get("step", 5))
        rpm_thr = int(call.data.get("rpm_threshold", 100))
        margin = int(call.data.get("margin", 5))

        found = None
        for pct in range(from_pct, to_pct + 1, step):
            await devx.api.set_pwm(pct)
            # allow RPM to settle
            await asyncio.sleep(max(1, int(devx.api._poll_interval)))
            await devx.coordinator.async_request_refresh()
            data = devx.coordinator.data or {}
            rpm = int(data.get("rpm") or 0)
            if rpm >= rpm_thr:
                found = pct
                break

        if found is not None:
            new_min = max(0, min(100, found + margin))
            _update_options({"min_pwm": new_min, "min_pwm_calibrated": True}, target_entry_id=owner_id)
            _LOGGER.info("Calibrated min_pwm=%s for entry %s", new_min, owner_id)
        else:
            _LOGGER.warning(
                "Calibration did not reach RPM threshold; leaving min_pwm unchanged."
            )

    # --------------- Services to configure temp control (Options fallback) ---------------

    async def svc_set_temp_control(call):
        nonlocal current_temp_entity, unsub_temp
        devx, owner_id = await _resolve_dev(call.data.get("entity_id", ""))
        if not devx or not owner_id:
            _LOGGER.error(
                "openfan_micro.set_temp_control: could not resolve device from entity_id"
            )
            return

        update = {}
        changed_entity = False
        if "temp_entity" in call.data:
            new_te = str(call.data.get("temp_entity") or "").strip()
            update["temp_entity"] = new_te
            changed_entity = (new_te != current_temp_entity)

        for k in (
            "temp_curve",
            "temp_integrate_seconds",
            "temp_update_min_interval",
            "temp_deadband_pct",
        ):
            if k in call.data:
                update[k] = call.data[k]

        _update_options(update, target_entry_id=owner_id)

        # (Re)subscribe to temp entity only for our own entry (owner == this entry)
        if owner_id == entry.entry_id and changed_entity:
            if unsub_temp:
                try:
                    unsub_temp()
                except Exception:
                    pass
            current_temp_entity = str(update.get("temp_entity", "")).strip()
            if current_temp_entity:
                @callback
                def _on_temp(ev):
                    new = ev.data.get("new_state")
                    if not new or new.state in (None, "", "unknown", "unavailable"):
                        return
                    try:
                        val = float(new.state)
                    except Exception:
                        return
                    temp_buf.append((time.monotonic(), val))
                    hass.async_create_task(apply_from_temp("state_change"))

                unsub_temp = async_track_state_change_event(
                    hass, [current_temp_entity], _on_temp
                )
                entry.async_on_unload(unsub_temp)

        # Immediate evaluation (only for our own entry)
        if owner_id == entry.entry_id:
            await apply_from_temp("set_temp_control")

    async def svc_clear_temp_control(call):
        nonlocal current_temp_entity, unsub_temp
        devx, owner_id = await _resolve_dev(call.data.get("entity_id", ""))
        if not devx or not owner_id:
            return
        _update_options({"temp_entity": ""}, target_entry_id=owner_id)
        if owner_id == entry.entry_id:
            current_temp_entity = ""
            if unsub_temp:
                try:
                    unsub_temp()
                except Exception:
                    pass
                unsub_temp = None
            dev.ctrl_state["active"] = False

    # Register all services
    hass.services.async_register(DOMAIN, "led_set", svc_led_set)
    hass.services.async_register(DOMAIN, "set_voltage", svc_set_voltage)
    hass.services.async_register(DOMAIN, "calibrate_min", svc_calibrate_min)
    hass.services.async_register(DOMAIN, "set_temp_control", svc_set_temp_control)
    hass.services.async_register(DOMAIN, "clear_temp_control", svc_clear_temp_control)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_get_options_flow(config_entry):
    return OptionsFlowHandler(config_entry)
