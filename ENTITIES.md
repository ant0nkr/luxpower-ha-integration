# Entities Reference

Complete reference of all entities created by the **LuxPower Modbus** integration.

## Summary

| Platform | Count | Notes |
| :--- | :---: | :--- |
| [Sensors](#sensors-203) | 203 | Operational, energy, state, and diagnostic sensors |
| [Battery Sensors](#battery-sensors-18-per-battery) | 18 × batteries | Created per connected LuxPower battery when Battery Entities is enabled |
| [Binary Sensors](#binary-sensors-5) | 5 | Grid connectivity and BMS status flags |
| [Numbers](#numbers-338) | 338 | Writable numeric settings (exposed as `sensor` in Read-Only Mode) |
| [Switches](#switches-30) | 30 | Writable feature toggles (exposed as `sensor` in Read-Only Mode) |
| [Selects](#selects-17) | 17 | Writable mode selectors (exposed as `sensor` in Read-Only Mode) |
| [Buttons](#buttons-4) | 4 | Maintenance and reset actions (omitted in Read-Only Mode) |
| [Time](#time-144) | 144 | Charge/discharge and peak-shaving schedules (exposed as `sensor` in Read-Only Mode) |
| **Total** | **741 + (18 × batteries)** | **759** entity definitions in total |

> [!NOTE]
> * **Device Group:** When *Enable Device Grouping* is enabled, entities are placed under `PV`, `Grid`, `EPS`, `Generator`, or `Battery` sub-devices; `Inverter` indicates the main device.
> * **Primary Only:** Entities marked `Yes` are only created on standalone or primary (master) inverters in parallel configurations.
> * **Register(s):** `input:<reg>` = input register, `hold:<reg>` = hold register, `battery:<reg>` = battery BMS register (`5000+` range), `calculated` = derived from listed registers.

## Sensors (203)

| Name | Device Group | Unit | Device Class | State Class | Register(s) | Primary Only | Enabled |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| Load Percentage | Inverter | % | power_factor | measurement | `calculated` (0, 170, 24) | No | Yes |
| Energy Flow | Inverter | W | power | measurement | `calculated` (11, 27, 186, 187, 203, 204, 7, 8, 9, 220, 221, 222) | No | Yes |
| Battery Flow | Battery | W | power | measurement | `calculated` (10, 11) | No | Yes |
| Grid Flow | Grid | W | power | measurement | `calculated` (26, 27) | No | Yes |
| Home Consumption Today Calculated | Inverter | kWh | energy | total_increasing | `calculated` (37, 31, 32, 36, 35) | No | Yes |
| Home Consumption Total Calculated | Inverter | kWh | energy | total_increasing | `calculated` (58, 59, 46, 47, 48, 49, 56, 57, 54, 55) | No | Yes |
| Inverter State | Inverter | — | — | — | `input:0` | No | Yes |
| Inverter State Code | Inverter | — | — | — | `input:0` | No | Yes |
| AC Input Type | Inverter | — | — | — | `input:77` | No | Yes |
| PV1 Voltage | PV | V | voltage | measurement | `input:1` | No | Yes |
| PV1 Power | PV | W | power | measurement | `input:7` | No | Yes |
| PV1 Current | PV | A | current | measurement | `calculated` (7, 1) | No | Yes |
| PV2 Voltage | PV | V | voltage | measurement | `input:2` | No | Yes |
| PV2 Power | PV | W | power | measurement | `input:8` | No | Yes |
| PV2 Current | PV | A | current | measurement | `calculated` (8, 2) | No | Yes |
| PV3 Voltage | PV | V | voltage | measurement | `input:3` | No | Yes |
| PV3 Power | PV | W | power | measurement | `input:9` | No | Yes |
| PV3 Current | PV | A | current | measurement | `calculated` (9, 3) | No | Yes |
| PV4 Voltage | PV | V | voltage | measurement | `input:217` | No | Yes |
| PV4 Power | PV | W | power | measurement | `input:220` | No | Yes |
| PV4 Current | PV | A | current | measurement | `calculated` (220, 217) | No | Yes |
| PV5 Voltage | PV | V | voltage | measurement | `input:218` | No | Yes |
| PV5 Power | PV | W | power | measurement | `input:221` | No | Yes |
| PV5 Current | PV | A | current | measurement | `calculated` (221, 218) | No | Yes |
| PV6 Voltage | PV | V | voltage | measurement | `input:219` | No | Yes |
| PV6 Power | PV | W | power | measurement | `input:222` | No | Yes |
| PV6 Current | PV | A | current | measurement | `calculated` (222, 219) | No | Yes |
| PV Power | PV | W | power | measurement | `calculated` (7, 8, 9, 220, 221, 222) | No | Yes |
| Battery Voltage | Battery | V | voltage | measurement | `input:4` | Yes | Yes |
| Battery SOC | Battery | % | battery | measurement | `input:5` | Yes | Yes |
| Battery SOH | Battery | % | — | measurement | `input:5` | Yes | Yes |
| Days since SOC >= 99 | Battery | d | duration | measurement | `hold:235` | Yes | Yes |
| Bootloader Version | Inverter | — | — | — | `hold:244` | Yes | Yes |
| Bootloader Update Flag | Inverter | — | — | — | `hold:244` | Yes | Yes |
| Inverter Time | Inverter | — | timestamp | — | `calculated` (12, 13, 14) | No | No |
| Battery Charge Power | Battery | W | power | measurement | `input:10` | No | Yes |
| Battery Discharge Power | Battery | W | power | measurement | `input:11` | No | Yes |
| Battery Temperature | Battery | °C | temperature | measurement | `input:67` | Yes | Yes |
| Grid Voltage | Grid | V | voltage | measurement | `input:12` | No | Yes |
| Grid Voltage S-Phase | Grid | V | voltage | measurement | `input:13` | No | Yes |
| Grid Voltage T-Phase | Grid | V | voltage | measurement | `input:14` | No | Yes |
| Grid Frequency | Grid | Hz | frequency | measurement | `input:15` | No | Yes |
| Grid Voltage L1N | Grid | V | voltage | measurement | `input:193` | No | Yes |
| Grid Voltage L2N | Grid | V | voltage | measurement | `input:194` | No | Yes |
| Inverter Power | Inverter | W | power | measurement | `input:16` | No | Yes |
| Inverter Power L1N | Inverter | W | power | measurement | `input:197` | No | Yes |
| Inverter Power L2N | Inverter | W | power | measurement | `input:198` | No | Yes |
| Inverter Current | Inverter | A | current | measurement | `input:18` | No | Yes |
| AC Charging Rectification Power | Inverter | W | power | measurement | `input:17` | No | Yes |
| AC Rectification Power L1N | Inverter | W | power | measurement | `input:199` | No | Yes |
| AC Rectification Power L2N | Inverter | W | power | measurement | `input:200` | No | Yes |
| AC Couple Power | AC Coupling | W | power | measurement | `input:153` | No | Yes |
| AC Couple Power S-Phase | AC Coupling | W | power | measurement | `input:206` | No | Yes |
| AC Couple Power T-Phase | AC Coupling | W | power | measurement | `input:207` | No | Yes |
| Power Factor | Inverter | % | power_factor | measurement | `input:19` | No | Yes |
| Reactive Power | Inverter | var | reactive_power | measurement | `input:139` | No | Yes |
| Power to Grid | Grid | W | power | measurement | `input:26` | No | Yes |
| Power to Grid L1N | Grid | W | power | measurement | `input:201` | No | Yes |
| Power to Grid L2N | Grid | W | power | measurement | `input:202` | No | Yes |
| Power from Grid | Grid | W | power | measurement | `input:27` | No | Yes |
| Power from Grid L1N | Grid | W | power | measurement | `input:203` | No | Yes |
| Power from Grid L2N | Grid | W | power | measurement | `input:204` | No | Yes |
| Load Power | Inverter | W | power | measurement | `input:170` | No | Yes |
| On-Grid Load Power | Grid | W | power | measurement | `input:114` | No | Yes |
| Smart Load Power | Inverter | W | power | measurement | `input:232` | No | Yes |
| EPS Voltage | EPS | V | voltage | measurement | `input:20` | No | Yes |
| EPS Voltage L1N | EPS | V | voltage | measurement | `input:127` | No | Yes |
| EPS Voltage L2N | EPS | V | voltage | measurement | `input:128` | No | Yes |
| EPS Voltage S-Phase | EPS | V | voltage | measurement | `input:21` | No | Yes |
| EPS Voltage T-Phase | EPS | V | voltage | measurement | `input:22` | No | Yes |
| EPS Frequency | EPS | Hz | frequency | measurement | `input:23` | No | Yes |
| EPS Power | EPS | W | power | measurement | `input:24` | No | Yes |
| EPS Power L1N | EPS | W | power | measurement | `input:129` | No | Yes |
| EPS Power L2N | EPS | W | power | measurement | `input:130` | No | Yes |
| EPS Apparent Power | EPS | VA | apparent_power | measurement | `input:25` | No | Yes |
| EPS Apparent Power L1N | EPS | VA | apparent_power | measurement | `input:131` | No | Yes |
| EPS Apparent Power L2N | EPS | VA | apparent_power | measurement | `input:132` | No | Yes |
| PV1 Energy Today | PV | kWh | energy | total_increasing | `input:28` | No | Yes |
| PV2 Energy Today | PV | kWh | energy | total_increasing | `input:29` | No | Yes |
| PV3 Energy Today | PV | kWh | energy | total_increasing | `input:30` | No | Yes |
| PV4 Energy Today | PV | kWh | energy | total_increasing | `input:223` | No | Yes |
| PV5 Energy Today | PV | kWh | energy | total_increasing | `input:226` | No | Yes |
| PV6 Energy Today | PV | kWh | energy | total_increasing | `input:229` | No | Yes |
| PV Energy Today | PV | kWh | energy | total_increasing | `calculated` (28, 29, 30, 223, 226, 229) | No | Yes |
| Inverter Energy Today | Inverter | kWh | energy | total_increasing | `input:31` | No | Yes |
| AC Charge Energy Today | Inverter | kWh | energy | total_increasing | `input:32` | No | Yes |
| Charge Energy Today | Inverter | kWh | energy | total_increasing | `input:33` | No | Yes |
| Discharge Energy Today | Inverter | kWh | energy | total_increasing | `input:34` | No | Yes |
| EPS Energy Today | EPS | kWh | energy | total_increasing | `input:35` | No | Yes |
| EPS Energy Today L1N | EPS | kWh | energy | total_increasing | `input:133` | No | Yes |
| EPS Energy Today L2N | EPS | kWh | energy | total_increasing | `input:134` | No | Yes |
| Energy to Grid Today | Grid | kWh | energy | total_increasing | `input:36` | No | Yes |
| Energy from Grid Today | Grid | kWh | energy | total_increasing | `input:37` | No | Yes |
| Generator Energy Today | Generator | kWh | energy | total_increasing | `input:124` | No | Yes |
| Load Consumption Today | Inverter | kWh | energy | total_increasing | `input:171` | No | Yes |
| Internal Temperature | Inverter | °C | temperature | measurement | `input:64` | No | Yes |
| Internal Temperature 2 | Inverter | °C | temperature | measurement | `input:214` | No | Yes |
| Radiator Temperature | Inverter | °C | temperature | measurement | `input:65` | No | Yes |
| Radiator Temperature 2 | Inverter | °C | temperature | measurement | `input:66` | No | Yes |
| Radiator Temperature 3 | Inverter | °C | temperature | measurement | `input:215` | No | Yes |
| Radiator Temperature 4 | Inverter | °C | temperature | measurement | `input:216` | No | Yes |
| Generator Voltage | Generator | V | voltage | measurement | `input:121` | No | Yes |
| Generator Voltage L1N | Generator | V | voltage | measurement | `input:195` | No | Yes |
| Generator Voltage L2N | Generator | V | voltage | measurement | `input:196` | No | Yes |
| Generator Frequency | Generator | Hz | frequency | measurement | `input:122` | No | Yes |
| Generator Power | Generator | W | power | measurement | `input:123` | No | Yes |
| Remaining One-Click Charge Time | Inverter | min | duration | measurement | `input:210` | No | Yes |
| Bus 1 Voltage | Inverter | V | voltage | measurement | `input:38` | No | Yes |
| Bus 2 Voltage | Inverter | V | voltage | measurement | `input:39` | No | Yes |
| Half Bus Voltage | Inverter | V | voltage | measurement | `input:120` | No | Yes |
| AFCI Current CH1 | Inverter | mA | — | measurement | `input:140` | No | No |
| AFCI Current CH2 | Inverter | mA | — | measurement | `input:141` | No | No |
| AFCI Current CH3 | Inverter | mA | — | measurement | `input:142` | No | No |
| AFCI Current CH4 | Inverter | mA | — | measurement | `input:143` | No | No |
| AFCI Flag | Inverter | — | — | — | `input:144` | No | No |
| AFCI Arc CH1 | Inverter | — | — | — | `input:145` | No | No |
| AFCI Arc CH2 | Inverter | — | — | — | `input:146` | No | No |
| AFCI Arc CH3 | Inverter | — | — | — | `input:147` | No | No |
| AFCI Arc CH4 | Inverter | — | — | — | `input:148` | No | No |
| AFCI Max Arc CH1 | Inverter | — | — | — | `input:149` | No | No |
| AFCI Max Arc CH2 | Inverter | — | — | — | `input:150` | No | No |
| AFCI Max Arc CH3 | Inverter | — | — | — | `input:151` | No | No |
| AFCI Max Arc CH4 | Inverter | — | — | — | `input:152` | No | No |
| BMS Max Charge Current | Battery | A | current | measurement | `input:81` | Yes | Yes |
| BMS Max Discharge Current | Battery | A | current | measurement | `input:82` | Yes | Yes |
| BMS Charge Voltage Reference | Battery | V | voltage | measurement | `input:83` | Yes | Yes |
| BMS Discharge Cut-off Voltage | Battery | V | voltage | measurement | `input:84` | Yes | Yes |
| Battery Parallel Number | Battery | — | — | — | `input:96` | Yes | Yes |
| Battery Capacity | Battery | Ah | — | measurement | `input:97` | Yes | Yes |
| BMS Battery Current | Battery | A | current | measurement | `input:98` | Yes | Yes |
| BMS Fault Code | Battery | — | — | — | `input:99` | Yes | Yes |
| BMS Warning Code | Battery | — | — | — | `input:100` | Yes | Yes |
| BMS Max Cell Voltage | Battery | V | voltage | measurement | `input:101` | Yes | Yes |
| BMS Min Cell Voltage | Battery | V | voltage | measurement | `input:102` | Yes | Yes |
| BMS Cell Difference | Battery | V | voltage | measurement | `calculated` (102, 101) | Yes | Yes |
| BMS Max Cell Temperature | Battery | °C | temperature | measurement | `input:103` | Yes | Yes |
| BMS Min Cell Temperature | Battery | °C | temperature | measurement | `input:104` | Yes | Yes |
| BMS Cycle Count | Battery | cycles | — | total_increasing | `input:106` | Yes | Yes |
| BMS Battery Status 0 | Battery | — | — | — | `input:85` | No | Yes |
| BMS Battery Status 1 | Battery | — | — | — | `input:86` | No | Yes |
| BMS Battery Status 2 | Battery | — | — | — | `input:87` | No | Yes |
| BMS Battery Status 3 | Battery | — | — | — | `input:88` | No | Yes |
| BMS Battery Status 4 | Battery | — | — | — | `input:89` | No | Yes |
| BMS Battery Status 5 | Battery | — | — | — | `input:90` | No | Yes |
| BMS Battery Status 6 | Battery | — | — | — | `input:91` | No | Yes |
| BMS Battery Status 7 | Battery | — | — | — | `input:92` | No | Yes |
| BMS Battery Status 8 | Battery | — | — | — | `input:93` | No | Yes |
| BMS Battery Status 9 | Battery | — | — | — | `input:94` | No | Yes |
| BMS Battery Status Aggregated | Battery | — | — | — | `input:95` | No | Yes |
| Inverter Battery Voltage Sample | Battery | V | voltage | measurement | `input:107` | Yes | Yes |
| Internal Fault Code | Inverter | — | — | — | `input:6` | No | Yes |
| Active Fault (Code) | Inverter | — | — | — | `calculated` (60, 61) | No | Yes |
| Active Fault (Text) | Inverter | — | — | — | `calculated` (60, 61) | No | Yes |
| Active Warning (Code) | Inverter | — | — | — | `calculated` (62, 63) | No | Yes |
| Active Warning (Text) | Inverter | — | — | — | `calculated` (62, 63) | No | Yes |
| Parallel Role | Inverter | — | — | — | `input:113` | No | Yes |
| Parallel Phase | Grid | — | — | — | `input:113` | No | Yes |
| Phase Sequence | Grid | — | — | — | `input:113` | No | Yes |
| Parallel Inverter Number | Inverter | — | — | — | `input:113` | No | Yes |
| Total Running Time | Inverter | s | duration | total_increasing | `calculated` (69, 70) | No | Yes |
| PV1 Energy Total | PV | kWh | energy | total_increasing | `calculated` (40, 41) | No | Yes |
| PV2 Energy Total | PV | kWh | energy | total_increasing | `calculated` (42, 43) | No | Yes |
| PV3 Energy Total | PV | kWh | energy | total_increasing | `calculated` (44, 45) | No | Yes |
| PV4 Energy Total | PV | kWh | energy | total_increasing | `calculated` (224, 225) | No | Yes |
| PV5 Energy Total | PV | kWh | energy | total_increasing | `calculated` (227, 228) | No | Yes |
| PV6 Energy Total | PV | kWh | energy | total_increasing | `calculated` (230, 231) | No | Yes |
| PV Energy Total | PV | kWh | energy | total_increasing | `calculated` (40, 41, 42, 43, 44, 45, 224, 225, 227, 228, 230, 231) | No | Yes |
| Inverter Energy Total | Inverter | kWh | energy | total_increasing | `calculated` (46, 47) | No | Yes |
| AC Charge Energy Total | Inverter | kWh | energy | total_increasing | `calculated` (48, 49) | No | Yes |
| Charge Energy Total | Inverter | kWh | energy | total_increasing | `calculated` (50, 51) | No | Yes |
| Discharge Energy Total | Inverter | kWh | energy | total_increasing | `calculated` (52, 53) | No | Yes |
| EPS Energy Total | EPS | kWh | energy | total_increasing | `calculated` (54, 55) | No | Yes |
| EPS Energy Total L1N | EPS | kWh | energy | total_increasing | `calculated` (135, 136) | No | Yes |
| EPS Energy Total L2N | EPS | kWh | energy | total_increasing | `calculated` (137, 138) | No | Yes |
| Energy to Grid Total | Grid | kWh | energy | total_increasing | `calculated` (56, 57) | No | Yes |
| Energy from Grid Total | Grid | kWh | energy | total_increasing | `calculated` (58, 59) | No | Yes |
| Generator Energy Total | Generator | kWh | energy | total_increasing | `calculated` (125, 126) | No | Yes |
| Load Consumption Total | Inverter | kWh | energy | total_increasing | `calculated` (172, 173) | No | Yes |
| Inverter Power S-Phase | Grid | W | power | measurement | `input:180` | No | Yes |
| Inverter Power T-Phase | Grid | W | power | measurement | `input:181` | No | Yes |
| AC Rectification Power S-Phase | Grid | W | power | measurement | `input:182` | No | Yes |
| AC Rectification Power T-Phase | Grid | W | power | measurement | `input:183` | No | Yes |
| Power to Grid S-Phase | Grid | W | power | measurement | `input:184` | No | Yes |
| Power to Grid T-Phase | Grid | W | power | measurement | `input:185` | No | Yes |
| Power from Grid S-Phase | Grid | W | power | measurement | `input:186` | No | Yes |
| Power from Grid T-Phase | Grid | W | power | measurement | `input:187` | No | Yes |
| Generator Power S-Phase | Generator | W | power | measurement | `input:188` | No | Yes |
| Generator Power T-Phase | Generator | W | power | measurement | `input:189` | No | Yes |
| Inverter Current S-Phase | Grid | A | current | measurement | `input:190` | No | Yes |
| Inverter Current T-Phase | Grid | A | current | measurement | `input:191` | No | Yes |
| Power Factor S-Phase | Grid | % | power_factor | measurement | `input:192` | No | Yes |
| Power Factor T-Phase | Grid | % | power_factor | measurement | `input:205` | No | Yes |
| On-Grid Load Power S-Phase | Grid | W | power | measurement | `input:208` | No | Yes |
| On-Grid Load Power T-Phase | Grid | W | power | measurement | `input:209` | No | Yes |
| Battery Type and Brand | Battery | — | — | — | `input:80` | No | Yes |
| BMS Firmware Update State | Battery | — | — | — | `input:105` | No | Yes |
| DIP Switch State | Inverter | — | — | — | `input:174` | No | Yes |
| Exception Reason 1 | Inverter | — | — | — | `input:176` | No | Yes |
| Exception Reason 2 | Inverter | — | — | — | `input:177` | No | Yes |
| Charge Discharge Disable Reason | Battery | — | — | — | `input:178` | No | Yes |
| Auto Test Status | Inverter | — | — | — | `input:71` | No | Yes |
| Input Data Read At | Inverter | — | timestamp | — | `meta:input_read_at` | No | No |
| Battery Data Read At | Battery | — | timestamp | — | `meta:battery_read_at` | No | No |

## Battery Sensors (18 per battery)

| Name | Unit | Device Class | State Class | Register(s) | Enabled |
| :--- | :--- | :--- | :--- | :--- | :---: |
| Capacity | Ah | — | — | `battery:3` | Yes |
| Max Charge Current | A | current | measurement | `battery:5` | Yes |
| Max Discharge Current | A | current | measurement | `battery:6` | Yes |
| Voltage | V | voltage | measurement | `battery:8` | Yes |
| Current | A | current | measurement | `battery:9` | Yes |
| SOC | % | battery | measurement | `battery:10` | Yes |
| SOH | % | — | measurement | `battery:10` | Yes |
| Cycle Count | cycles | — | total_increasing | `battery:11` | Yes |
| Max Cell Temperature | °C | temperature | measurement | `battery:12` | Yes |
| Min Cell Temperature | °C | temperature | measurement | `battery:13` | Yes |
| Max Cell Voltage | V | voltage | measurement | `battery:14` | Yes |
| Min Cell Voltage | V | voltage | measurement | `battery:15` | Yes |
| Cell Difference | V | voltage | measurement | `battery_calculated` (14, 15) | Yes |
| Cell with Min Temp | — | — | — | `battery:16` | Yes |
| Cell with Max Temp | — | — | — | `battery:16` | Yes |
| Cell with Min Voltage | — | — | — | `battery:17` | Yes |
| Cell with Max Voltage | — | — | — | `battery:17` | Yes |
| Firmware Version | — | — | — | `battery:18` | Yes |

## Binary Sensors (5)

| Name | Device Group | Device Class | Register(s) | Primary Only | Enabled |
| :--- | :--- | :--- | :--- | :---: | :---: |
| Grid Connected | Grid | connectivity | `calculated` (15) | No | Yes |
| BMS Charge Allowed | Battery | — | `input:95` | Yes | Yes |
| BMS Discharge Allowed | Battery | — | `input:95` | Yes | Yes |
| BMS Request Charge | Battery | problem | `input:95` | Yes | Yes |
| BMS Request Full Charge | Battery | problem | `input:95` | Yes | Yes |

## Numbers (338)

| Name | Device Group | Unit | Range | Step | Register | Notes | Primary Only | Enabled |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- | :---: | :---: |
| Modbus Address | Inverter | — | 0–150 | 1 | `hold:15` | — | Yes | Yes |
| Grid Connect Time | Grid | s | 30–600 | 1 | `hold:23` | — | Yes | Yes |
| Grid Reconnect Time | Grid | s | 0–900 | 1 | `hold:24` | — | Yes | Yes |
| Grid Voltage Low Limit | Grid | V | 0–6553.5 | 0.1 | `hold:25` | — | Yes | Yes |
| Grid Voltage High Limit | Grid | V | 0–6553.5 | 0.1 | `hold:26` | — | Yes | Yes |
| Grid Frequency Low Limit | Grid | Hz | 0–655.35 | 0.01 | `hold:27` | — | Yes | Yes |
| Grid Frequency High Limit | Grid | Hz | 0–655.35 | 0.01 | `hold:28` | — | Yes | Yes |
| Max Grid Input Power | Grid | kW | 0–65535 | 0.1 | `hold:176` | — | No | Yes |
| Start Discharge P_import | Battery | W | 0–65535 | 1 | `hold:116` | — | No | Yes |
| External CT Power Offset | Inverter | W | -32768–32767 | 1 | `hold:119` | — | No | Yes |
| Active Power Percent | Inverter | % | 0–100 | 1 | `hold:60` | — | Yes | Yes |
| Power Soft Start Slope | Inverter | %/min | 1–4000 | 1 | `hold:63` | — | Yes | Yes |
| Max Backflow Power | Inverter | % | 0–100 | 1 | `hold:103` | — | Yes | Yes |
| Charge Current | Battery | A | 0–500 | 1 | `hold:101` | — | Yes | Yes |
| Discharge Current | Battery | A | 0–500 | 1 | `hold:102` | — | Yes | Yes |
| AC Charge Power | Inverter | % | 0–100 | 1 | `hold:66` | — | Yes | Yes |
| AC Charge Power (kW) | Inverter | % | 0–100 | 1 | `hold:66` | Max based on rated power | Yes | Yes |
| AC Charge SOC Limit | Battery | % | 0–100 | 1 | `hold:67` | — | Yes | Yes |
| AC Charge Start Voltage | Battery | V | 38.5–52 | 0.1 | `hold:158` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge End Voltage | Battery | V | 48–59 | 0.1 | `hold:159` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Start SOC | Battery | % | 0–90 | 1 | `hold:160` | — | Yes | Yes |
| AC Charge End SOC | Battery | % | 0–100 | 1 | `hold:161` | — | Yes | Yes |
| AC Charge Current from Grid | Battery | A | 0–140 | 1 | `hold:168` | — | Yes | Yes |
| On-Grid Cut-Off SOC | Battery | % | 0–100 | 1 | `hold:105` | — | No | Yes |
| On-Grid Cut-Off Voltage | Grid | V | 40–56 | 0.1 | `hold:169` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Battery Stop Charging SOC | Battery | % | 10–101 | 1 | `hold:227` | — | Yes | Yes |
| Battery Stop Charging Voltage | Battery | V | 40–59.5 | 0.1 | `hold:228` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Quick Charge Time | Battery | min | 0–1440 | 1 | `hold:234` | — | No | Yes |
| Off-Grid Cut-Off SOC | Battery | % | 0–100 | 1 | `hold:125` | — | Yes | Yes |
| Unmatched Battery Capacity | Battery | Ah | 0–10000 | 1 | `hold:147` | — | Yes | Yes |
| Unmatched Battery Nominal Voltage | Battery | V | 40–59 | 0.1 | `hold:148` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Float Charge Voltage | Battery | V | 50–56 | 0.1 | `hold:144` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Equalization Interval | Inverter | Days | 0–365 | 1 | `hold:150` | — | Yes | Yes |
| Equalization Time | Inverter | Hours | 0–24 | 1 | `hold:151` | — | Yes | Yes |
| Battery Low Voltage Alarm | Battery | V | 40–50 | 0.1 | `hold:162` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Battery Low Voltage Recovery | Battery | V | 42–52 | 0.1 | `hold:163` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Battery Low SOC Alarm | Battery | % | 0–90 | 1 | `hold:164` | — | Yes | Yes |
| Battery Low SOC Recovery | Battery | % | 0–100 | 1 | `hold:165` | — | Yes | Yes |
| Battery Calibration Period | Battery | d | 0–255 | 1 | `hold:235` | — | Yes | Yes |
| Generator Rated Power | Generator | W | 0–65535 | 1 | `hold:177` | — | Yes | Yes |
| Generator Charge Start Voltage | Battery | V | 38.4–52 | 0.1 | `hold:194` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Generator Charge End Voltage | Battery | V | 48–59 | 0.1 | `hold:195` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Generator Charge Start SOC | Battery | % | 0–90 | 1 | `hold:196` | — | Yes | Yes |
| Generator Charge End SOC | Battery | % | 20–100 | 1 | `hold:197` | — | Yes | Yes |
| Max Generator Charge Current | Battery | A | 0–4000 | 1 | `hold:198` | — | Yes | Yes |
| Grid Peak Shaving Power | Grid | kW | 0–25.5 | 0.1 | `hold:206` | — | Yes | Yes |
| Grid Peak Shaving SOC | Battery | % | 0–100 | 1 | `hold:207` | — | Yes | Yes |
| LCD Password | Inverter | — | 0–65535 | 1 | `hold:225` | — | Yes | Yes |
| Battery SOC Hysteresis | Battery | % | 0–100 | 1 | `hold:253` | — | Yes | Yes |
| Battery Voltage Hysteresis | Battery | V | 2–10 | 0.1 | `hold:254` | — | Yes | Yes |
| BUS Overvoltage Alarm Point | Inverter | V | 550–595 | 1 | `hold:260` | — | Yes | Yes |
| Discharge Recovery SOC Threshold | Battery | % | 5–100 | 1 | `hold:261` | — | Yes | Yes |
| Discharge Recovery Volt Threshold | Inverter | V | 1–20 | 0.1 | `hold:261` | — | Yes | Yes |
| WattNode CT1 Amps | Inverter | A | 0–6000 | 1 | `hold:248` | — | Yes | Yes |
| WattNode CT2 Amps | Inverter | A | 0–6000 | 1 | `hold:249` | — | Yes | Yes |
| WattNode CT3 Amps | Inverter | A | 0–6000 | 1 | `hold:250` | — | Yes | Yes |
| NEC 120% Bus Bar Limit | Inverter | A | 5–80 | 1 | `hold:252` | — | Yes | Yes |
| NPE Threshold | Inverter | V | 0–6553.5 | 0.1 | `hold:242` | — | Yes | Yes |
| Flash Size | Inverter | KB | 0–65535 | 1 | `hold:245` | — | Yes | Yes |
| Charge Power Rate (Legacy) | Battery | % | 0–100 | 1 | `hold:64` | — | Yes | Yes |
| Discharge Power Rate (Legacy) | Battery | % | 0–100 | 1 | `hold:65` | — | Yes | Yes |
| System Charge Power Rate | Battery | % | 0–100 | 0.1 | `hold:138` | — | Yes | Yes |
| System Discharge Power Rate | Battery | % | 0–100 | 0.1 | `hold:139` | — | Yes | Yes |
| AC Charge Power Rate (Precise) | Battery | % | 0–100 | 0.1 | `hold:140` | — | Yes | Yes |
| Charge First Power Rate (Precise) | Battery | % | 0–100 | 0.1 | `hold:141` | — | Yes | Yes |
| Forced Discharge Power Rate (Precise) | Battery | % | 0–100 | 0.1 | `hold:142` | — | Yes | Yes |
| Active Power Percent (Precise) | Inverter | % | 0–100 | 0.1 | `hold:143` | — | Yes | Yes |
| Reactive Power Percent | Grid | % | 0–60 | 1 | `hold:61` | — | Yes | Yes |
| Power Factor Command | Grid | — | 0.8–1 | 0.001 | `hold:62` | — | Yes | Yes |
| Charge First Power | Battery | % | 0–100 | 1 | `hold:74` | — | Yes | Yes |
| Charge First SOC Limit | Battery | % | 0–101 | 1 | `hold:75` | — | Yes | Yes |
| Charge First End Voltage | Battery | V | 48–59.5 | 0.1 | `hold:201` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power | Battery | % | 0–100 | 1 | `hold:82` | — | Yes | Yes |
| Forced Discharge Power (kW) | Battery | % | 0–100 | 1 | `hold:82` | Max based on rated power | Yes | Yes |
| Forced Discharge SOC Limit | Battery | % | 0–100 | 1 | `hold:83` | — | Yes | Yes |
| Forced Discharge End Voltage | Battery | V | 40–56 | 0.1 | `hold:202` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Grid Voltage L1 Low | Grid | V | 0–6553.5 | 0.1 | `hold:29` | — | Yes | Yes |
| Grid Voltage L1 High | Grid | V | 0–6553.5 | 0.1 | `hold:30` | — | Yes | Yes |
| Grid Voltage L1 Low Time | Grid | cycles | 0–65535 | 1 | `hold:31` | — | Yes | Yes |
| Grid Voltage L1 High Time | Grid | cycles | 0–65535 | 1 | `hold:32` | — | Yes | Yes |
| Grid Voltage L2 Low | Grid | V | 0–6553.5 | 0.1 | `hold:33` | — | Yes | Yes |
| Grid Voltage L2 High | Grid | V | 0–6553.5 | 0.1 | `hold:34` | — | Yes | Yes |
| Grid Voltage L2 Low Time | Grid | cycles | 0–65535 | 1 | `hold:35` | — | Yes | Yes |
| Grid Voltage L2 High Time | Grid | cycles | 0–65535 | 1 | `hold:36` | — | Yes | Yes |
| Grid Voltage L3 Low | Grid | V | 0–6553.5 | 0.1 | `hold:37` | — | Yes | Yes |
| Grid Voltage L3 High | Grid | V | 0–6553.5 | 0.1 | `hold:38` | — | Yes | Yes |
| Grid Voltage L3 Low Time | Grid | cycles | 0–65535 | 1 | `hold:39` | — | Yes | Yes |
| Grid Voltage L3 High Time | Grid | cycles | 0–65535 | 1 | `hold:40` | — | Yes | Yes |
| Grid Voltage Moving Average High | Grid | V | 0–6553.5 | 0.1 | `hold:41` | — | Yes | Yes |
| Grid Frequency L1 Low | Grid | Hz | 0–655.35 | 0.01 | `hold:42` | — | Yes | Yes |
| Grid Frequency L1 High | Grid | Hz | 0–655.35 | 0.01 | `hold:43` | — | Yes | Yes |
| Grid Frequency L1 Low Time | Grid | cycles | 0–65535 | 1 | `hold:44` | — | Yes | Yes |
| Grid Frequency L1 High Time | Grid | cycles | 0–65535 | 1 | `hold:45` | — | Yes | Yes |
| Grid Frequency L2 Low | Grid | Hz | 0–655.35 | 0.01 | `hold:46` | — | Yes | Yes |
| Grid Frequency L2 High | Grid | Hz | 0–655.35 | 0.01 | `hold:47` | — | Yes | Yes |
| Grid Frequency L2 Low Time | Grid | cycles | 0–65535 | 1 | `hold:48` | — | Yes | Yes |
| Grid Frequency L2 High Time | Grid | cycles | 0–65535 | 1 | `hold:49` | — | Yes | Yes |
| Grid Frequency L3 Low | Grid | Hz | 0–655.35 | 0.01 | `hold:50` | — | Yes | Yes |
| Grid Frequency L3 High | Grid | Hz | 0–655.35 | 0.01 | `hold:51` | — | Yes | Yes |
| Grid Frequency L3 Low Time | Grid | cycles | 0–65535 | 1 | `hold:52` | — | Yes | Yes |
| Grid Frequency L3 High Time | Grid | cycles | 0–65535 | 1 | `hold:53` | — | Yes | Yes |
| Over-Frequency Derate Start | Grid | Hz | 50–52 | 0.01 | `hold:115` | — | Yes | Yes |
| Over-Frequency Derate End | Grid | Hz | 50–52 | 0.01 | `hold:124` | — | Yes | Yes |
| Over-Frequency Derate Delay | Grid | cycles | 0–1000 | 1 | `hold:97` | — | Yes | Yes |
| Over-Frequency Derate Ratio | Grid | %Pm/Hz | 1–100 | 1 | `hold:136` | — | Yes | Yes |
| Under-Frequency Derate Start | Grid | Hz | 45–50 | 0.01 | `hold:134` | — | Yes | Yes |
| Under-Frequency Derate End | Grid | Hz | 45–50 | 0.01 | `hold:135` | — | Yes | Yes |
| Under-Frequency Increase Ratio | Grid | %Pm/Hz | 1–100 | 1 | `hold:193` | — | Yes | Yes |
| Max Q Percent for QV | Grid | % | 0–100 | 1 | `hold:54` | — | Yes | Yes |
| QV Curve V2 Low | Grid | V | 0–6553.5 | 0.1 | `hold:55` | — | Yes | Yes |
| QV Curve V1 Low | Grid | V | 0–6553.5 | 0.1 | `hold:56` | — | Yes | Yes |
| QV Curve V1 High | Grid | V | 0–6553.5 | 0.1 | `hold:57` | — | Yes | Yes |
| QV Curve V2 High | Grid | V | 0–6553.5 | 0.1 | `hold:58` | — | Yes | Yes |
| PF Curve Lock-In Voltage | Grid | V | 230–300 | 0.1 | `hold:92` | — | Yes | Yes |
| PF Curve Lock-Out Voltage | Grid | V | 150–300 | 0.1 | `hold:93` | — | Yes | Yes |
| QV Lock-In Power | Grid | % | 0–100 | 1 | `hold:94` | — | Yes | Yes |
| QV Lock-Out Power | Grid | % | 0–100 | 1 | `hold:95` | — | Yes | Yes |
| QV Delay Time | Grid | cycles | 0–2000 | 1 | `hold:96` | — | Yes | Yes |
| VoltWatt V1 | Grid | V | 0–6553.5 | 0.1 | `hold:181` | — | Yes | Yes |
| VoltWatt V2 | Grid | V | 0–6553.5 | 0.1 | `hold:182` | — | Yes | Yes |
| VoltWatt Delay Time | Grid | ms | 500–60000 | 1 | `hold:183` | — | Yes | Yes |
| VoltWatt P2 | Grid | % | 0–100 | 1 | `hold:184` | — | Yes | Yes |
| Vref for QV | Grid | V | 0–6553.5 | 0.1 | `hold:185` | — | Yes | Yes |
| Vref Filter Time | Grid | s | 0–65535 | 1 | `hold:186` | — | Yes | Yes |
| Q3 for QV Curve | Grid | % | 0–100 | 1 | `hold:187` | — | Yes | Yes |
| Q4 for QV Curve | Grid | % | 0–100 | 1 | `hold:188` | — | Yes | Yes |
| P1 for QP Curve | Grid | % | 0–100 | 1 | `hold:189` | — | Yes | Yes |
| P2 for QP Curve | Grid | % | 0–100 | 1 | `hold:190` | — | Yes | Yes |
| P3 for QP Curve | Grid | % | 0–100 | 1 | `hold:191` | — | Yes | Yes |
| P4 for QP Curve | Grid | % | 0–100 | 1 | `hold:192` | — | Yes | Yes |
| Lead-Acid Charge Voltage | Battery | V | 50–59 | 0.1 | `hold:99` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Lead-Acid Discharge Cut-Off Voltage | Battery | V | 40–52 | 0.1 | `hold:100` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Lead-Acid Discharge Temp Low Limit | Battery | °C | -40–100 | 0.1 | `hold:106` | — | Yes | Yes |
| Lead-Acid Discharge Temp High Limit | Battery | °C | -40–100 | 0.1 | `hold:107` | — | Yes | Yes |
| Lead-Acid Charge Temp Low Limit | Battery | °C | -40–100 | 0.1 | `hold:108` | — | Yes | Yes |
| Lead-Acid Charge Temp High Limit | Battery | °C | -40–100 | 0.1 | `hold:109` | — | Yes | Yes |
| Battery Derating Start Voltage | Battery | V | 40–56 | 0.1 | `hold:118` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Lead-Acid Capacity | Battery | Ah | 50–5000 | 1 | `hold:204` | — | Yes | Yes |
| Float Charge Current Threshold | Battery | 0.01C | 1–255 | 1 | `hold:236` | — | Yes | Yes |
| Battery Transfer to Grid Voltage | Battery | V | 44.4–51.4 | 0.1 | `hold:166` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Battery Transfer to Grid SOC | Battery | % | 0–100 | 1 | `hold:167` | — | Yes | Yes |
| SOC Calibration Voltage 1 | Battery | V | 40–60 | 0.1 | `hold:171` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| SOC Calibration Voltage 2 | Battery | V | 40–60 | 0.1 | `hold:172` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| SOC Calibration SOC 1 | Battery | % | 0–100 | 1 | `hold:173` | — | Yes | Yes |
| SOC Calibration SOC 2 | Battery | % | 0–100 | 1 | `hold:174` | — | Yes | Yes |
| Battery Inner Resistance | Battery | µΩ | 0–100 | 1 | `hold:175` | — | Yes | Yes |
| Battery Cell Voltage Low Limit | Battery | V | 0–25.5 | 0.1 | `hold:132` | — | Yes | Yes |
| Battery Cell Voltage High Limit | Battery | V | 0–25.5 | 0.1 | `hold:132` | — | Yes | Yes |
| Battery Cells in Series | Battery | — | 0–255 | 1 | `hold:133` | — | Yes | Yes |
| Battery Cells in Parallel | Battery | — | 0–255 | 1 | `hold:133` | — | Yes | Yes |
| Smart Load On Voltage | Smart Load | V | 48–59 | 0.1 | `hold:213` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Smart Load Off Voltage | Smart Load | V | 40–52 | 0.1 | `hold:214` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Smart Load On SOC | Smart Load | % | 0–100 | 1 | `hold:215` | — | Yes | Yes |
| Smart Load Off SOC | Smart Load | % | 0–100 | 1 | `hold:216` | — | Yes | Yes |
| AC Couple Start SOC | AC Coupling | % | 0–100 | 1 | `hold:220` | — | Yes | Yes |
| AC Couple End SOC | AC Coupling | % | 0–255 | 1 | `hold:221` | — | Yes | Yes |
| AC Couple Start Voltage | AC Coupling | V | 40–59.5 | 0.1 | `hold:222` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Couple End Voltage | AC Coupling | V | 42–80 | 0.1 | `hold:223` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Grid Peak Shaving Voltage | Grid | V | 48–59 | 0.1 | `hold:208` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Grid Peak Shaving SOC Period 1 | Grid | % | 0–100 | 1 | `hold:218` | — | Yes | Yes |
| Grid Peak Shaving Voltage Period 1 | Grid | V | 48–59 | 0.1 | `hold:219` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Grid Peak Shaving Power Period 1 | Grid | kW | 0–25.5 | 0.1 | `hold:232` | — | Yes | Yes |
| Start Charge P_import Threshold | Inverter | W | -32768–32767 | 1 | `hold:117` | — | No | Yes |
| Specific Load Compensate | Inverter | W | 0–65535 | 1 | `hold:137` | — | Yes | Yes |
| Start PV Voltage | PV | V | 90–500 | 0.1 | `hold:22` | — | No | Yes |
| Start PV Power | PV | kW | 0–12 | 0.1 | `hold:217` | — | No | Yes |
| AFCI Arc Threshold | Inverter | A | 0–65535 | 1 | `hold:180` | — | Yes | Yes |
| Generator Cool Down Time | Generator | min | 0–25.5 | 0.1 | `hold:237` | — | Yes | Yes |
| Over-Temperature Derate Point | Inverter | °C | 60–90 | 0.1 | `hold:199` | — | Yes | Yes |
| Equalization Voltage | Battery | V | 50–59 | 0.1 | `hold:149` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 1 Mon | Schedules | kW | 0–25.5 | 0.1 | `hold:500` | — | Yes | Yes |
| AC Charge SOC Limit 1 Mon | Schedules | % | 0–100 | 1 | `hold:500` | — | Yes | Yes |
| AC Charge Volt Limit 1 Mon | Schedules | V | 40–59 | 0.1 | `hold:501` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 2 Mon | Schedules | kW | 0–25.5 | 0.1 | `hold:504` | — | Yes | Yes |
| AC Charge SOC Limit 2 Mon | Schedules | % | 0–100 | 1 | `hold:504` | — | Yes | Yes |
| AC Charge Volt Limit 2 Mon | Schedules | V | 40–59 | 0.1 | `hold:505` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 1 Tue | Schedules | kW | 0–25.5 | 0.1 | `hold:508` | — | Yes | Yes |
| AC Charge SOC Limit 1 Tue | Schedules | % | 0–100 | 1 | `hold:508` | — | Yes | Yes |
| AC Charge Volt Limit 1 Tue | Schedules | V | 40–59 | 0.1 | `hold:509` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 2 Tue | Schedules | kW | 0–25.5 | 0.1 | `hold:512` | — | Yes | Yes |
| AC Charge SOC Limit 2 Tue | Schedules | % | 0–100 | 1 | `hold:512` | — | Yes | Yes |
| AC Charge Volt Limit 2 Tue | Schedules | V | 40–59 | 0.1 | `hold:513` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 1 Wed | Schedules | kW | 0–25.5 | 0.1 | `hold:516` | — | Yes | Yes |
| AC Charge SOC Limit 1 Wed | Schedules | % | 0–100 | 1 | `hold:516` | — | Yes | Yes |
| AC Charge Volt Limit 1 Wed | Schedules | V | 40–59 | 0.1 | `hold:517` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 2 Wed | Schedules | kW | 0–25.5 | 0.1 | `hold:520` | — | Yes | Yes |
| AC Charge SOC Limit 2 Wed | Schedules | % | 0–100 | 1 | `hold:520` | — | Yes | Yes |
| AC Charge Volt Limit 2 Wed | Schedules | V | 40–59 | 0.1 | `hold:521` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 1 Thu | Schedules | kW | 0–25.5 | 0.1 | `hold:524` | — | Yes | Yes |
| AC Charge SOC Limit 1 Thu | Schedules | % | 0–100 | 1 | `hold:524` | — | Yes | Yes |
| AC Charge Volt Limit 1 Thu | Schedules | V | 40–59 | 0.1 | `hold:525` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 2 Thu | Schedules | kW | 0–25.5 | 0.1 | `hold:528` | — | Yes | Yes |
| AC Charge SOC Limit 2 Thu | Schedules | % | 0–100 | 1 | `hold:528` | — | Yes | Yes |
| AC Charge Volt Limit 2 Thu | Schedules | V | 40–59 | 0.1 | `hold:529` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 1 Fri | Schedules | kW | 0–25.5 | 0.1 | `hold:532` | — | Yes | Yes |
| AC Charge SOC Limit 1 Fri | Schedules | % | 0–100 | 1 | `hold:532` | — | Yes | Yes |
| AC Charge Volt Limit 1 Fri | Schedules | V | 40–59 | 0.1 | `hold:533` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 2 Fri | Schedules | kW | 0–25.5 | 0.1 | `hold:536` | — | Yes | Yes |
| AC Charge SOC Limit 2 Fri | Schedules | % | 0–100 | 1 | `hold:536` | — | Yes | Yes |
| AC Charge Volt Limit 2 Fri | Schedules | V | 40–59 | 0.1 | `hold:537` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 1 Sat | Schedules | kW | 0–25.5 | 0.1 | `hold:540` | — | Yes | Yes |
| AC Charge SOC Limit 1 Sat | Schedules | % | 0–100 | 1 | `hold:540` | — | Yes | Yes |
| AC Charge Volt Limit 1 Sat | Schedules | V | 40–59 | 0.1 | `hold:541` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 2 Sat | Schedules | kW | 0–25.5 | 0.1 | `hold:544` | — | Yes | Yes |
| AC Charge SOC Limit 2 Sat | Schedules | % | 0–100 | 1 | `hold:544` | — | Yes | Yes |
| AC Charge Volt Limit 2 Sat | Schedules | V | 40–59 | 0.1 | `hold:545` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 1 Sun | Schedules | kW | 0–25.5 | 0.1 | `hold:548` | — | Yes | Yes |
| AC Charge SOC Limit 1 Sun | Schedules | % | 0–100 | 1 | `hold:548` | — | Yes | Yes |
| AC Charge Volt Limit 1 Sun | Schedules | V | 40–59 | 0.1 | `hold:549` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| AC Charge Power 2 Sun | Schedules | kW | 0–25.5 | 0.1 | `hold:552` | — | Yes | Yes |
| AC Charge SOC Limit 2 Sun | Schedules | % | 0–100 | 1 | `hold:552` | — | Yes | Yes |
| AC Charge Volt Limit 2 Sun | Schedules | V | 40–59 | 0.1 | `hold:553` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 1 Mon | Schedules | kW | 0–25.5 | 0.1 | `hold:556` | — | Yes | Yes |
| Forced Charge SOC Limit 1 Mon | Schedules | % | 0–100 | 1 | `hold:556` | — | Yes | Yes |
| Forced Charge Volt Limit 1 Mon | Schedules | V | 40–59 | 0.1 | `hold:557` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 2 Mon | Schedules | kW | 0–25.5 | 0.1 | `hold:560` | — | Yes | Yes |
| Forced Charge SOC Limit 2 Mon | Schedules | % | 0–100 | 1 | `hold:560` | — | Yes | Yes |
| Forced Charge Volt Limit 2 Mon | Schedules | V | 40–59 | 0.1 | `hold:561` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 1 Tue | Schedules | kW | 0–25.5 | 0.1 | `hold:564` | — | Yes | Yes |
| Forced Charge SOC Limit 1 Tue | Schedules | % | 0–100 | 1 | `hold:564` | — | Yes | Yes |
| Forced Charge Volt Limit 1 Tue | Schedules | V | 40–59 | 0.1 | `hold:565` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 2 Tue | Schedules | kW | 0–25.5 | 0.1 | `hold:568` | — | Yes | Yes |
| Forced Charge SOC Limit 2 Tue | Schedules | % | 0–100 | 1 | `hold:568` | — | Yes | Yes |
| Forced Charge Volt Limit 2 Tue | Schedules | V | 40–59 | 0.1 | `hold:569` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 1 Wed | Schedules | kW | 0–25.5 | 0.1 | `hold:572` | — | Yes | Yes |
| Forced Charge SOC Limit 1 Wed | Schedules | % | 0–100 | 1 | `hold:572` | — | Yes | Yes |
| Forced Charge Volt Limit 1 Wed | Schedules | V | 40–59 | 0.1 | `hold:573` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 2 Wed | Schedules | kW | 0–25.5 | 0.1 | `hold:576` | — | Yes | Yes |
| Forced Charge SOC Limit 2 Wed | Schedules | % | 0–100 | 1 | `hold:576` | — | Yes | Yes |
| Forced Charge Volt Limit 2 Wed | Schedules | V | 40–59 | 0.1 | `hold:577` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 1 Thu | Schedules | kW | 0–25.5 | 0.1 | `hold:580` | — | Yes | Yes |
| Forced Charge SOC Limit 1 Thu | Schedules | % | 0–100 | 1 | `hold:580` | — | Yes | Yes |
| Forced Charge Volt Limit 1 Thu | Schedules | V | 40–59 | 0.1 | `hold:581` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 2 Thu | Schedules | kW | 0–25.5 | 0.1 | `hold:584` | — | Yes | Yes |
| Forced Charge SOC Limit 2 Thu | Schedules | % | 0–100 | 1 | `hold:584` | — | Yes | Yes |
| Forced Charge Volt Limit 2 Thu | Schedules | V | 40–59 | 0.1 | `hold:585` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 1 Fri | Schedules | kW | 0–25.5 | 0.1 | `hold:588` | — | Yes | Yes |
| Forced Charge SOC Limit 1 Fri | Schedules | % | 0–100 | 1 | `hold:588` | — | Yes | Yes |
| Forced Charge Volt Limit 1 Fri | Schedules | V | 40–59 | 0.1 | `hold:589` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 2 Fri | Schedules | kW | 0–25.5 | 0.1 | `hold:592` | — | Yes | Yes |
| Forced Charge SOC Limit 2 Fri | Schedules | % | 0–100 | 1 | `hold:592` | — | Yes | Yes |
| Forced Charge Volt Limit 2 Fri | Schedules | V | 40–59 | 0.1 | `hold:593` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 1 Sat | Schedules | kW | 0–25.5 | 0.1 | `hold:596` | — | Yes | Yes |
| Forced Charge SOC Limit 1 Sat | Schedules | % | 0–100 | 1 | `hold:596` | — | Yes | Yes |
| Forced Charge Volt Limit 1 Sat | Schedules | V | 40–59 | 0.1 | `hold:597` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 2 Sat | Schedules | kW | 0–25.5 | 0.1 | `hold:600` | — | Yes | Yes |
| Forced Charge SOC Limit 2 Sat | Schedules | % | 0–100 | 1 | `hold:600` | — | Yes | Yes |
| Forced Charge Volt Limit 2 Sat | Schedules | V | 40–59 | 0.1 | `hold:601` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 1 Sun | Schedules | kW | 0–25.5 | 0.1 | `hold:604` | — | Yes | Yes |
| Forced Charge SOC Limit 1 Sun | Schedules | % | 0–100 | 1 | `hold:604` | — | Yes | Yes |
| Forced Charge Volt Limit 1 Sun | Schedules | V | 40–59 | 0.1 | `hold:605` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Charge Power 2 Sun | Schedules | kW | 0–25.5 | 0.1 | `hold:608` | — | Yes | Yes |
| Forced Charge SOC Limit 2 Sun | Schedules | % | 0–100 | 1 | `hold:608` | — | Yes | Yes |
| Forced Charge Volt Limit 2 Sun | Schedules | V | 40–59 | 0.1 | `hold:609` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 1 Mon | Schedules | kW | 0–25.5 | 0.1 | `hold:612` | — | Yes | Yes |
| Forced Discharge SOC Limit 1 Mon | Schedules | % | 0–100 | 1 | `hold:612` | — | Yes | Yes |
| Forced Discharge Volt Limit 1 Mon | Schedules | V | 40–59 | 0.1 | `hold:613` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 2 Mon | Schedules | kW | 0–25.5 | 0.1 | `hold:616` | — | Yes | Yes |
| Forced Discharge SOC Limit 2 Mon | Schedules | % | 0–100 | 1 | `hold:616` | — | Yes | Yes |
| Forced Discharge Volt Limit 2 Mon | Schedules | V | 40–59 | 0.1 | `hold:617` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 1 Tue | Schedules | kW | 0–25.5 | 0.1 | `hold:620` | — | Yes | Yes |
| Forced Discharge SOC Limit 1 Tue | Schedules | % | 0–100 | 1 | `hold:620` | — | Yes | Yes |
| Forced Discharge Volt Limit 1 Tue | Schedules | V | 40–59 | 0.1 | `hold:621` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 2 Tue | Schedules | kW | 0–25.5 | 0.1 | `hold:624` | — | Yes | Yes |
| Forced Discharge SOC Limit 2 Tue | Schedules | % | 0–100 | 1 | `hold:624` | — | Yes | Yes |
| Forced Discharge Volt Limit 2 Tue | Schedules | V | 40–59 | 0.1 | `hold:625` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 1 Wed | Schedules | kW | 0–25.5 | 0.1 | `hold:628` | — | Yes | Yes |
| Forced Discharge SOC Limit 1 Wed | Schedules | % | 0–100 | 1 | `hold:628` | — | Yes | Yes |
| Forced Discharge Volt Limit 1 Wed | Schedules | V | 40–59 | 0.1 | `hold:629` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 2 Wed | Schedules | kW | 0–25.5 | 0.1 | `hold:632` | — | Yes | Yes |
| Forced Discharge SOC Limit 2 Wed | Schedules | % | 0–100 | 1 | `hold:632` | — | Yes | Yes |
| Forced Discharge Volt Limit 2 Wed | Schedules | V | 40–59 | 0.1 | `hold:633` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 1 Thu | Schedules | kW | 0–25.5 | 0.1 | `hold:636` | — | Yes | Yes |
| Forced Discharge SOC Limit 1 Thu | Schedules | % | 0–100 | 1 | `hold:636` | — | Yes | Yes |
| Forced Discharge Volt Limit 1 Thu | Schedules | V | 40–59 | 0.1 | `hold:637` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 2 Thu | Schedules | kW | 0–25.5 | 0.1 | `hold:640` | — | Yes | Yes |
| Forced Discharge SOC Limit 2 Thu | Schedules | % | 0–100 | 1 | `hold:640` | — | Yes | Yes |
| Forced Discharge Volt Limit 2 Thu | Schedules | V | 40–59 | 0.1 | `hold:641` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 1 Fri | Schedules | kW | 0–25.5 | 0.1 | `hold:644` | — | Yes | Yes |
| Forced Discharge SOC Limit 1 Fri | Schedules | % | 0–100 | 1 | `hold:644` | — | Yes | Yes |
| Forced Discharge Volt Limit 1 Fri | Schedules | V | 40–59 | 0.1 | `hold:645` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 2 Fri | Schedules | kW | 0–25.5 | 0.1 | `hold:648` | — | Yes | Yes |
| Forced Discharge SOC Limit 2 Fri | Schedules | % | 0–100 | 1 | `hold:648` | — | Yes | Yes |
| Forced Discharge Volt Limit 2 Fri | Schedules | V | 40–59 | 0.1 | `hold:649` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 1 Sat | Schedules | kW | 0–25.5 | 0.1 | `hold:652` | — | Yes | Yes |
| Forced Discharge SOC Limit 1 Sat | Schedules | % | 0–100 | 1 | `hold:652` | — | Yes | Yes |
| Forced Discharge Volt Limit 1 Sat | Schedules | V | 40–59 | 0.1 | `hold:653` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 2 Sat | Schedules | kW | 0–25.5 | 0.1 | `hold:656` | — | Yes | Yes |
| Forced Discharge SOC Limit 2 Sat | Schedules | % | 0–100 | 1 | `hold:656` | — | Yes | Yes |
| Forced Discharge Volt Limit 2 Sat | Schedules | V | 40–59 | 0.1 | `hold:657` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 1 Sun | Schedules | kW | 0–25.5 | 0.1 | `hold:660` | — | Yes | Yes |
| Forced Discharge SOC Limit 1 Sun | Schedules | % | 0–100 | 1 | `hold:660` | — | Yes | Yes |
| Forced Discharge Volt Limit 1 Sun | Schedules | V | 40–59 | 0.1 | `hold:661` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Forced Discharge Power 2 Sun | Schedules | kW | 0–25.5 | 0.1 | `hold:664` | — | Yes | Yes |
| Forced Discharge SOC Limit 2 Sun | Schedules | % | 0–100 | 1 | `hold:664` | — | Yes | Yes |
| Forced Discharge Volt Limit 2 Sun | Schedules | V | 40–59 | 0.1 | `hold:665` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 1 Mon | Schedules | kW | 0–25.5 | 0.1 | `hold:668` | — | Yes | Yes |
| Peak Shaving SOC Limit 1 Mon | Schedules | % | 0–100 | 1 | `hold:668` | — | Yes | Yes |
| Peak Shaving Volt Limit 1 Mon | Schedules | V | 40–59 | 0.1 | `hold:669` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 2 Mon | Schedules | kW | 0–25.5 | 0.1 | `hold:672` | — | Yes | Yes |
| Peak Shaving SOC Limit 2 Mon | Schedules | % | 0–100 | 1 | `hold:672` | — | Yes | Yes |
| Peak Shaving Volt Limit 2 Mon | Schedules | V | 40–59 | 0.1 | `hold:673` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 1 Tue | Schedules | kW | 0–25.5 | 0.1 | `hold:676` | — | Yes | Yes |
| Peak Shaving SOC Limit 1 Tue | Schedules | % | 0–100 | 1 | `hold:676` | — | Yes | Yes |
| Peak Shaving Volt Limit 1 Tue | Schedules | V | 40–59 | 0.1 | `hold:677` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 2 Tue | Schedules | kW | 0–25.5 | 0.1 | `hold:680` | — | Yes | Yes |
| Peak Shaving SOC Limit 2 Tue | Schedules | % | 0–100 | 1 | `hold:680` | — | Yes | Yes |
| Peak Shaving Volt Limit 2 Tue | Schedules | V | 40–59 | 0.1 | `hold:681` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 1 Wed | Schedules | kW | 0–25.5 | 0.1 | `hold:684` | — | Yes | Yes |
| Peak Shaving SOC Limit 1 Wed | Schedules | % | 0–100 | 1 | `hold:684` | — | Yes | Yes |
| Peak Shaving Volt Limit 1 Wed | Schedules | V | 40–59 | 0.1 | `hold:685` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 2 Wed | Schedules | kW | 0–25.5 | 0.1 | `hold:688` | — | Yes | Yes |
| Peak Shaving SOC Limit 2 Wed | Schedules | % | 0–100 | 1 | `hold:688` | — | Yes | Yes |
| Peak Shaving Volt Limit 2 Wed | Schedules | V | 40–59 | 0.1 | `hold:689` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 1 Thu | Schedules | kW | 0–25.5 | 0.1 | `hold:692` | — | Yes | Yes |
| Peak Shaving SOC Limit 1 Thu | Schedules | % | 0–100 | 1 | `hold:692` | — | Yes | Yes |
| Peak Shaving Volt Limit 1 Thu | Schedules | V | 40–59 | 0.1 | `hold:693` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 2 Thu | Schedules | kW | 0–25.5 | 0.1 | `hold:696` | — | Yes | Yes |
| Peak Shaving SOC Limit 2 Thu | Schedules | % | 0–100 | 1 | `hold:696` | — | Yes | Yes |
| Peak Shaving Volt Limit 2 Thu | Schedules | V | 40–59 | 0.1 | `hold:697` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 1 Fri | Schedules | kW | 0–25.5 | 0.1 | `hold:700` | — | Yes | Yes |
| Peak Shaving SOC Limit 1 Fri | Schedules | % | 0–100 | 1 | `hold:700` | — | Yes | Yes |
| Peak Shaving Volt Limit 1 Fri | Schedules | V | 40–59 | 0.1 | `hold:701` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 2 Fri | Schedules | kW | 0–25.5 | 0.1 | `hold:704` | — | Yes | Yes |
| Peak Shaving SOC Limit 2 Fri | Schedules | % | 0–100 | 1 | `hold:704` | — | Yes | Yes |
| Peak Shaving Volt Limit 2 Fri | Schedules | V | 40–59 | 0.1 | `hold:705` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 1 Sat | Schedules | kW | 0–25.5 | 0.1 | `hold:708` | — | Yes | Yes |
| Peak Shaving SOC Limit 1 Sat | Schedules | % | 0–100 | 1 | `hold:708` | — | Yes | Yes |
| Peak Shaving Volt Limit 1 Sat | Schedules | V | 40–59 | 0.1 | `hold:709` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 2 Sat | Schedules | kW | 0–25.5 | 0.1 | `hold:712` | — | Yes | Yes |
| Peak Shaving SOC Limit 2 Sat | Schedules | % | 0–100 | 1 | `hold:712` | — | Yes | Yes |
| Peak Shaving Volt Limit 2 Sat | Schedules | V | 40–59 | 0.1 | `hold:713` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 1 Sun | Schedules | kW | 0–25.5 | 0.1 | `hold:716` | — | Yes | Yes |
| Peak Shaving SOC Limit 1 Sun | Schedules | % | 0–100 | 1 | `hold:716` | — | Yes | Yes |
| Peak Shaving Volt Limit 1 Sun | Schedules | V | 40–59 | 0.1 | `hold:717` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |
| Peak Shaving Power 2 Sun | Schedules | kW | 0–25.5 | 0.1 | `hold:720` | — | Yes | Yes |
| Peak Shaving SOC Limit 2 Sun | Schedules | % | 0–100 | 1 | `hold:720` | — | Yes | Yes |
| Peak Shaving Volt Limit 2 Sun | Schedules | V | 40–59 | 0.1 | `hold:721` | Scaled by battery voltage (12/24/48 V) | Yes | Yes |

## Switches (30)

| Name | Device Group | Device Class | Register | Primary Only | Enabled |
| :--- | :--- | :--- | :--- | :---: | :---: |
| Power Backup | Grid | switch | `hold:21` | Yes | Yes |
| Over-Frequency Load Reduction | Grid | switch | `hold:21` | Yes | Yes |
| DRMS | Grid | switch | `hold:21` | Yes | Yes |
| AC Charging | Inverter | switch | `hold:21` | Yes | Yes |
| Seamless EPS Switching | Inverter | switch | `hold:21` | Yes | Yes |
| Forced Discharge | Inverter | switch | `hold:21` | Yes | Yes |
| Charge First (PV) | Inverter | switch | `hold:21` | Yes | Yes |
| Grid Export | Grid | switch | `hold:21` | Yes | Yes |
| Fast Zero Export | Inverter | switch | `hold:110` | Yes | Yes |
| Micro-Grid | Inverter | switch | `hold:110` | Yes | Yes |
| Charge Last | Battery | switch | `hold:110` | Yes | Yes |
| Buzzer | Inverter | switch | `hold:110` | Yes | Yes |
| Take Load Together | Inverter | switch | `hold:110` | Yes | Yes |
| Green Mode | Inverter | switch | `hold:110` | Yes | Yes |
| Eco Mode | Inverter | switch | `hold:110` | Yes | Yes |
| Half Hour AC Charge Start | Inverter | switch | `hold:120` | Yes | Yes |
| AC CT Direction Reversed | Grid | switch | `hold:179` | Yes | Yes |
| Volt-Watt Function | Grid | switch | `hold:179` | Yes | Yes |
| Grid Peak Shaving | Grid | switch | `hold:179` | Yes | Yes |
| AC Coupling | Inverter | switch | `hold:179` | Yes | Yes |
| PV Arc Detection | PV | switch | `hold:179` | No | Yes |
| On-Grid Always On | Smart Load | switch | `hold:179` | Yes | Yes |
| Grid CT Connection | Grid | switch | `hold:226` | Yes | Yes |
| Quick Charge Start | Inverter | switch | `hold:233` | Yes | Yes |
| Battery Backup | Battery | switch | `hold:233` | Yes | Yes |
| Battery Maintenance | Battery | switch | `hold:233` | Yes | Yes |
| 7-Day Schedule Enable | Schedules | switch | `hold:233` | Yes | Yes |
| WattNode CT1 Direction | Inverter | switch | `hold:251` | Yes | Yes |
| WattNode CT2 Direction | Inverter | switch | `hold:251` | Yes | Yes |
| WattNode CT3 Direction | Inverter | switch | `hold:251` | Yes | Yes |

## Selects (17)

| Name | Device Group | Options | Register | Primary Only | Enabled |
| :--- | :--- | :--- | :--- | :---: | :---: |
| AC Charge Type | Inverter | Disable, According to Time, According to Voltage, According to SOC, According to Voltage and Time, According to SOC and Time | `hold:120` | Yes | Yes |
| Discharge Control Type | Inverter | According to Voltage, According to SOC, According to Both | `hold:120` | Yes | Yes |
| On-Grid EOD Type | Grid | According to Voltage, According to SOC | `hold:120` | Yes | Yes |
| Generator Charge Type | Generator | According to Battery Voltage, According to Battery SOC | `hold:120` | Yes | Yes |
| System Type | Inverter | No parallel (single one), Single-phase parallel (primary), Secondary, Three phase parallel (Master), 2*208 (Master) - for split-phase | `hold:112` | No | Yes |
| Language | Inverter | English, German | `hold:16` | Yes | Yes |
| PV Input Model | PV | No PV, PV1 in, PV2 in, PV3 in, PV1 & PV2 in, PV1 & PV3 in, PV2 & PV3 in, PV1 & PV2 & PV3 in | `hold:20` | No | Yes |
| Reactive Power Command Type | Grid | Unit power factor, Fixed PF, Default PF curve (Q(P)), Custom PF curve, Capacitive reactive power percentage, Inductive reactive power percentage, Q(V) curve, Q(V) Dynamic | `hold:59` | Yes | Yes |
| Output Priority Config | Inverter | Battery First, PV First, AC First | `hold:145` | Yes | Yes |
| Line Mode | Inverter | APL (Appliance), UPS (Uninterruptible Power Supply), GEN (Generator) | `hold:146` | Yes | Yes |
| Grid Type | Grid | Split Phase 240V/120V, 3-Phase Star 120V/208V, Single Phase 240V, Single Phase 230V, Split Phase 200V/100V, 3-Phase Delta 230V/230V, 3-Phase Star 240V/415V, 3-Phase Star 230V/400V, 3-Phase Star 220V/380V | `hold:205` | Yes | Yes |
| Working Mode | Inverter | Standby, Normal | `hold:21` | Yes | Yes |
| Smart Load Enable | Inverter | Generator, Smart Load | `hold:179` | Yes | Yes |
| LCD Screen Type | Inverter | Screen 'B' size, Screen 'S' size | `hold:224` | Yes | Yes |
| EPS Voltage Set | EPS | 208 V, 220 V, 230 V, 240 V, 277 V | `hold:90` | Yes | Yes |
| EPS Frequency Set | EPS | 50 Hz, 60 Hz | `hold:91` | Yes | Yes |
| Off-grid Composed Phase | Grid | R Phase, S Phase, T Phase | `hold:113` | No | Yes |

## Buttons (4)

| Name | Device Group | Register | Primary Only | Enabled |
| :--- | :--- | :--- | :---: | :---: |
| Reboot Inverter | Inverter | `hold:11` | No | Yes |
| Clear Detected Phases | Grid | `hold:113` | No | Yes |
| Clear Parallel Alarm | Inverter | `hold:114` | Yes | Yes |
| Reset G100 Lockout | Grid | `hold:231` | Yes | Yes |

## Time (144)

| Name | Device Group | Register | Primary Only | Enabled |
| :--- | :--- | :--- | :---: | :---: |
| AC Charging Start Time | Inverter | `hold:68` | Yes | Yes |
| AC Charging End Time | Inverter | `hold:69` | Yes | Yes |
| AC Charging Start Time 1 | Inverter | `hold:70` | Yes | Yes |
| AC Charging End Time 1 | Inverter | `hold:71` | Yes | Yes |
| AC Charging Start Time 2 | Inverter | `hold:72` | Yes | Yes |
| AC Charging End Time 2 | Inverter | `hold:73` | Yes | Yes |
| AC First Load Start Time | Inverter | `hold:152` | Yes | Yes |
| AC First Load End Time | Inverter | `hold:153` | Yes | Yes |
| AC First Load Start Time 1 | Inverter | `hold:154` | Yes | Yes |
| AC First Load End Time 1 | Inverter | `hold:155` | Yes | Yes |
| Peak Shaving Start Time | Grid | `hold:209` | Yes | Yes |
| Peak Shaving End Time | Grid | `hold:210` | Yes | Yes |
| Peak Shaving Start Time 1 | Grid | `hold:211` | Yes | Yes |
| Peak Shaving End Time 1 | Grid | `hold:212` | Yes | Yes |
| Generator Start Time | Generator | `hold:256` | Yes | Yes |
| Generator End Time | Generator | `hold:257` | Yes | Yes |
| Generator Start Time 1 | Generator | `hold:258` | Yes | Yes |
| Generator End Time 1 | Generator | `hold:259` | Yes | Yes |
| Forced Discharge Start Time | Inverter | `hold:84` | Yes | Yes |
| Forced Discharge End Time | Inverter | `hold:85` | Yes | Yes |
| Forced Discharge Start Time 1 | Inverter | `hold:86` | Yes | Yes |
| Forced Discharge End Time 1 | Inverter | `hold:87` | Yes | Yes |
| Forced Discharge Start Time 2 | Inverter | `hold:88` | Yes | Yes |
| Forced Discharge End Time 2 | Inverter | `hold:89` | Yes | Yes |
| AC Charge Start Time 1 Mon | Schedules | `hold:502` | Yes | Yes |
| AC Charge End Time 1 Mon | Schedules | `hold:503` | Yes | Yes |
| AC Charge Start Time 2 Mon | Schedules | `hold:506` | Yes | Yes |
| AC Charge End Time 2 Mon | Schedules | `hold:507` | Yes | Yes |
| AC Charge Start Time 1 Tue | Schedules | `hold:510` | Yes | Yes |
| AC Charge End Time 1 Tue | Schedules | `hold:511` | Yes | Yes |
| AC Charge Start Time 2 Tue | Schedules | `hold:514` | Yes | Yes |
| AC Charge End Time 2 Tue | Schedules | `hold:515` | Yes | Yes |
| AC Charge Start Time 1 Wed | Schedules | `hold:518` | Yes | Yes |
| AC Charge End Time 1 Wed | Schedules | `hold:519` | Yes | Yes |
| AC Charge Start Time 2 Wed | Schedules | `hold:522` | Yes | Yes |
| AC Charge End Time 2 Wed | Schedules | `hold:523` | Yes | Yes |
| AC Charge Start Time 1 Thu | Schedules | `hold:526` | Yes | Yes |
| AC Charge End Time 1 Thu | Schedules | `hold:527` | Yes | Yes |
| AC Charge Start Time 2 Thu | Schedules | `hold:530` | Yes | Yes |
| AC Charge End Time 2 Thu | Schedules | `hold:531` | Yes | Yes |
| AC Charge Start Time 1 Fri | Schedules | `hold:534` | Yes | Yes |
| AC Charge End Time 1 Fri | Schedules | `hold:535` | Yes | Yes |
| AC Charge Start Time 2 Fri | Schedules | `hold:538` | Yes | Yes |
| AC Charge End Time 2 Fri | Schedules | `hold:539` | Yes | Yes |
| AC Charge Start Time 1 Sat | Schedules | `hold:542` | Yes | Yes |
| AC Charge End Time 1 Sat | Schedules | `hold:543` | Yes | Yes |
| AC Charge Start Time 2 Sat | Schedules | `hold:546` | Yes | Yes |
| AC Charge End Time 2 Sat | Schedules | `hold:547` | Yes | Yes |
| AC Charge Start Time 1 Sun | Schedules | `hold:550` | Yes | Yes |
| AC Charge End Time 1 Sun | Schedules | `hold:551` | Yes | Yes |
| AC Charge Start Time 2 Sun | Schedules | `hold:554` | Yes | Yes |
| AC Charge End Time 2 Sun | Schedules | `hold:555` | Yes | Yes |
| Forced Charge Start Time 1 Mon | Schedules | `hold:558` | Yes | Yes |
| Forced Charge End Time 1 Mon | Schedules | `hold:559` | Yes | Yes |
| Forced Charge Start Time 2 Mon | Schedules | `hold:562` | Yes | Yes |
| Forced Charge End Time 2 Mon | Schedules | `hold:563` | Yes | Yes |
| Forced Charge Start Time 1 Tue | Schedules | `hold:566` | Yes | Yes |
| Forced Charge End Time 1 Tue | Schedules | `hold:567` | Yes | Yes |
| Forced Charge Start Time 2 Tue | Schedules | `hold:570` | Yes | Yes |
| Forced Charge End Time 2 Tue | Schedules | `hold:571` | Yes | Yes |
| Forced Charge Start Time 1 Wed | Schedules | `hold:574` | Yes | Yes |
| Forced Charge End Time 1 Wed | Schedules | `hold:575` | Yes | Yes |
| Forced Charge Start Time 2 Wed | Schedules | `hold:578` | Yes | Yes |
| Forced Charge End Time 2 Wed | Schedules | `hold:579` | Yes | Yes |
| Forced Charge Start Time 1 Thu | Schedules | `hold:582` | Yes | Yes |
| Forced Charge End Time 1 Thu | Schedules | `hold:583` | Yes | Yes |
| Forced Charge Start Time 2 Thu | Schedules | `hold:586` | Yes | Yes |
| Forced Charge End Time 2 Thu | Schedules | `hold:587` | Yes | Yes |
| Forced Charge Start Time 1 Fri | Schedules | `hold:590` | Yes | Yes |
| Forced Charge End Time 1 Fri | Schedules | `hold:591` | Yes | Yes |
| Forced Charge Start Time 2 Fri | Schedules | `hold:594` | Yes | Yes |
| Forced Charge End Time 2 Fri | Schedules | `hold:595` | Yes | Yes |
| Forced Charge Start Time 1 Sat | Schedules | `hold:598` | Yes | Yes |
| Forced Charge End Time 1 Sat | Schedules | `hold:599` | Yes | Yes |
| Forced Charge Start Time 2 Sat | Schedules | `hold:602` | Yes | Yes |
| Forced Charge End Time 2 Sat | Schedules | `hold:603` | Yes | Yes |
| Forced Charge Start Time 1 Sun | Schedules | `hold:606` | Yes | Yes |
| Forced Charge End Time 1 Sun | Schedules | `hold:607` | Yes | Yes |
| Forced Charge Start Time 2 Sun | Schedules | `hold:610` | Yes | Yes |
| Forced Charge End Time 2 Sun | Schedules | `hold:611` | Yes | Yes |
| Forced Discharge Start Time 1 Mon | Schedules | `hold:614` | Yes | Yes |
| Forced Discharge End Time 1 Mon | Schedules | `hold:615` | Yes | Yes |
| Forced Discharge Start Time 2 Mon | Schedules | `hold:618` | Yes | Yes |
| Forced Discharge End Time 2 Mon | Schedules | `hold:619` | Yes | Yes |
| Forced Discharge Start Time 1 Tue | Schedules | `hold:622` | Yes | Yes |
| Forced Discharge End Time 1 Tue | Schedules | `hold:623` | Yes | Yes |
| Forced Discharge Start Time 2 Tue | Schedules | `hold:626` | Yes | Yes |
| Forced Discharge End Time 2 Tue | Schedules | `hold:627` | Yes | Yes |
| Forced Discharge Start Time 1 Wed | Schedules | `hold:630` | Yes | Yes |
| Forced Discharge End Time 1 Wed | Schedules | `hold:631` | Yes | Yes |
| Forced Discharge Start Time 2 Wed | Schedules | `hold:634` | Yes | Yes |
| Forced Discharge End Time 2 Wed | Schedules | `hold:635` | Yes | Yes |
| Forced Discharge Start Time 1 Thu | Schedules | `hold:638` | Yes | Yes |
| Forced Discharge End Time 1 Thu | Schedules | `hold:639` | Yes | Yes |
| Forced Discharge Start Time 2 Thu | Schedules | `hold:642` | Yes | Yes |
| Forced Discharge End Time 2 Thu | Schedules | `hold:643` | Yes | Yes |
| Forced Discharge Start Time 1 Fri | Schedules | `hold:646` | Yes | Yes |
| Forced Discharge End Time 1 Fri | Schedules | `hold:647` | Yes | Yes |
| Forced Discharge Start Time 2 Fri | Schedules | `hold:650` | Yes | Yes |
| Forced Discharge End Time 2 Fri | Schedules | `hold:651` | Yes | Yes |
| Forced Discharge Start Time 1 Sat | Schedules | `hold:654` | Yes | Yes |
| Forced Discharge End Time 1 Sat | Schedules | `hold:655` | Yes | Yes |
| Forced Discharge Start Time 2 Sat | Schedules | `hold:658` | Yes | Yes |
| Forced Discharge End Time 2 Sat | Schedules | `hold:659` | Yes | Yes |
| Forced Discharge Start Time 1 Sun | Schedules | `hold:662` | Yes | Yes |
| Forced Discharge End Time 1 Sun | Schedules | `hold:663` | Yes | Yes |
| Forced Discharge Start Time 2 Sun | Schedules | `hold:666` | Yes | Yes |
| Forced Discharge End Time 2 Sun | Schedules | `hold:667` | Yes | Yes |
| Peak Shaving Start Time 1 Mon | Schedules | `hold:670` | Yes | Yes |
| Peak Shaving End Time 1 Mon | Schedules | `hold:671` | Yes | Yes |
| Peak Shaving Start Time 2 Mon | Schedules | `hold:674` | Yes | Yes |
| Peak Shaving End Time 2 Mon | Schedules | `hold:675` | Yes | Yes |
| Peak Shaving Start Time 1 Tue | Schedules | `hold:678` | Yes | Yes |
| Peak Shaving End Time 1 Tue | Schedules | `hold:679` | Yes | Yes |
| Peak Shaving Start Time 2 Tue | Schedules | `hold:682` | Yes | Yes |
| Peak Shaving End Time 2 Tue | Schedules | `hold:683` | Yes | Yes |
| Peak Shaving Start Time 1 Wed | Schedules | `hold:686` | Yes | Yes |
| Peak Shaving End Time 1 Wed | Schedules | `hold:687` | Yes | Yes |
| Peak Shaving Start Time 2 Wed | Schedules | `hold:690` | Yes | Yes |
| Peak Shaving End Time 2 Wed | Schedules | `hold:691` | Yes | Yes |
| Peak Shaving Start Time 1 Thu | Schedules | `hold:694` | Yes | Yes |
| Peak Shaving End Time 1 Thu | Schedules | `hold:695` | Yes | Yes |
| Peak Shaving Start Time 2 Thu | Schedules | `hold:698` | Yes | Yes |
| Peak Shaving End Time 2 Thu | Schedules | `hold:699` | Yes | Yes |
| Peak Shaving Start Time 1 Fri | Schedules | `hold:702` | Yes | Yes |
| Peak Shaving End Time 1 Fri | Schedules | `hold:703` | Yes | Yes |
| Peak Shaving Start Time 2 Fri | Schedules | `hold:706` | Yes | Yes |
| Peak Shaving End Time 2 Fri | Schedules | `hold:707` | Yes | Yes |
| Peak Shaving Start Time 1 Sat | Schedules | `hold:710` | Yes | Yes |
| Peak Shaving End Time 1 Sat | Schedules | `hold:711` | Yes | Yes |
| Peak Shaving Start Time 2 Sat | Schedules | `hold:714` | Yes | Yes |
| Peak Shaving End Time 2 Sat | Schedules | `hold:715` | Yes | Yes |
| Peak Shaving Start Time 1 Sun | Schedules | `hold:718` | Yes | Yes |
| Peak Shaving End Time 1 Sun | Schedules | `hold:719` | Yes | Yes |
| Peak Shaving Start Time 2 Sun | Schedules | `hold:722` | Yes | Yes |
| Peak Shaving End Time 2 Sun | Schedules | `hold:723` | Yes | Yes |
| Charge First Start Time | Battery | `hold:76` | Yes | Yes |
| Charge First End Time | Battery | `hold:77` | Yes | Yes |
| Charge First Start Time 1 | Battery | `hold:78` | Yes | Yes |
| Charge First End Time 1 | Battery | `hold:79` | Yes | Yes |
| Charge First Start Time 2 | Battery | `hold:80` | Yes | Yes |
| Charge First End Time 2 | Battery | `hold:81` | Yes | Yes |
| AC First Load Start Time 2 | Inverter | `hold:156` | Yes | Yes |
| AC First Load End Time 2 | Inverter | `hold:157` | Yes | Yes |
