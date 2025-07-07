# OpenFAN Micro

**Home Assistant custom integration for controlling [OpenFAN Micro](https://docs.sasakaranovic.com/openfan_micro/) fans.**

This integration lets you control your OpenFAN Micro fan via its REST API, including:
- Setting the fan speed as a percentage
- Viewing the fan’s current speed (RPM) as a separate sensor entity

**Most of this code is AI generated, so ymmv**

---

## Installation

### HACS

If you plan to release via HACS:

1. Go to **HACS → Integrations → Custom repositories → Add**
2. Paste the repository URL where this integration is hosted
3. Select “Integration”
4. Click **Add**

Or install manually:

### Manual Installation

1. Copy the folder:
    ```
    custom_components/openfan_micro
    ```
    into:
    ```
    config/custom_components/openfan_micro
    ```

2. Restart Home Assistant.

---

## Configuration

This integration supports **Config Flow UI** setup from Home Assistant’s front end.

### How to set it up

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration**
3. Search for:
    ```
    OpenFAN Micro
    ```
4. Enter:
    - **Host** → The IP address of your OpenFAN Micro fan
    - **Name** → (Optional) A custom name for your fan entity

---

## Entities Created

When setup is complete, this integration will create:

- **Fan Entity**
    - Controls the fan speed (%)
    - Reports current speed percentage

- **RPM Sensor Entity**
    - Displays the fan’s current RPM

Both entities are grouped under the same device in Home Assistant.

---

---

## Development

This integration uses:
- `requests` library for HTTP calls
- Config Flow UI
- Fan platform
- Sensor platform

---

## License

MIT License
