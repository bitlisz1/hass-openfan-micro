# OpenFAN Micro — Home Assistant Integration (Pro)

> **Status:** Beta `v0.3.1-beta.3`  
> Custom integration for [OpenFAN Micro](https://github.com/SasaKaranovic/OpenFan-Micro) devices.  
> Adds LED and 5V/12V switches, stall detection, diagnostics, and **temperature-based fan control** with smoothing and **calibration-gated minimum PWM**.

---

## Features

- **Fan control**: on/off and percentage (0–100%)
- **RPM sensor** (`sensor.<name>_rpm`) with long-term statistics
- **LED switch** (`switch.<name>_led`) — activity LED on/off
- **12V mode switch** (`switch.<name>_12v_mode`) — on=12V, off=5V
- **Availability gating** — marks device `unavailable` only after N consecutive failures
- **Stall detection** — binary sensor + persistent notification + HA event
- **Diagnostics export** — from the integration card
- **Temperature-based control** (piecewise-linear curve) with:
  - moving-average **integration window**
  - **minimum interval** between speed changes
  - **deadband** to avoid flapping
  - **clamped by calibrated minimum PWM** (never drives below min, except when fully off)

---

## Requirements

- OpenFAN Micro firmware providing:
  - Fan status & set: `/api/v0/fan/status`, `/api/v0/fan/0/status`, `/api/v0/fan/0/set?value=…` (legacy `/api/v0/fan/set?value=…` also supported)
  - Device status: `/api/v0/openfan/status` (fields: `act_led_enabled`, `fan_is_12v`)
  - LED & voltage: `/api/v0/led/(enable|disable)`, `/api/v0/fan/voltage/(high|low)?confirm=true`
- Home Assistant **2024.12 or newer** (tested on 2025.x)

---

## Installation

### Option A — HACS (Custom Repository)

1. **HACS → Integrations →** ⋮ **Custom repositories**
2. Add: `https://github.com/bitlisz1/hass-openfan-micro` (Category: **Integration**)
3. Find **OpenFAN Micro** → **Download**
4. (Optional) Click **“Need a different version?”** and select **`v0.3.1-beta.3`** (pre-release)
5. **Restart Home Assistant**
6. **Settings → Devices & Services → Add Integration → OpenFAN Micro**, then enter the device IP and a friendly name  
   (repeat per device if you have multiple)

### Option B — Manual

1. Copy this folder to your HA config:  
   `custom_components/openfan_micro/`
2. **Restart Home Assistant**
3. Add the integration: **Settings → Devices & Services → Add Integration → OpenFAN Micro**

> **Note:** If the **Options** button doesn’t show up on the integration card (frontend cache), all advanced settings can be configured via **Developer Tools → Actions** services (see below).

---

## Entities created (per device)

- `fan.<name>` — main fan entity (percentage + on/off)
- `sensor.<name>_rpm` — RPM (unit: `rpm`, `state_class: measurement`)
- `switch.<name>_led` — activity LED on/off
- `switch.<name>_12v_mode` — 12V mode on/off (on=12V, off=5V)
- `binary_sensor.<name>_stall` — **on** when stall is detected

### Extra attributes on the fan entity

The `fan.<name>` entity exposes:

- `min_pwm`, `min_pwm_calibrated`
- `temp_control_active`
- `temp_entity`, `temp_curve`
- `temp_avg` (moving-average), `last_target_pwm`, `last_applied_pwm`
- `temp_update_min_interval`, `temp_deadband_pct`

Use a **Markdown** Lovelace card to display these attributes if you like (examples below).

---

## First run: Calibrate the minimum PWM (required for temp control)

Run once per device to find the minimum PWM that reliably spins the fan.

**Developer Tools → Actions →**

`openfan_micro.calibrate_min`:

yaml

action: openfan_micro.calibrate_min
data:
  entity_id: fan.your_fan_entity
  from_pct: 5
  to_pct: 40
  step: 2
  rpm_threshold: 120
  margin: 5
The routine increases PWM until RPM >= rpm_threshold, then stores min_pwm = found + margin

Sets min_pwm_calibrated = true

Tip: Re-calibrate after switching 5V/12V

Temperature-based control
You can configure it through Options (if visible) or via Actions services (always available).

A) Configure via Options

Integrations → OpenFAN Micro → Options:

temp_entity: temperature sensor entity (e.g. sensor.rt_ax92u_temperature_cpu)
temp_curve: curve points in °C=PWM% pairs, comma-separated, e.g.

45=35, 60=60, 70=100

temp_integrate_seconds: moving-average window (e.g. 30–90)
temp_update_min_interval: minimum seconds between changes (e.g. 10–30)
temp_deadband_pct: change threshold in % to avoid tiny adjustments (e.g. 3–5)

The controller activates only if the entry is calibrated and has a valid temp_entity and curve.

B) Configure via Actions (services)
Enable / update:

yaml

action: openfan_micro.set_temp_control
data:
  entity_id: fan.your_fan_entity
  temp_entity: sensor.any_temperature
  temp_curve: "45=35, 60=60, 70=100"
  temp_integrate_seconds: 30
  temp_update_min_interval: 10
  temp_deadband_pct: 3
Disable:

yaml

action: openfan_micro.clear_temp_control
data:
  entity_id: fan.your_fan_entity

Recommended curves (45–75 °C)
Quiet: 45=25, 60=55, 75=100

Balanced (default): 45=35, 60=60, 70=100

Aggressive: 45=40, 55=70, 65=100

The controller never drives below min_pwm (except when target is 0%, which turns the fan off).

LED & Voltage services (optional)

yaml

# LED on/off
action: openfan_micro.led_set
data:
  entity_id: fan.your_fan_entity
  enabled: true

# 12V / 5V (UI offers "5"/"12" strings; service accepts numbers too)
action: openfan_micro.set_voltage
data:
  entity_id: fan.your_fan_entity
  volts: "12"   # or "5"
Stall detection
The binary sensor turns on if PWM > min_pwm and RPM == 0 for N consecutive polls
(stall_consecutive option; default 3). When detected, the integration also emits:

Event: openfan_micro_stall (payload includes host)

Persistent notification in HA

Diagnostics
Settings → Devices & Services → Integrations → OpenFAN Micro → ⋮ Download diagnostics
The bundle includes:

Config entry options

Last coordinator data (rpm, pwm, LED, 12V, stall)

Controller state (temp average, last target/applied PWM, gating flags)

If you open an issue, attaching diagnostics and a debug log helps a lot.

Troubleshooting
Options button missing: Use the Actions services; refresh the browser (Ctrl+F5) or restart HA to reveal Options later.

Fan sticks near minimum: Confirm min_pwm_calibrated: true. Check temp_avg, last_target_pwm, last_applied_pwm. Consider reducing temp_deadband_pct, lowering temp_update_min_interval, or raising curve points.

LED/12V toggles jump back: Ensure your firmware provides /api/v0/openfan/status; this integration reads act_led_enabled / fan_is_12v from there.

“No long-term statistics” warning: The RPM sensor sets state_class: measurement. If you saw earlier warnings, you can safely delete the old statistics record when prompted.

Multiple devices: All services accept entity_id to target the correct device; options are stored on the owner config entry.

Enable debug logging
yaml

logger:
  default: info
  logs:
    custom_components.openfan_micro: debug

Lovelace examples
Entities + attributes (Markdown)

yaml

type: vertical-stack
cards:
  - type: entities
    title: UOpenFan Up
    entities:
      - entity: fan.uopenfanup
        name: Fan
      - entity: sensor.uopenfanup_rpm
        name: RPM
      - entity: switch.uopenfan_up_led
        name: LED
      - entity: switch.uopenfan_up_12v_mode
        name: 12V Mode
  - type: markdown
    content: |
      **Control state**
      - Calibrated min: **{{ state_attr('fan.uopenfanup','min_pwm') }}%** (calibrated: {{ state_attr('fan.uopenfanup','min_pwm_calibrated') }})
      - Temp control active: **{{ state_attr('fan.uopenfanup','temp_control_active') }}**
      - Temp entity: `{{ state_attr('fan.uopenfanup','temp_entity') }}`
      - Temp average: **{{ (state_attr('fan.uopenfanup','temp_avg') or 0) | round(1) }}°C**
      - Target PWM: **{{ state_attr('fan.uopenfanup','last_target_pwm') }}%**
      - Applied PWM: **{{ state_attr('fan.uopenfanup','last_applied_pwm') }}%**

Gauge (RPM)
yaml

type: gauge
entity: sensor.uopenfanup_rpm
min: 0
max: 2500
name: UOpenFan Up RPM
(Repeat the stack for the “Down” fan with the corresponding entity ids.)


Contributing
Issues and PRs are welcome. When reporting bugs, please attach:

Diagnostics export (see above)

Debug logs

Credits

OpenFAN Micro hardware & firmware: Sasa Karanovic

Original HA integration: BeryJu

This fork: enhancements for LED/12V, stall detection, diagnostics, and temperature-based control with smoothing

License
See LICENSE in this repository. The integration may include code adapted from the original project; original licenses apply.