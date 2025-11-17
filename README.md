# LuxPower Modbus Integration for Home Assistant

[![HACS Default](https://img.shields.io/badge/HACS-Default-blue.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/ant0nkr/luxpower-ha-integration?style=for-the-badge)](https://github.com/ant0nkr/luxpower-ha-integration/releases)
[![GitHub License](https://img.shields.io/github/license/ant0nkr/luxpower-ha-integration?style=for-the-badge)](https://github.com/ant0nkr/luxpower-ha-integration/blob/main/LICENSE)
[![Donate](https://img.shields.io/badge/Donate-PayPal-yellow.svg?style=for-the-badge)](https://www.paypal.com/donate/?business=LDZNJ5UTHRBY8&no_recurring=0&item_name=Help+improve+Lux+Power+integration+for+Home+Assistant.+Every+contribution+keeps+the+project+alive&currency_code=USD)

A comprehensive Home Assistant integration to monitor and control LuxPower inverters via their Modbus TCP interface.

This integration connects directly to your inverter's WiFi dongle, providing real-time data and control over various settings without relying on the cloud.

> [!NOTE]
> **Version 0.2.0 introduces Device Grouping** - a major organizational improvement that groups your 250+ entities into logical sub-devices (PV, Grid, EPS, Generator, Battery, Temperatures & Diagnostics, Settings & Schedules) for much better navigation in Home Assistant. See the [Device Grouping section](#device-grouping-available-since-v020) below for details.

## Features

* **Real-time Monitoring:** Track PV power, battery state of charge (SOC), grid import/export, load consumption, and more.
* **Inverter Control:** Change charge/discharge currents, set timed charging/discharging periods, and enable/disable features like grid feed-in.
* **Organized Device Structure:** (v0.2.0+) Entities are automatically grouped into logical sub-devices (PV, Grid, EPS, Generator, Battery, Temperatures & Diagnostics, Settings & Schedules) for better organization in Home Assistant.
* **Detailed States:** A user-friendly text sensor shows exactly what the inverter is doing (e.g., "PV Powering Load & Charging Battery").
* **Calculated Sensors:** Includes derived sensors like "Load Percentage" for a clearer view of your system's performance.
* **Local Polling:** All communication is local. No cloud dependency.

### Prerequisites

Your LuxPower inverter's WiFi data logging dongle must be connected to the same local network as your Home Assistant instance. You will need to know its IP address.

### HACS (Home Assistant Community Store)

This integration is available in the default HACS repository.

1.  Navigate to **HACS** > **Integrations** in your Home Assistant instance.
2.  Click the **Explore & Download Repositories** button.
3.  Search for "Luxpower Inverter (Modbus)" and click **"Download"**.
4.  Restart Home Assistant when prompted.

### Manual Installation

1.  Copy the `lxp_modbus` folder from this repository into your Home Assistant `custom_components` directory.
2.  Restart Home Assistant.

## Configuration

Configuration is done entirely through the Home Assistant UI.

1.  Go to **Settings** > **Devices & Services**.
2.  Click **Add Integration** and search for **"Luxpower Inverter (Modbus)"**.
3.  Fill in the required details for your inverter.

### Configuration Options

| Name | Type | Description |
| :--- | :--- | :--- |
| **IP Address** | string | **(Required)** The IP address of your inverter's WiFi dongle. |
| **Port** | integer | **(Required)** The communication port for the Modbus connection, typically `8000`. |
| **Dongle Serial Number**| string | **(Required)** The 10-character serial number of your WiFi dongle. |
| **Inverter Serial Number**| string | **(Required)** The 10-character serial number of your inverter. |
| **Polling Interval** | integer | **(Required)** How often (in seconds) to poll the inverter for data. Default is 60. |
| **Inverter Rated Power**| integer | **(Required)** The rated power of your inverter in Watts (e.g., `5000` for a 5kW model). |
| **Entity Prefix** | string | (Optional) A custom prefix for all entity names (e.g., 'LXP'). Leave blank for no prefix. |
| **Read-Only Mode** | boolean| (Optional) See the important warning below before changing this setting. |
| **Register Block Size** | integer | (Optional) Size of register blocks to read. Use `125` (default) for most inverters, use `40` for older firmware versions that don't support larger blocks. |
| **Connection Retry Attempts** | integer | Number of connection retry attempts before giving up (default is 3). |
| **Enable Device Grouping** | boolean | (v0.2.0+) Group entities into logical sub-devices for better organization (default: enabled). |
| **Protocol Type** | string | (Optional) Communication protocol: `lxp` for LuxPower dongles (default), `default` for standard Modbus RTU. |

> [!TIP]
> ### Protocol Type Configuration
>
> The **Protocol Type** setting allows you to choose between two communication modes:
>
> * **LuxPower (LXP Protocol)** (Default): Use this for LuxPower WiFi dongles and inverters that use the proprietary LuxPower communication protocol. This is the standard mode that has been tested extensively.
> * **Standard Modbus RTU**: Use this for direct Modbus communication following the official Modbus RTU protocol specification. This mode sends standard Modbus packets without dongle-specific encapsulation and is useful for:
>   - Direct serial/RS485 connections to the inverter
>   - Third-party Modbus gateways or converters
>   - Custom hardware setups
>   - Troubleshooting communication issues
>
> **When to use Standard Modbus RTU:**
> - You're connecting directly via RS485/serial without a LuxPower dongle
> - You're using a generic Modbus-to-WiFi/Ethernet converter
> - The LXP protocol is not working with your setup
> - You want to follow strict Modbus RTU specifications
>
> If you're unsure, start with the default **LXP Protocol** setting, as it's designed specifically for LuxPower systems.

> [!WARNING]
> ### Important Note on Read-Only Mode (Available since v0.1.5)
>
> The **Read-Only Mode** setting fundamentally changes the type of entities this integration creates for inverter controls.
>
> * **If `Read-Only Mode` is OFF (default):** The integration will create interactive entities like `number`, `switch`, and `select` to allow you to control your inverter.
> * **If `Read-Only Mode` is ON:** All of those control entities will instead be created as read-only `sensor` entities. You will be able to see the current settings, but you will not be able to change them.
>
> **Please choose this setting carefully during the initial setup.** Changing this option later by reconfiguring the integration will **delete** your existing control entities and create new `sensor` entities (or vice-versa). This will break any dashboards, automations, or history that relied on the old entities.

> [!TIP]
> ### Register Block Size Configuration
>
> The **Register Block Size** option allows you to adjust how the integration communicates with your inverter:
>
> * **125** (Default): Use for most modern inverter firmware versions for optimal performance.
> * **40**: Use if you have an older inverter firmware that doesn't support larger register block reads.
>
> If you experience communication errors with the default setting, try switching to the smaller block size.

> [!TIP]
> ### Reconnection Logic & Reliability
>
> This integration includes advanced reconnection logic to handle temporary network or inverter communication issues:
>
> * **Connection Retry Attempts**: Configure how many immediate retry attempts the integration makes when connection fails (default: 3).
> * **Automatic Recovery**: If connection is lost, the integration will temporarily use cached data while attempting to reconnect.
> * **Adaptive Polling**: During recovery mode, the polling frequency automatically adjusts to find the optimal balance between quick reconnection and network load.
> * **Graceful Degradation**: Entities remain available with last known good values during brief connection interruptions.
>
> These features ensure that temporary network issues don't cause your automations to fail or entities to show as unavailable.

> [!IMPORTANT]
> ### Device Grouping (Available since v0.2.0)
>
> Starting with version 0.2.0, this integration introduces **Device Grouping** to better organize the 250+ entities created by your inverter:
>
> * **PV Group** (25 entities): Solar panel monitoring and MPPT controls
> * **Grid Group** (42 entities): Utility grid connection and import/export data
> * **EPS Group** (18 entities): Emergency Power Supply / backup load outputs
> * **Generator Group** (12 entities): Backup generator monitoring and controls
> * **Battery Group** (62 entities): BMS data, cell voltages, temperatures, and battery controls
> * **Temperatures & Diagnostics** (12 entities): Temperature sensors, fault codes, and diagnostic data
> * **Settings & Schedules** (56 entities): Configuration settings, timing schedules, and power management
>
> **Configuration Options:**
> * **Enabled by default** for new installations - provides much better organization in Home Assistant
> * **Optional** - can be disabled in integration settings if you prefer all entities under one device
> * **Configurable** - can be toggled on/off at any time through the integration options
>
> **For Existing Users:** When updating to v0.2.0+, device grouping will be automatically enabled. If you prefer the old single-device layout, you can disable it in the integration settings.

## Entities

This integration creates a wide range of entities to give you full visibility and control over your inverter.

#### Sensors
Provides detailed operational data, including:
* Inverter State (Text and Code)
* Battery SOC & SOH
* PV Power (Total and per-string)
* Grid Import/Export Power
* Load Power
* Battery Charge/Discharge Power
* Daily & Total Energy Statistics (PV, Grid, Load, etc.)
* Temperatures (Battery, Radiator, etc.)
* Voltages, Currents, and Frequencies for Grid, EPS, and Battery.
* Calculated Load Percentage

#### Numbers
Allows control over inverter settings:
* Charge & Discharge Currents
* AC Charge Power Limit
* End of Discharge (EOD) SOC
* Battery Stop Charging Voltage/SOC

#### Switches
Enable or disable key features on the fly:
* AC Charging Enable
* Feed-In Grid Enable
* Forced Discharge Enable
* Eco & Green Modes

#### Selects
Choose from predefined operational modes:
* AC Charge Type (by Time, SOC, etc.)
* Output Priority (Battery first, PV first, etc.)

#### Time
Set schedules for timed operations:
* AC Charging Start & End Times
* Peak Shaving Start & End Times

## Blueprints

This integration includes blueprints to help you get started with powerful automations.

### How to Import Blueprints

There are two ways to get the blueprints into your Home Assistant instance.

**Method 1: Direct Import Button (Easiest)**

Click the "Import Blueprint" button under the blueprint you wish to use. This will take you to your Home Assistant instance to complete the import.

**Method 2: Manual Import**

1.  In Home Assistant, go to **Settings** > **Automations & Scenes**.
2.  Select the **Blueprints** tab.
3.  Click the **Import Blueprint** button in the bottom right.
4.  Paste the "Manual Import URL" for the blueprint you want.
5.  Click **"Preview Blueprint"** and then **"Import Blueprint"**.

---

### Available Blueprints

#### Force Charge for a Specific Duration
This script blueprint allows you to temporarily force the inverter to charge from the grid for a set amount of time. It saves your existing settings, applies the temporary charge schedule, and restores your settings when finished.

[![Open your Home Assistant instance and import this blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fant0nkr%2Fluxpower-ha-integration%2Fmain%2Fblueprints%2Fscript%2Flxp_force_charge.yaml)
> Manual Import URL: `https://raw.githubusercontent.com/ant0nkr/luxpower-ha-integration/main/blueprints/script/lxp_force_charge.yaml`

#### Force Charge to a Target SOC
This automation blueprint allows you to charge your inverter's battery from the AC grid until it reaches a specific State of Charge (SOC) percentage. It automatically saves a snapshot of your current inverter settings before starting and perfectly restores them once the target SOC is met.

[![Open your Home-Assistant instance and import this blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fant0nkr%2Fluxpower-ha-integration%2Fmain%2Fblueprints%2Fautomation%2Flxp_charge_automation.yaml)
> Manual Import URL: `https://raw.githubusercontent.com/ant0nkr/luxpower-ha-integration/main/blueprints/automation/lxp_charge_automation.yaml`

## Debugging

If you are having issues, you can enable debug logging by adding the following to your `configuration.yaml` file:

```yaml
logger:
  default: info
  logs:
    custom_components.lxp_modbus: debug
