"""Data sanity validation for Modbus register values."""
import logging

from ..constants.hold_registers import (
    H_AC_CHARGE_START_TIME, H_AC_CHARGE_END_TIME, H_AC_CHARGE_START_TIME_1, H_AC_CHARGE_END_TIME_1,
    H_AC_CHARGE_START_TIME_2, H_AC_CHARGE_END_TIME_2, H_AC_FIRST_START_TIME, H_AC_FIRST_END_TIME,
    H_AC_FIRST_START_TIME_1, H_AC_FIRST_END_TIME_1, H_PEAK_SHAVING_START_TIME, H_PEAK_SHAVING_END_TIME,
    H_PEAK_SHAVING_START_TIME_1, H_PEAK_SHAVING_END_TIME_1
)

_LOGGER = logging.getLogger(__name__)

HOLD_TIME_REGISTERS = {
    H_AC_CHARGE_START_TIME,
    H_AC_CHARGE_END_TIME,
    H_AC_CHARGE_START_TIME_1,
    H_AC_CHARGE_END_TIME_1,
    H_AC_CHARGE_START_TIME_2,
    H_AC_CHARGE_END_TIME_2,
    H_AC_FIRST_START_TIME,
    H_AC_FIRST_END_TIME,
    H_AC_FIRST_START_TIME_1,
    H_AC_FIRST_END_TIME_1,
    H_PEAK_SHAVING_START_TIME,
    H_PEAK_SHAVING_END_TIME,
    H_PEAK_SHAVING_START_TIME_1,
    H_PEAK_SHAVING_END_TIME_1,
}
INPUT_TIME_REGISTERS = set()


def is_data_sane(registers: dict, register_type: str) -> bool:
    """Performs a sanity check on key values to detect data corruption."""
    time_registers = HOLD_TIME_REGISTERS if register_type == "hold" else INPUT_TIME_REGISTERS

    for register, value in registers.items():
        if register in time_registers:
            # The value is packed as Hour | (Minute << 8)
            hour = value & 0xFF
            minute = (value >> 8) & 0xFF
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                _LOGGER.debug("Sanity check failed for %s register %s value: %s: H=%s, M=%s", register_type, register, value, hour, minute)
                return False
    return True
