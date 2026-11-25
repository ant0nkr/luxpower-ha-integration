# LuxPower Modbus Integration for Home Assistant

[![HACS Default](https://img.shields.io/badge/HACS-Default-blue.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/ant0nkr/luxpower-ha-integration?style=for-the-badge)](https://github.com/ant0nkr/luxpower-ha-integration/releases)
[![GitHub License](https://img.shields.io/github/license/ant0nkr/luxpower-ha-integration?style=for-the-badge)](https://github.com/ant0nkr/luxpower-ha-integration/blob/main/LICENSE)
[![Donate](https://img.shields.io/badge/Donate-PayPal-yellow.svg?style=for-the-badge)](https://www.paypal.com/donate/?business=LDZNJ5UTHRBY8&no_recurring=0&item_name=Help+improve+Lux+Power+integration+for+Home+Assistant.+Every+contribution+keeps+the+project+alive&currency_code=USD)

A Home Assistant integration to monitor and control LuxPower inverters locally via their Modbus TCP interface.

This integration connects directly to your inverter's WiFi dongle, providing real-time monitoring and control over inverter settings without relying on the cloud.

## Features

* **100% Local Control & Monitoring:** Direct Modbus TCP communication over your local network with no cloud dependency.
* **Real-Time Energy Monitoring:** Track PV, battery SOC/SOH, grid import/export, EPS, load power, and Load Percentage.
* **Full Inverter Control:** Adjust currents, charge/discharge schedules, grid feed-in, and maintenance actions.
* **Battery BMS Monitoring:** Per-battery state, cell voltages, and temperatures for LuxPower batteries with auto-discovery.
* **12 V, 24 V & 48 V Support:** Automatically scales battery voltage limits and ranges to match your system.
* **Parallel Inverter Support:** Primary/secondary-aware entities and controls for multi-inverter setups.
* **Organized Device Structure:** Groups entities into PV, Grid, EPS, Generator, and Battery sub-devices.
* **Optional Read-Only Mode:** Exposes control registers as read-only sensors for safe monitoring.
* **Resilient & Diagnosable:** Automatic retries, packet recovery, fault/warning/AFCI codes, and redacted diagnostics.
* **Ready-to-Use Blueprints:** Included blueprints for timed or target-SOC charging with settings restore.

## Installation

### Prerequisites

* **Home Assistant:** `2025.5.0` or newer (`2026.11+` includes the built-in Marketplace)
* **HACS:** `2.0.5` or newer (only required on Home Assistant versions prior to `2026.11`)
* **Network:** Your LuxPower inverter's WiFi data logging dongle must be on the same local network as Home Assistant, and you will need its IP address.

### Home Assistant Marketplace (Home Assistant 2026.11+)

Starting with Home Assistant `2026.11`, HACS is built directly into Home Assistant as the **Marketplace**:

1. Navigate to **Settings** > **Marketplace** in your Home Assistant instance.
2. Search for **"Luxpower Inverter (Modbus)"** and click **Install**.
3. Restart Home Assistant when prompted.

### HACS (Home Assistant 2025.5 – 2026.10)

On Home Assistant versions prior to `2026.11`, install via the standalone HACS integration (this integration is in the default HACS repository):

1. Navigate to **HACS** > **Integrations** in your Home Assistant instance.
2. Click **Explore & Download Repositories**.
3. Search for **"Luxpower Inverter (Modbus)"** and click **Download**.
4. Restart Home Assistant when prompted.

### Manual Installation

1. Copy the `custom_components/lxp_modbus` folder from this repository into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Compatibility

### Dongles & Connection

| Hardware / Mode | Supported | Notes |
| :--- | :---: | :--- |
| **E-WIFI dongle (local protocol)** | Yes | Connects over TCP port `8000` (default). Only one local client should connect to the dongle at a time. |
| **E-WIFI ENC dongle** | No | May leave port `8000` open but does not expose the unencrypted local protocol. Use an isolated RS485 bridge (e.g., [OpenLux](https://github.com/f-garofalo/openlux)) or a cloud integration instead. |

### Inverter Firmware, Batteries & Voltage Classes

| Feature / Component | Requirement / Options | Notes |
| :--- | :--- | :--- |
| **Inverter Protocol** | LuxPower / compatible EG4 models | Model is auto-detected from hold registers `7–8`. Unimplemented registers (`0xFFFF`) on a given model/firmware are automatically ignored. |
| **Register Block Size** | `125` (modern) / `40` (legacy) | Use `40` on older firmware that rejects larger block reads. |
| **Battery BMS (`5000+` registers)** | LuxPower batteries + block size `>= 120` | Third-party batteries that do not populate registers `5000+` will not expose per-battery sensors (polling automatically backs off). Not available when block size is `40`. |
| **Battery Voltage Class** | `48 V` (default), `24 V`, `12 V` | Scales battery voltage limits and ranges in `number` controls to match your system. |
| **Parallel Inverters** | Primary + Secondary | Configure each inverter separately; `master_only` entities are omitted on secondary units. |

## Configuration

Configuration is done entirely through the Home Assistant UI:

1. Go to **Settings** > **Devices & Services**.
2. Click **Add Integration** and search for **"LuxPower Inverter (Modbus)"**.
3. Enter the connection and inverter details.

### Configuration Options

| Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **IP Address** | string | — | **(Required)** IP address of your inverter's WiFi dongle. |
| **Port** | integer | `8000` | **(Required)** Modbus TCP communication port. |
| **WiFi Dongle Serial Number** | string | — | **(Required)** 10-character serial number of your WiFi dongle. |
| **Inverter Serial Number** | string | — | **(Required)** 10-character serial number of your inverter. |
| **Polling Interval** | integer | `60` | **(Required)** How often (in seconds) to poll the inverter for data. |
| **Inverter Rated Power** | integer | `5000` | **(Required)** Rated power of your inverter in Watts (e.g., `5000` for a 5 kW model). |
| **Entity Prefix** | string | *(blank)* | (Optional) Custom prefix for all entity names (e.g., `LXP`). |
| **Read-Only Mode** | boolean | `false` | (Optional) Exposes control registers as read-only `sensor` entities. See the warning below before changing. |
| **Register Block Size** | integer | `125` | (Optional) Number of registers to read per block. Use `125` for most inverters, or `40` for older firmware. |
| **Connection Retry Attempts** | integer | `3` | (Optional) Immediate retry attempts on connection failure (`1–10`). |
| **Enable Device Grouping** | boolean | `true` | (Optional) Group entities into logical sub-devices (`PV`, `Grid`, `EPS`, `Generator`, `Battery`). |
| **Battery Entities** | string | `none` | (Optional) Battery BMS monitoring mode: `none` (disabled), `auto` (auto-discover), or comma-separated battery serial numbers. |
| **Battery Voltage (V)** | integer | `48` | (Optional) Battery system voltage class (`12`, `24`, or `48`). Adjusts battery voltage limits and ranges to match your system. |

> [!WARNING]
> **Read-Only Mode** fundamentally changes the entity types created for inverter controls:
>
> * **`false` (default):** Creates interactive `number`, `switch`, `select`, `button`, and `time` entities.
> * **`true`:** Exposes those settings as read-only `sensor` entities so you can view values without modifying them.
>
> **Choose this carefully during initial setup.** Changing this option later will **delete** the existing control entities and replace them with `sensor` entities (or vice versa), which will break dashboards, automations, and entity history.

### Device Grouping

When **Enable Device Grouping** is enabled (default), entities are organized into logical sub-devices under your inverter:

* **PV Group:** Solar panel monitoring and MPPT controls
* **Grid Group:** Utility grid connection, import/export data, and grid controls
* **EPS Group:** Emergency Power Supply / backup load outputs
* **Generator Group:** Backup generator monitoring and controls
* **Battery Group:** BMS data, cell voltages, temperatures, and battery controls

You can toggle this setting at any time in the integration options if you prefer all entities under a single device.

### Battery Monitoring (LuxPower Batteries Only)

When enabled, the integration reads battery data directly from the BMS via Modbus register range `5000+`, providing per-battery sensors including:

* **State:** SOC, SOH, Voltage, Current, Capacity, Cycle Count
* **Cell Details:** Max/Min Cell Voltage, Max/Min Cell Temperature, Cell Voltage Difference
* **Diagnostics:** Firmware Version, Max Charge/Discharge Current

**Modes:**
* `none` *(default)*: Battery monitoring is disabled.
* `auto`: Automatically discovers connected batteries and creates entities dynamically.
* **Comma-separated serial numbers** (e.g., `SN1234567890,SN0987654321`): Monitors only the specified batteries.

When Device Grouping is enabled, each battery appears as a separate sub-device.

> [!NOTE]
> Battery data polling requires a **Register Block Size** of at least `120`. If your block size is set to `40` for older firmware, battery monitoring will not be available.

### Register Block Size & Reconnection Logic

* **Register Block Size:** Use `125` (default) for most modern inverter firmware. Switch to `40` if you experience communication errors on older firmware.
* **Reconnection & Reliability:** On transient failures, the integration retries up to the configured **Connection Retry Attempts** (`1–10`) with backoff and briefly retains cached values across brief interruptions so automations do not immediately fail.

## Energy Dashboard & Predbat

### Home Assistant Energy Dashboard

All energy sensors use `total_increasing` in `kWh`. Map the `Total` sensors in **Settings** > **Dashboards** > **Energy**:

| Energy Dashboard Slot | Recommended Sensor | Notes |
| :--- | :--- | :--- |
| **Solar production** | `PV Energy Total` | Or add `PV1 Energy Total` – `PV6 Energy Total` individually per string |
| **Grid consumption** | `Energy from Grid Total` | Total energy imported from the grid |
| **Return to grid** | `Energy to Grid Total` | Total energy exported to the grid |
| **Battery charging** | `Charge Energy Total` | Total energy charged into the battery |
| **Battery discharging** | `Discharge Energy Total` | Total energy discharged from the battery |

> [!TIP]
> If you configured an **Entity Prefix** (e.g., `LXP`), your entity names and IDs will be prefixed accordingly. For home load tracking, `Load Consumption Total` or `Home Consumption Total Calculated` are also available.

### Predbat

* **Inverter Time:** The **Inverter Time** sensor (disabled by default) exposes the inverter's internal wall-clock time without a timezone. Enable it under **Settings** > **Devices & Services** > **Entities** (filter for **Disabled**), then point Predbat's `inverter_time` setting to that entity ID.
* **Control Entities:** Ensure **Read-Only Mode** is disabled (`false`) so Predbat can write charge/discharge schedules, currents, and mode switches.

## Entities

See [ENTITIES.md](ENTITIES.md) for the complete reference table of all 741 inverter entities and 18 per-battery sensors.

### Sensors
Provides operational, energy, and diagnostic data, including:
* Inverter State (Text and Code)
* Battery SOC & SOH
* PV Power (Total and per-string)
* Grid Import/Export Power
* Load Power & Calculated Load Percentage
* Battery Charge/Discharge Power
* Daily & Total Energy Statistics (PV, Grid, Load, etc.)
* Temperatures (Battery, Radiator, etc.)
* Voltages, Currents, and Frequencies for Grid, EPS, and Battery
* Diagnostic timestamps (`Data Read At` for input and battery registers)
* **Inverter Time** *(disabled by default)*: The wall-clock time kept by the inverter for charge/discharge windows (no timezone). Useful for spotting clock drift or configuring Predbat's `inverter_time`. To enable it, go to **Settings** > **Devices & Services** > **Entities**, toggle the **Disabled** filter, and enable the entity.

### Binary Sensors
* Grid Connected
* BMS Charge Allowed / BMS Discharge Allowed
* BMS Request Charge / BMS Request Full Charge

### Numbers
* Charge & Discharge Currents
* AC Charge Power Limit
* End of Discharge (EOD) SOC
* Battery Stop Charging Voltage / SOC

### Switches
* AC Charging Enable
* Feed-In Grid Enable
* Forced Discharge Enable
* Eco & Green Modes

### Selects
* AC Charge Type (by Time, SOC, etc.)
* Output Priority (Battery first, PV first, etc.)

### Buttons
* Reboot Inverter
* Clear Detected Phases
* Clear Parallel Alarm
* Reset G100 Lockout

### Time
* AC Charging Start & End Times
* Peak Shaving Start & End Times

## Blueprints

This integration includes blueprints to help you get started with common automations.

### How to Import Blueprints

**Method 1: Direct Import Button (Easiest)**

Click the **Import Blueprint** button under the blueprint you want to use to open it directly in your Home Assistant instance.

**Method 2: Manual Import**

1. In Home Assistant, go to **Settings** > **Automations & Scenes**.
2. Select the **Blueprints** tab.
3. Click **Import Blueprint** in the bottom right.
4. Paste the **Manual Import URL** for the blueprint you want.
5. Click **Preview Blueprint** and then **Import Blueprint**.

---

### Available Blueprints

#### Force Charge for a Specific Duration
Temporarily forces the inverter to charge from the grid for a set duration. It saves your existing settings, applies the temporary charge schedule, and restores your settings when finished.

[![Open your Home Assistant instance and import this blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fant0nkr%2Fluxpower-ha-integration%2Fmain%2Fblueprints%2Fscript%2Flxp_force_charge.yaml)

> Manual Import URL: `https://raw.githubusercontent.com/ant0nkr/luxpower-ha-integration/main/blueprints/script/lxp_force_charge.yaml`

#### Force Charge to a Target SOC
Charges your inverter's battery from the AC grid until it reaches a target State of Charge (SOC) percentage. It saves a snapshot of your current inverter settings before starting and restores them once the target SOC is met.

[![Open your Home Assistant instance and import this blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fant0nkr%2Fluxpower-ha-integration%2Fmain%2Fblueprints%2Fautomation%2Flxp_charge_automation.yaml)

> Manual Import URL: `https://raw.githubusercontent.com/ant0nkr/luxpower-ha-integration/main/blueprints/automation/lxp_charge_automation.yaml`

## Debugging

### Debug Logging & Diagnostics

To enable debug logging, add the following to your `configuration.yaml` and restart Home Assistant:

```yaml
logger:
  default: info
  logs:
    custom_components.lxp_modbus: debug
```

You can also download a diagnostics report (with sensitive values redacted) from **Settings** > **Devices & Services** > **LuxPower Inverter (Modbus)** > **Download diagnostics** to attach when reporting an issue.

### Port 8000 connects, then resets

LuxPower dongles that look alike can expose different local behavior. Check the dongle type in the LuxPower cloud: an **E-WIFI ENC** unit may not provide the local protocol this integration needs, even when TCP port 8000 appears open. Firmware version alone does not reliably identify that capability.

For an **E-WIFI** unit that resets or stops answering on port 8000:

1. Stop scanners, `modpoll`, `lxp-bridge`, and other clients using the dongle.
2. Reset the dongle, then cold-start the inverter and dongle according to the manufacturer's safety procedure. One reported recovery required a full shutdown, removing the dongle for several minutes, reinstalling it, and reconnecting Wi-Fi.
3. Reserve the dongle's IP address in DHCP.
4. Configure this integration with the dongle IP, port `8000`, and the exact dongle and inverter serial numbers. Let it make the first protocol connection; malformed probes can leave some dongles refusing later connections until another reset.

If the cloud identifies the dongle as **E-WIFI ENC**, or a clean cold start still cannot complete the integration's model read, this integration cannot repair that firmware/device limitation. Options reported by users include asking LuxPower for a local-capable E-WIFI dongle, using an isolated RS485 adapter with an [OpenLux-style bridge](https://github.com/f-garofalo/openlux), or using a LuxPower-compatible cloud integration such as [EG4 Web Monitor](https://github.com/joyfulhouse/eg4_web_monitor). Cloud polling is slower and may expose fewer values than a local connection.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, test instructions (`pytest`), and pull request guidelines. Register mappings, ranges, and protocol notes are documented in [docs/protocol-registers.md](docs/protocol-registers.md), and release history is tracked in [CHANGELOG.md](CHANGELOG.md).
