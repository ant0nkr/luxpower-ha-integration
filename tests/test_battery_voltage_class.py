"""Tests for scaling battery voltage limits to 12 V and 24 V systems.

Issue #134: on a 24 V GETA-LB-EU, setting 25.6 V was refused with
"Value 25.6 for number.<...>_ac_charge_start_voltage is outside valid range
38.5 - 52.0", because every voltage limit was written for a 48 V battery.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.const import (
    BATTERY_VOLTAGE_CLASSES,
    CONF_BATTERY_VOLTAGE_CLASS,
    DEFAULT_BATTERY_VOLTAGE_CLASS,
    DOMAIN,
    REFERENCE_BATTERY_VOLTAGE_CLASS,
)
from custom_components.lxp_modbus.entity_descriptions.number_types import NUMBER_TYPES
from custom_components.lxp_modbus.number import ModbusBridgeNumber

ENTRY_ID = "test_entry_id"

# The entity from the issue: AC Charge Start Voltage, 38.5-52.0 at 48 V
AC_CHARGE_START = {
    "name": "AC Charge Start Voltage",
    "register": 158,
    "register_type": "hold",
    "min": 38.5,
    "max": 52.0,
    "step": 0.1,
    "unit": "V",
    "battery_voltage": True,
    "multiplier": 10,
    "master_only": False,
}

GRID_VOLTAGE = {
    "name": "Grid Voltage Low Limit",
    "register": 25,
    "register_type": "hold",
    "min": 0.0,
    "max": 6553.5,
    "step": 0.1,
    "unit": "V",
    "multiplier": 10,
    "master_only": False,
}


@pytest.fixture
def coordinator():
    coord = MagicMock()
    coord.data = {"hold": {}, "input": {}}
    coord.async_request_refresh = AsyncMock()
    coord.hass = MagicMock()
    coord.hass.data = {DOMAIN: {ENTRY_ID: {"write_lock": asyncio.Lock()}}}
    return coord


def make_entry(voltage_class=None):
    cfg = MagicMock()
    cfg.entry_id = ENTRY_ID
    cfg.title = "Test Inverter"
    cfg.data = {} if voltage_class is None else {CONF_BATTERY_VOLTAGE_CLASS: voltage_class}
    return cfg


def make_number(coordinator, entry, desc):
    entity = ModbusBridgeNumber(coordinator, entry, dict(desc), "lxp", None)
    entity.async_write_ha_state = MagicMock()
    return entity


class TestVoltageScaling:
    def test_48v_is_unchanged(self, coordinator):
        entity = make_number(coordinator, make_entry(48), AC_CHARGE_START)

        assert entity.native_min_value == 38.5
        assert entity.native_max_value == 52.0

    def test_default_is_48v(self, coordinator):
        """An existing install with no option set must behave exactly as before."""
        entity = make_number(coordinator, make_entry(None), AC_CHARGE_START)

        assert entity.native_min_value == 38.5
        assert entity.native_max_value == 52.0
        assert DEFAULT_BATTERY_VOLTAGE_CLASS == REFERENCE_BATTERY_VOLTAGE_CLASS

    def test_24v_halves_the_range(self, coordinator):
        entity = make_number(coordinator, make_entry(24), AC_CHARGE_START)

        assert entity.native_min_value == 19.2
        assert entity.native_max_value == 26.0

    def test_24v_accepts_the_value_from_the_issue(self, coordinator):
        """25.6 V was refused on a 24 V system; it must now be in range."""
        entity = make_number(coordinator, make_entry(24), AC_CHARGE_START)

        assert entity.native_min_value <= 25.6 <= entity.native_max_value

    def test_12v_quarters_the_range(self, coordinator):
        entity = make_number(coordinator, make_entry(12), AC_CHARGE_START)

        assert entity.native_min_value == 9.6
        assert entity.native_max_value == 13.0

    def test_non_battery_voltages_are_never_scaled(self, coordinator):
        """Grid, PV, bus and per-cell limits are not battery pack voltages."""
        entity = make_number(coordinator, make_entry(12), GRID_VOLTAGE)

        assert entity.native_min_value == 0.0
        assert entity.native_max_value == 6553.5

    def test_unknown_class_falls_back_to_default(self, coordinator):
        entity = make_number(coordinator, make_entry(36), AC_CHARGE_START)

        assert entity.native_min_value == 38.5
        assert entity.native_max_value == 52.0

    def test_register_scaling_is_unaffected(self, coordinator):
        """The register is still 0.1 V regardless of the battery class."""
        coordinator.data["hold"][158] = 256      # 25.6 V
        entity = make_number(coordinator, make_entry(24), AC_CHARGE_START)

        assert entity.native_value == 25.6

    @pytest.mark.parametrize("voltage_class", BATTERY_VOLTAGE_CLASSES)
    def test_every_class_produces_a_sane_range(self, coordinator, voltage_class):
        entity = make_number(coordinator, make_entry(voltage_class), AC_CHARGE_START)

        assert 0 < entity.native_min_value < entity.native_max_value


class TestTagging:
    """Which descriptions are tagged decides what gets rescaled."""

    def _tagged(self):
        return [d for d in NUMBER_TYPES if d.get("battery_voltage")]

    def test_tagged_entities_are_all_volts(self):
        for desc in self._tagged():
            assert desc.get("unit") == "V", f"{desc['name']} is tagged but not in volts"

    def test_tagged_ranges_are_plausible_for_48v(self):
        """A tagged range outside roughly 20-70 V is probably not a pack voltage."""
        for desc in self._tagged():
            assert 9 <= desc["min"] <= 70, f"{desc['name']} min {desc['min']} looks wrong"
            assert desc["max"] <= 85, f"{desc['name']} max {desc['max']} looks wrong"

    def test_known_non_pack_voltages_are_not_tagged(self):
        """These must never scale: grid rails, the DC bus, PV, and per-cell limits."""
        must_not_scale = {
            "Grid Voltage Low Limit", "Grid Voltage High Limit",
            "Grid Voltage L1 Low", "Grid Voltage L1 High",
            "BUS Overvoltage Alarm Point", "Start PV Voltage",
            "Battery Cell Voltage Low Limit", "Battery Cell Voltage High Limit",
            "PF Curve Lock-In Voltage", "PF Curve Lock-Out Voltage",
            "Vref for QV", "VoltWatt V1", "VoltWatt V2",
        }
        tagged = {d["name"] for d in self._tagged()}
        assert not (tagged & must_not_scale)

    def test_core_battery_voltages_are_tagged(self):
        """If these are missed, 12 V and 24 V users still cannot set them."""
        expected = {
            "AC Charge Start Voltage", "AC Charge End Voltage",
            "Battery Stop Charging Voltage", "Float Charge Voltage",
            "Battery Low Voltage Alarm", "Battery Low Voltage Recovery",
            "Charge First End Voltage", "Forced Discharge End Voltage",
            "On-Grid Cut-Off Voltage",
        }
        tagged = {d["name"] for d in self._tagged()}
        missing = expected - tagged
        assert not missing, f"untagged battery voltages: {sorted(missing)}"

    def test_expected_number_of_tagged_entities(self):
        """A guard against a bulk edit silently adding or dropping tags."""
        assert len(self._tagged()) == 81


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
