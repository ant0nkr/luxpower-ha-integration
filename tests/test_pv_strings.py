"""Tests for PV string detection and the combined PV totals.

Issue #133: an inverter with 3 MPPTs still exposes PV4-PV6, and those unused inputs
reported stale non-zero energy that was being added into the combined totals, making
each inverter's "total" wrong by 92.8 kWh/day.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.const import DOMAIN
from custom_components.lxp_modbus.constants.hold_registers import H_PV_INPUT_MODEL
from custom_components.lxp_modbus.constants.input_registers import (
    I_EPV1_DAY, I_EPV2_DAY, I_EPV3_DAY, I_EPV4_DAY, I_EPV5_DAY, I_EPV6_DAY,
)
from custom_components.lxp_modbus.entity_descriptions.sensor_types import SENSOR_TYPES
from custom_components.lxp_modbus.sensor import ModbusBridgeSensor, _apply_pv_availability
from custom_components.lxp_modbus.utils import (
    ALL_PV_STRINGS, active_pv_strings, sum_pv_registers,
)

ENTRY_ID = "test_entry_id"


class TestActivePvStrings:
    """Hold register 20 has two conflicting mappings; only one value is ambiguous."""

    @pytest.mark.parametrize("value,expected", [
        (0, set()),
        (1, {1}),
        (2, {2}),
        (4, {1, 2}),
        (5, {1, 3}),      # only exists in the 12K mapping
        (6, {2, 3}),      # only exists in the 12K mapping
        (7, {1, 2, 3}),   # only exists in the 12K mapping
    ])
    def test_unambiguous_values(self, value, expected):
        assert active_pv_strings(value) == expected

    def test_value_three_is_treated_as_unknown(self):
        """The generic mapping calls 3 "PV1&2 parallel", the 12K mapping calls it PV3.

        Guessing would hide a working string, so it must report unknown.
        """
        assert active_pv_strings(3) is None

    def test_unknown_and_missing_values_are_unknown(self):
        assert active_pv_strings(99) is None
        assert active_pv_strings(None) is None

    def test_no_mapping_ever_claims_pv4_to_pv6(self):
        """No documented value implies a fourth string, which is the whole point."""
        for value in range(8):
            strings = active_pv_strings(value)
            if strings is not None:
                assert not (strings & {4, 5, 6})


class TestSumPvRegisters:
    def test_skips_absent_strings(self):
        registers = {10: 100, 11: 200, 12: 400}
        mapping = {1: 10, 2: 11, 3: 12}

        assert sum_pv_registers(registers, mapping, {1, 2}) == 300
        assert sum_pv_registers(registers, mapping, {1, 2, 3}) == 700
        assert sum_pv_registers(registers, mapping, set()) == 0

    def test_missing_register_counts_as_zero(self):
        assert sum_pv_registers({}, {1: 10}, {1}) == 0


class TestCombinedTotals:
    """The reporter's setup: 3 MPPTs in use, stale values on PV4 and PV5."""

    @pytest.fixture
    def coordinator(self):
        coord = MagicMock()
        coord.async_request_refresh = AsyncMock()
        coord.hass = MagicMock()
        coord.hass.data = {DOMAIN: {ENTRY_ID: {"write_lock": MagicMock()}}}
        coord.data = {
            "input": {
                I_EPV1_DAY: 100,   # 10.0 kWh
                I_EPV2_DAY: 50,    # 5.0 kWh
                I_EPV3_DAY: 25,    # 2.5 kWh
                I_EPV4_DAY: 800,   # phantom, 80.0 kWh/day as reported in #133
                I_EPV5_DAY: 128,   # phantom, 12.8 kWh/day
                I_EPV6_DAY: 0,
            },
            "hold": {H_PV_INPUT_MODEL: 7},   # PV1, PV2 and PV3 in use
        }
        return coord

    @pytest.fixture
    def entry(self):
        cfg = MagicMock()
        cfg.entry_id = ENTRY_ID
        cfg.title = "Test Inverter"
        cfg.data = {}
        return cfg

    def _energy_today(self, coordinator, entry):
        desc = next(d for d in SENSOR_TYPES if d.get("name") == "PV Energy Today")
        return ModbusBridgeSensor(coordinator, entry, dict(desc), "lxp", None)

    def test_phantom_strings_are_excluded(self, coordinator, entry):
        """17.5 kWh, not the 110.3 kWh the phantom strings would add."""
        assert self._energy_today(coordinator, entry).native_value == pytest.approx(17.5)

    def test_all_strings_summed_when_mapping_is_unknown(self, coordinator, entry):
        """Value 3 is ambiguous, so behaviour falls back to summing everything."""
        coordinator.data["hold"][H_PV_INPUT_MODEL] = 3

        assert self._energy_today(coordinator, entry).native_value == pytest.approx(110.3)

    def test_all_strings_summed_when_register_absent(self, coordinator, entry):
        """Older firmware may not report the register at all."""
        coordinator.data["hold"] = {}

        assert self._energy_today(coordinator, entry).native_value == pytest.approx(110.3)

    def test_two_string_inverter(self, coordinator, entry):
        """The reporter's second inverter uses 2 of 3 MPPTs."""
        coordinator.data["hold"][H_PV_INPUT_MODEL] = 4   # PV1 and PV2

        assert self._energy_today(coordinator, entry).native_value == pytest.approx(15.0)

    def test_combined_sensors_all_use_string_filtering(self):
        """Every combined PV sensor must filter, or the totals stay inconsistent."""
        combined = [d for d in SENSOR_TYPES
                    if d.get("name") in ("PV Power", "PV Energy Today", "PV Energy Total")]
        assert len(combined) == 3
        for desc in combined:
            assert "extract_pv" in desc, f"{desc['name']} still sums every string"


class TestEntityGating:
    """Per-string entities for absent inputs are disabled, never silently dropped."""

    def test_absent_strings_are_disabled(self):
        desc = {"name": "PV4 Power", "enabled": True}

        assert _apply_pv_availability(desc, frozenset({1, 2, 3}))["enabled"] is False

    def test_present_strings_untouched(self):
        desc = {"name": "PV2 Power", "enabled": True}

        assert _apply_pv_availability(desc, frozenset({1, 2, 3})) is desc

    def test_unknown_mapping_changes_nothing(self):
        """Never hide a sensor on a mapping we cannot interpret."""
        desc = {"name": "PV4 Power", "enabled": True}

        assert _apply_pv_availability(desc, None) is desc

    def test_non_pv_sensors_untouched(self):
        desc = {"name": "Battery Voltage", "enabled": True}

        assert _apply_pv_availability(desc, frozenset({1})) is desc

    def test_combined_pv_sensor_is_not_gated(self):
        """"PV Power" has no string number and must never be disabled."""
        desc = {"name": "PV Power", "enabled": True}

        assert _apply_pv_availability(desc, frozenset({1})) is desc

    def test_all_pv_strings_constant(self):
        assert ALL_PV_STRINGS == frozenset({1, 2, 3, 4, 5, 6})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
