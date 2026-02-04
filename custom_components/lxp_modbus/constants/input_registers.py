#
# Luxpower Inverter Modbus RTU Protocol - Input Registers
#
# This file contains constants for the Input Register addresses.
# These registers are read-only (Function Code 0x04).
#

# --- Core Status & PV Information ---
I_STATE = 0  # Inverter operational state. See operation mode definition.
I_VPV1 = 1  # PV1 voltage (Unit: 0.1V).
I_VPV2 = 2  # PV2 voltage (Unit: 0.1V).
I_VPV3 = 3  # PV3 voltage (Unit: 0.1V).
I_VBAT = 4  # Battery voltage (Unit: 0.1V).
I_SOC_SOH = 5  # Battery State of Charge (SOC) and State of Health (SOH) (Unit: %).
I_INTERNAL_FAULT = 6  # Internal Fault Code. See fault code definition file.
I_PPV1 = 7  # PV1 power (Unit: W).
I_PPV2 = 8  # PV2 power (Unit: W).
I_PPV3 = 9  # PV3 power (or total PV power) (Unit: W).
I_PCHARGE = 10  # Battery charging power (power flowing into the battery) (Unit: W).
I_PDISCHARGE = 11  # Battery discharging power (power flowing out of the battery) (Unit: W).

# --- Grid Information ---
I_VAC_R = 12  # R-phase utility grid voltage (Unit: 0.1V).
I_VAC_S = 13  # S-phase utility grid voltage (Unit: 0.1V).
I_VAC_T = 14  # T-phase utility grid voltage (Unit: 0.1V).
I_FAC = 15  # Utility grid frequency (Unit: 0.01Hz).
I_PINV_PREC = 16  # On-grid inverter power (Pinv) and AC charging rectification power (Prec) (Unit: W).
I_PINV = 16  # Alias for On-grid inverter power (R-phase for 3-phase systems).
I_PREC = 17  # Alias for AC charging power (R-phase for 3-phase systems).
I_IINV_RMS = 18  # Inverter RMS current output (R-phase for 3-phase systems) (Unit: 0.01A).
I_PF = 19  # Power factor (R-phase for 3-phase systems) (Unit: 0.001).
I_PTOGRID = 26  # User on-grid power (export) (R-phase for 3-phase systems) (Unit: W).
I_PTOUSER = 27  # Grid power supplied to user (import) (R-phase for 3-phase systems) (Unit: W).

# --- EPS (Off-Grid) Information ---
I_VEPS_R = 20  # R-phase off-grid output voltage (Unit: 0.1V).
I_VEPS_S = 21  # S-phase off-grid output voltage (Unit: 0.1V).
I_VEPS_T = 22  # T-phase off-grid output voltage (Unit: 0.1V).
I_FEPS = 23  # Off-grid output frequency (Unit: 0.01Hz).
I_PEPS = 24  # Off-grid inverter power (R-phase for 3-phase systems) (Unit: W).
I_SEPS = 25  # Off-grid apparent power (R-phase for 3-phase systems) (Unit: VA).

# --- Daily Energy Totals ---
I_EPV1_DAY = 28  # PV1 power generation today (Unit: 0.1kWh).
I_EPV2_DAY = 29  # PV2 power generation today (Unit: 0.1kWh).
I_EPV3_DAY = 30  # PV3 power generation today (or total PV) (Unit: 0.1kWh).
I_EINV_DAY = 31  # Today's on-grid inverter output energy (Unit: 0.1kWh).
I_EREC_DAY = 32  # Today's AC charging rectifier energy (Unit: 0.1kWh).
I_ECHG_DAY = 33  # Energy charged to battery today (Unit: 0.1kWh).
I_EDISCHG_DAY = 34  # Energy discharged from battery today (Unit: 0.1kWh).
I_EEPS_DAY = 35  # Today's off-grid output energy (Unit: 0.1kWh).
I_ETOGRID_DAY = 36  # Today's export to grid energy (Unit: 0.1kWh).
I_ETOUSER_DAY = 37  # Today's import from grid energy (Unit: 0.1kWh).
I_EGEN_DAY = 124 # Energy from generator today (Unit: 0.1kWh).
I_ELOAD_DAY = 171 # Load energy consumption for today (Unit: 0.1kWh).

# --- System & Bus Voltages ---
I_VBUS1 = 38  # Voltage of Bus 1 (Unit: 0.1V).
I_VBUS2 = 39  # Voltage of Bus 2 (Unit: 0.1V).
I_VBUS_P = 120 # Half BUS voltage (Unit: 0.1V).

# --- Cumulative Energy Totals (32-bit values) ---
I_EPV1_ALL_L = 40  # PV1 cumulative power generation, Low byte (Unit: 0.1kWh).
I_EPV1_ALL_H = 41  # PV1 cumulative power generation, High byte (Unit: 0.1kWh).
I_EPV2_ALL_L = 42  # PV2 cumulative power generation, Low byte (Unit: 0.1kWh).
I_EPV2_ALL_H = 43  # PV2 cumulative power generation, High byte (Unit: 0.1kWh).
I_EPV3_ALL_L = 44  # PV3 (or total) cumulative power generation, Low byte (Unit: 0.1kWh).
I_EPV3_ALL_H = 45  # PV3 (or total) cumulative power generation, High byte (Unit: 0.1kWh).
I_EINV_ALL_L = 46  # Inverter output accumulated power, Low byte (Unit: 0.1kWh).
I_EINV_ALL_H = 47  # Inverter output accumulated power, High byte (Unit: 0.1kWh).
I_EREC_ALL_L = 48  # AC charging accumulated power, Low byte (Unit: 0.1kWh).
I_EREC_ALL_H = 49  # AC charging accumulated power, High byte (Unit: 0.1kWh).
I_ECHG_ALL_L = 50  # Cumulative charge energy, Low byte (Unit: 0.1kWh).
I_ECHG_ALL_H = 51  # Cumulative charge energy, High byte (Unit: 0.1kWh).
I_EDISCHG_ALL_L = 52  # Cumulative discharge energy, Low byte (Unit: 0.1kWh).
I_EDISCHG_ALL_H = 53  # Cumulative discharge energy, High byte (Unit: 0.1kWh).
I_EEPS_ALL_L = 54  # Cumulative off-grid output energy, Low byte (Unit: 0.1kWh).
I_EEPS_ALL_H = 55  # Cumulative off-grid output energy, High byte (Unit: 0.1kWh).
I_ETOGRID_ALL_L = 56  # Accumulated export energy, Low byte (Unit: 0.1kWh).
I_ETOGRID_ALL_H = 57  # Accumulated export energy, High byte (Unit: 0.1kWh).
I_ETOUSER_ALL_L = 58  # Cumulative import energy, Low byte (Unit: 0.1kWh).
I_ETOUSER_ALL_H = 59  # Cumulative import energy, High byte (Unit: 0.1kWh).
I_EGEN_ALL_L = 125 # Total generator energy, Low byte (Unit: 0.1kWh).
I_EGEN_ALL_H = 126 # Total generator energy, High byte (Unit: 0.1kWh).
I_ELOAD_ALL_L = 172 # Total load energy, Low byte (Unit: 0.1kWh).
I_ELOAD_ALL_H = 173 # Total load energy, High byte (Unit: 0.1kWh).

# --- Fault & Warning Codes (32-bit values) ---
I_FAULT_CODE_L = 60  # Fault Code, Low byte. See fault code definition file.
I_FAULT_CODE_H = 61  # Fault Code, High byte.
I_WARNING_CODE_L = 62  # Warning Code, Low byte. See alarm code definition file.
I_WARNING_CODE_H = 63  # Warning Code, High byte.

# --- Temperature & Runtime ---
I_TINNER = 64  # Internal temperature (Unit: °C).
I_TRADIATOR1 = 65  # Radiator temperature 1 (Unit: °C).
I_TRADIATOR2 = 66  # Radiator temperature 2 (Unit: °C).
I_TBAT = 67  # Battery temperature (Unit: °C).
# Register 68 is not defined in the Input Register table.
I_RUNNING_TIME_L = 69 # Total runtime duration, Low byte (Unit: second).
I_RUNNING_TIME_H = 70 # Total runtime duration, High byte (Unit: second).

# --- Auto Test & System Status ---
I_AUTO_TEST_STATUS = 71 # Auto test status register (Unit: bitfield, Range: 0-65535).
# Bit 0-3: AutoTestStart (0:not started, 1:started)
# Bit 4-7: UbAutoTestStatus (0:waiting, 1:testing, 2:fail, 3:V test OK, 4:F test OK, 5:pass)
# Bit 8-11: UbAutoTestStep (1:V1L, 2:V1H...)
I_W_AUTO_TEST_LIMIT = 72 # Voltage/Frequency limit for auto test (Unit: 0.1V / 0.01Hz).
I_UW_AUTO_TEST_DEFAULT_TIME = 73 # Default time for auto test (Unit: ms).
I_UW_AUTO_TEST_TRIP_VALUE = 74 # Trip value for auto test (Unit: 0.1V / 0.01Hz).
I_UW_AUTO_TEST_TRIP_TIME = 75 # Trip time for auto test (Unit: ms).
# Register 76 is not defined in the Input Register table.
I_AC_INPUT_TYPE_FLAGS = 77 # Flags for AC Input Type, AC Couple Flow, etc.
# Bit 0: ACInputType (0:Grid, 1:Generator)
# Bit 1: ACCoupleInverterFlow (0:no flow, 1:show flow)
# Bit 2: ACCoupleEn (0:Disable, 1:Enable)
# Registers 78-112 are not defined in the Input Register table.
I_MASTER_SLAVE_PARALLEL_STATUS = 113
# Bit 0-1: MasterOrSlave (1:Master, 2:Slave)
# Bit 2-3: SingleOrThreePhase (1:R, 2:S, 3:T)
# Bit 4-5: Phases sequence (0:Positive, 1:Negative)
# Bit 8-16: ParallelNum
I_SWITCH_STATE = 174 # DIP switch status and other flags (Unit: bitfield, Range: 0-65535).
# Bit 0-4: SafetySw (Status of 5-digit safety DIP switch)

# --- BMS Information ---
# --- BMS Information ---
I_BAT_TYPE_AND_BRAND = 80 # Battery type and brand. See model definition file.
I_BMS_MAX_CHG_CURR = 81 # Corrected Address: Max charging current limited by BMS (Unit: 0.01A).
I_BMS_MAX_DISCHG_CURR = 82 # Corrected Address: Max discharging current limited by BMS (Unit: 0.01A).
I_BMS_CHARGE_VOLT_REF = 83 # Recommended charging voltage by BMS (Unit: 0.1V).
I_BMS_DISCHG_CUT_VOLT = 84 # Recommended discharging cut-off voltage by BMS (Unit: 0.1V).
I_BMS_BAT_STATUS_0 = 85 # Status information from BMS.
I_BMS_BAT_STATUS_1 = 86 # Status information from BMS.
I_BMS_BAT_STATUS_2 = 87 # Status information from BMS.
I_BMS_BAT_STATUS_3 = 88 # Status information from BMS.
I_BMS_BAT_STATUS_4 = 89 # Status information from BMS.
I_BMS_BAT_STATUS_5 = 90 # Status information from BMS.
I_BMS_BAT_STATUS_6 = 91 # Status information from BMS.
I_BMS_BAT_STATUS_7 = 92 # Status information from BMS.
I_BMS_BAT_STATUS_8 = 93 # Status information from BMS.
I_BMS_BAT_STATUS_9 = 94 # Status information from BMS.
I_BMS_BAT_STATUS_INV = 95 # Aggregated lithium battery status by inverter
I_BAT_PARALLEL_NUM = 96 # Number of batteries in parallel.
I_BAT_CAPACITY = 97 # Battery capacity (Unit: Ah).
I_BMS_BAT_CURRENT = 98 # Battery current from BMS (signed number) (Unit: 0.01A).
I_BMS_FAULT_CODE = 99 # Fault code from BMS.
I_BMS_WARNING_CODE = 100 # Warning code from BMS.
I_BMS_MAX_CELL_VOLT = 101 # Maximum voltage of a cell (Unit: 0.001V).
I_BMS_MIN_CELL_VOLT = 102 # Minimum voltage of a cell (Unit: 0.001V).
I_BMS_MAX_CELL_TEMP = 103 # Maximum temperature of a cell (signed number) (Unit: 0.1°C).
I_BMS_MIN_CELL_TEMP = 104 # Minimum temperature of a cell (signed number) (Unit: 0.1°C).
I_BMS_FW_UPDATE_STATE = 105 # BMS Firmware Update State (1:in process, 2:success, 3:failed).
I_BMS_CYCLE_COUNT = 106 # Number of charging/discharging cycles from BMS.
I_INV_BAT_VOLT_SAMPLE = 107 # Inverter's sample of the battery voltage (Unit: 0.1V).

# --- Three-Phase & US Model Specific ---
I_PINV_S = 180 # On-grid inverter power of S-phase (Unit: W).
I_PINV_T = 181 # On-grid inverter power of T-phase (Unit: W).
I_PREC_S = 182 # Charging rectification power of S-phase (Unit: W).
I_PREC_T = 183 # Charging rectification power of T-phase (Unit: W).
I_PTOGRID_S = 184 # User on-grid power of S-phase (Unit: W).
I_PTOGRID_T = 185 # User on-grid power of T-phase (Unit: W).
I_PTOUSER_S = 186 # Grid supply power of S-phase (Unit: W).
I_PTOUSER_T = 187 # Grid supply power of T-phase (Unit: W).
I_IINV_RMS_S = 190 # RMS current of S-phase (Unit: 0.01A).
I_IINV_RMS_T = 191 # RMS current of T-phase (Unit: 0.01A).
I_PF_S = 192 # Power factor of S-phase (Unit: 0.001).
I_PF_T = 205 # Power factor of T-phase (Unit: 0.001).

# --- Split Phase Specific - US / BR models ---
I_GRID_VOLT_L1N = 193 # Voltage of Grid L1N (for US model) (Unit: 0.1V).
I_GRID_VOLT_L2N = 194 # Voltage of Grid L2N (for US model) (Unit: 0.1V).
I_GEN_VOLT_L1N = 195 # Voltage of Generator L1N (for US model) (Unit: 0.1V).
I_GEN_VOLT_L2N = 196 # Voltage of Generator L2N (for US model) (Unit: 0.1V).
I_PINV_L1N = 197 # Inverting power of phase L1N (for US model) (Unit: W).
I_PINV_L2N = 198 # Inverting power of phase L2N (for US model) (Unit: W).
I_PREC_L1N = 199 # Rectifying power of phase L1N (for US model) (Unit: W).
I_PREC_L2N = 200 # Rectifying power of phase L2N (for US model) (Unit: W).
I_PTOGRID_L1N = 201 # Grid export power of phase L1N (for US model) (Unit: W).
I_PTOGRID_L2N = 202 # Grid export power of phase L2N (for US model) (Unit: W).
I_PTOUSER_L1N = 203 # Grid import power of phase L1N (for US model) (Unit: W).
I_PTOUSER_L2N = 204 # Grid import power of phase L2N (for US model) (Unit: W).

I_EPS_VOLT_L1N = 127 # Voltage of EPS L1N (for US model) (Unit: 0.1V).
I_EPS_VOLT_L2N = 128 # Voltage of EPS L1N (for US model) (Unit: 0.1V).

# This registers appear to have different content if is a split-phase or a tri-phase inverter (need testing)
I_PEPS_L1N = 129 # Active Power of EPS L1N (for US model) (Unit: W)
I_PEPS_L2N = 130 # Active Power of EPS L2N (for US model) (Unit: W)
I_SEPS_L1N = 131 # Apparent Power of EPS L1N (for US model) (Unit: VA)
I_SEPS_L2N = 132 # Apparent Power of EPS L2N (for US model) (Unit: VA)
I_EEPS_L1N_DAY = 133 # Daily energy of EPS L1N (for US model) (Unit: 0.1kWh)
I_EEPS_L2N_DAY = 134 # Daily energy of EPS L2N (for US model) (Unit: 0.1kWh)
I_EEPS_L1N_ALL_L = 135 # Total energy of EPS L1N (for US model) Low byte (Unit: 0.1kWh)
I_EEPS_L1N_ALL_H = 136 # Total energy of EPS L1N (for US model) High byte (Unit: 0.1kWh)
I_EEPS_L2N_ALL_L = 137 # Total energy of EPS L2N (for US model) Low byte (Unit: 0.1kWh)
I_EEPS_L2N_ALL_H = 138 # Total energy of EPS L2N (for US model) High byte (Unit: 0.1kWh)

# --- Miscellaneous ---
I_ONGRID_LOAD_POWER = 114 # Load power when not off-grid (for 12k inverter) (Unit: W).
I_SERIAL_NUMBER_0_3 = 115 # Serial Number ASCII chars [0] through [3].
I_SERIAL_NUMBER_4_5 = 116 # Serial Number ASCII chars [4] and [5].
I_SERIAL_NUMBER_6_7 = 117 # Serial Number ASCII chars [6] and [7].
I_SERIAL_NUMBER_8_9 = 118 # Serial Number ASCII chars [8] and [9]. (Note: Doc shows 119 for [8] and [9])
# Registers 119-120 are not defined in the Input Register table.
I_GEN_VOLT = 121 # Generator voltage (Unit: 0.1V).
I_GEN_FREQ = 122 # Generator frequency (Unit: 0.01Hz).
I_GEN_POWER = 123 # Generator power (Unit: W).
I_QINV = 139 # Reactive power (Unit: Var).
I_PLOAD = 170 # Load consumption when working in on-grid mode (Unit: W).

# --- Added in V23 (2025-06-14) ---

# Additional AC Couple Power
I_AC_COUPLE_POWER = 153 # AC Couple Power (Unit: W, Range: -32768-32767).
I_AC_COUPLE_POWER_S = 206 # AC Couple Power S-phase (Unit: W, Range: -32768-32767).
I_AC_COUPLE_POWER_T = 207 # AC Couple Power T-phase (Unit: W, Range: -32768-32767).

# One-Click Charging
I_REMAINING_CHARGE_TIME = 210 # Remaining charge time for one-click charging (Unit: min, Range: 0-65535).

# Additional Temperature Sensors
I_TEMP_NTC_FOR_INDC = 214 # NTC temperature for INDC (Unit: °C, Range: -40-125).
I_TEMP_NTC_FOR_DCDCL = 215 # NTC temperature for DCDCL (Unit: °C, Range: -40-125).
I_TEMP_NTC_FOR_DCDCH = 216 # NTC temperature for DCDCH (Unit: °C, Range: -40-125).

# Additional PV Strings (PV4, PV5, PV6)
I_VPV4 = 217 # PV4 voltage (Unit: 0.1V, Range: 0-6553.5V).
I_VPV5 = 218 # PV5 voltage (Unit: 0.1V, Range: 0-6553.5V).
I_VPV6 = 219 # PV6 voltage (Unit: 0.1V, Range: 0-6553.5V).
I_PPV4 = 220 # PV4 power (Unit: W, Range: 0-65535).
I_PPV5 = 221 # PV5 power (Unit: W, Range: 0-65535).
I_PPV6 = 222 # PV6 power (Unit: W, Range: 0-65535).
I_EPV4_DAY = 223 # PV4 daily energy generation (Unit: 0.1kWh, Range: 0-6553.5kWh).
I_EPV4_ALL_L = 224 # PV4 total energy generation, Low byte (Unit: 0.1kWh).
I_EPV4_ALL_H = 225 # PV4 total energy generation, High byte (Unit: 0.1kWh).
I_EPV5_DAY = 226 # PV5 daily energy generation (Unit: 0.1kWh, Range: 0-6553.5kWh).
I_EPV5_ALL_L = 227 # PV5 total energy generation, Low byte (Unit: 0.1kWh).
I_EPV5_ALL_H = 228 # PV5 total energy generation, High byte (Unit: 0.1kWh).
I_EPV6_DAY = 229 # PV6 daily energy generation (Unit: 0.1kWh, Range: 0-6553.5kWh).
I_EPV6_ALL_L = 230 # PV6 total energy generation, Low byte (Unit: 0.1kWh).
I_EPV6_ALL_H = 231 # PV6 total energy generation, High byte (Unit: 0.1kWh).

# Smart Load
I_SMART_LOAD_POWER = 232 # Smart Load power consumption (Unit: W, Range: 0-65535).