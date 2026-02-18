"""Tests for the data_validator module."""

import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.classes.data_validator import (
    is_data_sane,
    HOLD_TIME_REGISTERS,
    INPUT_TIME_REGISTERS,
)
from custom_components.lxp_modbus.constants.hold_registers import (
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
)


def _encode_time(hour, minute):
    """Encode hour and minute into the packed register format: Hour | (Minute << 8)."""
    return hour | (minute << 8)


class TestHoldTimeRegisters:
    """Test cases for the HOLD_TIME_REGISTERS set."""

    def test_hold_time_registers_contains_expected_registers(self):
        """HOLD_TIME_REGISTERS contains all 14 expected time register addresses."""
        expected = {
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
        assert HOLD_TIME_REGISTERS == expected
        assert len(HOLD_TIME_REGISTERS) == 14

    def test_input_time_registers_is_empty(self):
        """INPUT_TIME_REGISTERS is an empty set."""
        assert INPUT_TIME_REGISTERS == set()
        assert len(INPUT_TIME_REGISTERS) == 0


class TestIsDataSane:
    """Test cases for the is_data_sane function."""

    # --- Valid hold time values ---

    def test_valid_hold_time_values(self):
        """Valid time values in hold registers pass the sanity check."""
        registers = {
            H_AC_CHARGE_START_TIME: _encode_time(8, 10),   # 08:10
            H_AC_CHARGE_END_TIME: _encode_time(22, 30),    # 22:30
            100: 12345,                                     # non-time register
        }
        assert is_data_sane(registers, "hold") is True

    # --- Invalid hour (>23) ---

    def test_invalid_hour_above_23(self):
        """Hour value of 24 causes the sanity check to fail."""
        registers = {
            H_AC_CHARGE_START_TIME: _encode_time(24, 10),  # hour=24, invalid
        }
        assert is_data_sane(registers, "hold") is False

    def test_invalid_hour_255(self):
        """Hour value of 255 (max byte) causes the sanity check to fail."""
        registers = {
            H_AC_CHARGE_START_TIME: _encode_time(255, 0),
        }
        assert is_data_sane(registers, "hold") is False

    # --- Invalid minute (>59) ---

    def test_invalid_minute_above_59(self):
        """Minute value of 60 causes the sanity check to fail."""
        registers = {
            H_AC_CHARGE_START_TIME: _encode_time(8, 60),  # minute=60, invalid
        }
        assert is_data_sane(registers, "hold") is False

    def test_invalid_minute_255(self):
        """Minute value of 255 (max byte) causes the sanity check to fail."""
        registers = {
            H_AC_CHARGE_START_TIME: _encode_time(0, 255),
        }
        assert is_data_sane(registers, "hold") is False

    # --- Boundary valid: 23:59 and 0:00 ---

    def test_boundary_valid_23_59(self):
        """23:59 is the maximum valid time and passes the sanity check."""
        registers = {
            H_AC_CHARGE_START_TIME: _encode_time(23, 59),
        }
        assert is_data_sane(registers, "hold") is True

    def test_boundary_valid_0_00(self):
        """00:00 is the minimum valid time and passes the sanity check."""
        registers = {
            H_AC_CHARGE_END_TIME: _encode_time(0, 0),
        }
        assert is_data_sane(registers, "hold") is True

    def test_boundary_both_extremes(self):
        """Both 23:59 and 00:00 in the same dict pass together."""
        registers = {
            H_AC_CHARGE_START_TIME: _encode_time(23, 59),
            H_AC_CHARGE_END_TIME: _encode_time(0, 0),
        }
        assert is_data_sane(registers, "hold") is True

    # --- Non-time registers always pass ---

    def test_non_time_registers_always_pass(self):
        """Registers not in HOLD_TIME_REGISTERS are never validated as time."""
        registers = {
            100: 12345,
            200: 67890,
            300: 0xFFFF,  # would be invalid as a time, but it is not a time register
        }
        assert is_data_sane(registers, "hold") is True

    def test_non_time_register_with_garbage_value(self):
        """A non-time register with an absurd value still passes."""
        registers = {
            999: 0xFFFF,
        }
        assert is_data_sane(registers, "hold") is True

    # --- Input registers always pass (no time registers) ---

    def test_input_registers_always_pass(self):
        """Input register type has no time registers, so all values pass."""
        registers = {
            100: 12345,
            200: 67890,
        }
        assert is_data_sane(registers, "input") is True

    def test_input_registers_with_hold_time_address_still_pass(self):
        """Even if an input register uses a hold time register address, it passes
        because INPUT_TIME_REGISTERS is empty."""
        registers = {
            H_AC_CHARGE_START_TIME: _encode_time(99, 99),  # would fail as hold
        }
        assert is_data_sane(registers, "input") is True

    # --- Empty dict passes ---

    def test_empty_dict_passes(self):
        """An empty register dict passes for hold type."""
        assert is_data_sane({}, "hold") is True

    def test_empty_dict_passes_input(self):
        """An empty register dict passes for input type."""
        assert is_data_sane({}, "input") is True

    # --- Multiple time registers, one invalid fails all ---

    def test_multiple_time_registers_one_invalid_fails_all(self):
        """If any single time register has an invalid value, the whole check fails."""
        registers = {
            H_AC_CHARGE_START_TIME: _encode_time(8, 30),    # valid
            H_AC_CHARGE_END_TIME: _encode_time(22, 0),      # valid
            H_AC_CHARGE_START_TIME_1: _encode_time(25, 0),   # invalid hour
            H_AC_CHARGE_END_TIME_1: _encode_time(12, 45),    # valid
        }
        assert is_data_sane(registers, "hold") is False

    def test_multiple_time_registers_last_one_invalid(self):
        """Even if only the last time register is invalid, the check still fails."""
        registers = {
            H_AC_CHARGE_START_TIME: _encode_time(6, 0),
            H_AC_CHARGE_END_TIME: _encode_time(7, 30),
            H_AC_FIRST_START_TIME: _encode_time(12, 0),
            H_AC_FIRST_END_TIME: _encode_time(14, 0),
            H_PEAK_SHAVING_END_TIME_1: _encode_time(10, 61),  # invalid minute
        }
        assert is_data_sane(registers, "hold") is False

    def test_multiple_time_registers_all_valid(self):
        """All time registers with valid values pass."""
        registers = {
            H_AC_CHARGE_START_TIME: _encode_time(6, 0),
            H_AC_CHARGE_END_TIME: _encode_time(7, 30),
            H_AC_FIRST_START_TIME: _encode_time(12, 0),
            H_AC_FIRST_END_TIME: _encode_time(14, 0),
            H_PEAK_SHAVING_START_TIME: _encode_time(17, 0),
            H_PEAK_SHAVING_END_TIME: _encode_time(19, 30),
        }
        assert is_data_sane(registers, "hold") is True

    # --- All 14 hold time registers individually tested ---

    ALL_14_TIME_REGISTERS = [
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
    ]

    @pytest.mark.parametrize("register", ALL_14_TIME_REGISTERS, ids=[
        "H_AC_CHARGE_START_TIME",
        "H_AC_CHARGE_END_TIME",
        "H_AC_CHARGE_START_TIME_1",
        "H_AC_CHARGE_END_TIME_1",
        "H_AC_CHARGE_START_TIME_2",
        "H_AC_CHARGE_END_TIME_2",
        "H_AC_FIRST_START_TIME",
        "H_AC_FIRST_END_TIME",
        "H_AC_FIRST_START_TIME_1",
        "H_AC_FIRST_END_TIME_1",
        "H_PEAK_SHAVING_START_TIME",
        "H_PEAK_SHAVING_END_TIME",
        "H_PEAK_SHAVING_START_TIME_1",
        "H_PEAK_SHAVING_END_TIME_1",
    ])
    def test_each_time_register_valid_value_passes(self, register):
        """Each of the 14 time registers accepts a valid time value."""
        registers = {register: _encode_time(12, 30)}
        assert is_data_sane(registers, "hold") is True

    @pytest.mark.parametrize("register", ALL_14_TIME_REGISTERS, ids=[
        "H_AC_CHARGE_START_TIME",
        "H_AC_CHARGE_END_TIME",
        "H_AC_CHARGE_START_TIME_1",
        "H_AC_CHARGE_END_TIME_1",
        "H_AC_CHARGE_START_TIME_2",
        "H_AC_CHARGE_END_TIME_2",
        "H_AC_FIRST_START_TIME",
        "H_AC_FIRST_END_TIME",
        "H_AC_FIRST_START_TIME_1",
        "H_AC_FIRST_END_TIME_1",
        "H_PEAK_SHAVING_START_TIME",
        "H_PEAK_SHAVING_END_TIME",
        "H_PEAK_SHAVING_START_TIME_1",
        "H_PEAK_SHAVING_END_TIME_1",
    ])
    def test_each_time_register_invalid_value_fails(self, register):
        """Each of the 14 time registers rejects an invalid time value."""
        registers = {register: _encode_time(25, 61)}  # both hour and minute invalid
        assert is_data_sane(registers, "hold") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
