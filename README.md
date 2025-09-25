# OpenFAN Micro — Home Assistant Integration (fw 107c190 compatible)

Home Assistant custom integration to control **[OpenFAN Micro](https://docs.sasakaranovic.com/openfan_micro/)** via its local Web API.

This fork adds **firmware 107c190** compatibility and improves stability:
- New **set endpoint**: `GET /api/v0/fan/0/set?value=NN` (with legacy fallback)
- **Status parser** accepts **both** payload shapes:
  - Top-level: `{"status":"ok","rpm":NNN,"pwm_percent":NN}`
  - Nested: `{"status":"ok","data":{"rpm":NNN,"pwm_percent":NN}}`
- Proper **on/off + percentage** support on the `fan` entity
- Separate **RPM sensor** entity
- Robust error handling and debug logging
- Optional MAC in device registry (works even if the API does not expose MAC)

> Tested with two devices on fw `107c190`.

---

## Install

### HACS (Custom Repository)
1. In Home Assistant go to **HACS → Integrations → ⋮ → Custom repositories**.
2. **Add** repository URL: `https://github.com/bitlisz1/hass-openfan-micro`  
   **Category:** *Integration*
3. Then open **HACS → Integrations → + Explore & Add Repositories**, search for **OpenFAN Micro**, and install.
4. **Restart Home Assistant.**



### Manual
Copy this folder:
```
custom_components/openfan_micro
```
into your HA config folder:
```
config/custom_components/openfan_micro
```
Then **Restart Home Assistant**.

---

## Setup (Config Flow)
1. Go to **Settings → Devices & Services → + Add Integration**.
2. Search for **OpenFAN Micro**.
3. Enter:
   - **Host** — IP of your OpenFAN Micro
   - **Name** — optional friendly name

The integration creates **one device** with two entities:
- **Fan** (`fan.<name>`) — on/off + percentage 0–100
- **RPM Sensor** (`sensor.<name>_rpm`) — current rotor speed

---

## Lovelace Examples

**Tile + Gauge**
```yaml
type: vertical-stack
cards:
  - type: tile
    entity: fan.uopenfanup
    name: UOpenFan Up
    features:
      - type: fan-speed
  - type: gauge
    entity: sensor.uopenfanup_rpm
    name: Up RPM
    min: 0
    max: 4000
```

**Fan + RPM**
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
```

---

## Troubleshooting

### Enable debug logging
Add to `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.openfan_micro: debug
```
Restart HA, then check **Settings → System → Logs**.

### Quick API sanity check
Open in a browser (replace `<IP>`):
- `http://<IP>/api/v0/fan/status`
- `http://<IP>/api/v0/fan/0/set?value=60`

A healthy device should return JSON and `{ "status": "ok", ... }`.

---

## Compatibility Notes

- Designed for **OpenFAN Micro**; supports firmware **107c190** (and earlier, via fallbacks).
- Uses only local HTTP; no cloud connectivity required.
- Entities refresh every **5 seconds** by default (adjustable in code).

---

## Contributing

PRs welcome. Please include:
- Real device logs (DEBUG) for any API changes
- Firmware version
- Clear reproduction steps

---

## License

MIT © 2025
