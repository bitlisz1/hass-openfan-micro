# OpenFAN Micro — Home Assistant Integration (pro features, fw 107c190)

Local control of **[OpenFAN Micro](https://docs.sasakaranovic.com/openfan_micro/)** via its Web API.

## v0.3.1-beta.2 (pre-release)
- **LED switch** (`switch.<name>_led`)
- **12V mode switch** (`switch.<name>_12v_mode`) – on=12V, off=5V
- **Availability gating** (unavailable only after N consecutive failures)
- **Stall detection** (binary sensor + notification + event `openfan_micro_stall`)
- **Temperature curve controller** (piecewise-linear, **requires calibration**)
- **Smoothing for temperature control**:
  - `temp_integrate_seconds` — moving average window
  - `temp_update_min_interval` — min time between PWM changes
  - `temp_deadband_pct` — do not change unless difference exceeds this
- **Calibration service** to determine **min_pwm** reliably (enables temp control)

> Still includes: Fan on/off + percentage, RPM sensor.

---

## Install (HACS Custom Repository)
1. HACS → Integrations → ⋮ → **Custom repositories**
2. Add: `https://github.com/bitlisz1/hass-openfan-micro` (Category: *Integration*)
3. Install → **Restart Home Assistant** → Add Integration → **OpenFAN Micro**

> For this beta, publish a GitHub pre-release tag: `v0.3.1-beta.2` (HACS → *Show beta versions*).

---

## Entities
- **Fan**: `fan.<name>` — on/off + percentage (0–100)
- **RPM sensor**: `sensor.<name>_rpm`
- **LED switch**: `switch.<name>_led`
- **12V switch**: `switch.<name>_12v_mode`
- **Stall**: `binary_sensor.<name>_stall`

---

## Options (Settings → Devices & Services → OpenFAN Micro → Configure)
- **Poll interval** (seconds, default 5)
- **Min PWM** (default 0; set by calibration)
- **Failure threshold** (consecutive failures to mark unavailable, default 3)
- **Stall consecutive** (consecutive 0-RPM readings above min to mark “stalled”, default 3)
- **Temperature entity** (e.g. `sensor.asusrouter_temperature`)
- **Temperature curve** (e.g. `45=25, 65=55, 70=100`)
- **Temp smoothing**:
  - `temp_integrate_seconds` (default 30)
  - `temp_update_min_interval` (default 10)
  - `temp_deadband_pct` (default 3)

> **Temperature control is active only after calibration** (`min_pwm_calibrated: true`) and never drives the fan below **min_pwm** (except turning off → 0%).

---

## Services (Developer Tools → Actions)
- `openfan_micro.led_set` (`entity_id`, `enabled: true/false`)
- `openfan_micro.set_voltage` (`entity_id`, `volts: 5|12`)
- `openfan_micro.calibrate_min` (`entity_id`, optional: `from_pct`, `to_pct`, `step`, `rpm_threshold`, `margin`)

**Calibration flow**
1. Run `calibrate_min` (e.g. 10→40%, step 5, `rpm_threshold: 100`, `margin: 5`)
2. Options updated: `min_pwm`, `min_pwm_calibrated: true`
3. Temperature control will now obey `min_pwm`.

---

## Lovelace example
```yaml
type: vertical-stack
cards:
  - type: fan
    entity: fan.uopenfanup
    name: UOpenFan Up
  - type: gauge
    entity: sensor.uopenfanup_rpm
    name: Up RPM
    min: 0
    max: 4000
  - type: entities
    entities:
      - entity: switch.uopenfanup_led
        name: Activity LED
      - entity: switch.uopenfanup_12v_mode
        name: 12V Mode
```

---

## Troubleshooting
Enable debug logs:
```yaml
logger:
  logs:
    custom_components.openfan_micro: debug
```
Quick API checks (`<IP>` is the device):
- `http://<IP>/api/v0/fan/status`
- `http://<IP>/api/v0/openfan/status`
- `http://<IP>/api/v0/led/enable` / `.../disable`
- `http://<IP>/api/v0/fan/voltage/high?confirm=true` / `.../low?confirm=true`
