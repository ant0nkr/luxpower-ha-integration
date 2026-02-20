🚀 v1.0.0 — Major Architecture Refactoring & Protocol V23 Update
🏗️ Architecture Refactoring
SOLID / Clean Architecture Overhaul
Decomposed monolithic modbus_client.py into focused, single-responsibility modules
Extracted ModbusConnectionManager — TCP connection lifecycle management with timeout handling
Extracted PacketRecoveryHandler — malformed packet detection and recovery with statistics tracking
Extracted DataValidator — register data sanity validation (time registers, voltage/frequency bounds)
Extracted InverterDiscovery — inverter serial number discovery from config_flow.py
Extracted DataUpdateCoordinator — Home Assistant coordinator pattern from __init__.py
Simplified __init__.py from 240+ lines to ~135 lines of clean setup orchestration
Removed legacy register_bits.py (functionality consolidated into utils.py)
📊 Protocol V23 Register Updates
New Input Registers (7 added)

I_EXCEPTION_REASON_1 (176) — 3-phase grid-on exit reasons
I_EXCEPTION_REASON_2 (177) — 3-phase EPS/charge/discharge exit reasons
I_CHG_DISCHG_DISABLE_REASON (178) — charge/discharge disable reason bits
I_GEN_POWER_S (188), I_GEN_POWER_T (189) — 3-phase generator power
I_ONGRID_LOAD_POWER_S (208), I_ONGRID_LOAD_POWER_T (209) — 3-phase on-grid load power
Register Comment Fixes

Fixed H_GRID_PEAK_SHAVING_POWER_1 unit: W → 0.1kW, range: 0-65535 → 0-255
Fixed I_REMAINING_CHARGE_TIME unit: min → s (seconds)
Updated H_WATTNODE_CT_DIRECTIONS to document WattNode update frequency bits (3-5)
New Warning Code

Added W010 "Grid overload" (Trip6-20k models)
🐛 Bug Fixes
Fixed Warning Code Byte Swap Bug
Warning code extraction had L and H registers swapped, causing incorrect warning code reporting
Corrected (I_WARNING_CODE_L << 16) | I_WARNING_CODE_H → (I_WARNING_CODE_H << 16) | I_WARNING_CODE_L
⚡ New Entities (~130 added)
Number Entities (~100 new)

Power Rate Settings — charge/discharge power rates (legacy + precise), reactive power %, PF command
Charge First / Forced Discharge — power limits, SOC limits, end voltages with combined register extraction
Grid Protection Limits — voltage L1-L3 low/high/time, frequency L1-L3 low/high/time, moving average window
Frequency Derate — over/under frequency start/end points, derate ratios, activation delays
Q(V)/VoltWatt/PF Curves — QV curve points (V1-V4, Q1-Q4), VoltWatt settings, PF lock-in/out
Lead-Acid & Battery Config — charge/discharge voltage refs, temperature limits, derating curves, SOC calibration
Smart Load — on/off voltage and SOC thresholds
AC Coupling — start/end SOC and voltage thresholds
Peak Shaving Extended — voltage, SOC, and power thresholds
Miscellaneous — start charge threshold, load compensate, AFCI settings, generator cool-down, equalization voltage
Sensor Entities (~24 new)

Three-Phase S/T Power Sensors (14) — inverter power, rectification, grid export/import, generator power, current, power factor, on-grid load for S and T phases
Diagnostic Sensors (8) — battery type/brand, BMS FW update state, DIP switch state, exception reasons 1/2, charge/discharge disable reason, auto test status
Remaining One-Click Charge Time duplicate removed
Time Entities (6 new) — charge first end times, charge first start/end time 2, AC first load start/end time 2

Button Entities (2 new) — Clear Parallel Alarm, Reset G100 Lockout

🧪 Testing
4 New Test Modules Added
test_coordinator.py — DataUpdateCoordinator lifecycle and error handling
test_connection_manager.py — TCP connection, timeout, and close behavior
test_data_validator.py — register data sanity validation edge cases
test_packet_recovery.py — malformed packet detection, recovery, and statistics
All 124 tests passing
🎯 What's New
This is a major release that brings a comprehensive architecture overhaul alongside full Modbus Protocol V23 support. The codebase has been refactored following SOLID principles — extracting connection management, packet recovery, data validation, and coordinator logic into focused modules, improving maintainability and testability. Over 130 previously unexposed registers are now available as Home Assistant entities, organized into logical device groups (Grid, Battery, Smart Load, AC Coupling, etc.). A critical warning code byte-swap bug has been fixed, and 4 new test modules ensure robust coverage of the refactored components.

📈 Statistics
Metric	Count
Files changed	31
Lines added	4,115
Lines removed	483
New entities	~130
Total entities	703
Tests passing	124
Full Changelog: main...code-refactoring

There you go! The release notes follow the 0.2.2/0.2.3 style with emoji section headers, bold feature names with descriptions, organized by feature area, and a statistics summary. Let me know if you'd like any adjustments to the wording or structure.