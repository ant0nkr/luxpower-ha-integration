"""Net energy counters built from several registers.

The calculated home consumption sensors subtract one counter from another, so a
poll that returned some register blocks and not others must not be turned into a
number: zeros in the gaps produce a plausible but wrong value, and can produce a
negative one, which Home Assistant cannot record against total_increasing.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.constants.input_registers import (
    I_EEPS_DAY,
    I_EINV_DAY,
    I_EREC_DAY,
    I_ETOGRID_DAY,
    I_ETOUSER_DAY,
)
from custom_components.lxp_modbus.entity_descriptions.sensor_types import SENSOR_TYPES
from custom_components.lxp_modbus.utils import energy_balance

DAY_REGISTERS = {
    I_ETOUSER_DAY: 120,   # 12.0 kWh imported
    I_EINV_DAY: 300,      # 30.0 kWh inverter output
    I_EEPS_DAY: 10,       # 1.0 kWh off-grid output
    I_EREC_DAY: 50,       # 5.0 kWh charged from the grid
    I_ETOGRID_DAY: 80,    # 8.0 kWh exported
}


def description_for(name):
    """Return the single sensor description with this name."""
    matches = [desc for desc in SENSOR_TYPES if desc["name"] == name]
    assert len(matches) == 1, f"expected exactly one '{name}', found {len(matches)}"
    return matches[0]


class TestEnergyBalance:
    """The helper itself."""

    def test_adds_and_subtracts(self):
        assert energy_balance({1: 10, 2: 4}, add=(1,), subtract=(2,)) == 6

    def test_combines_a_split_counter(self):
        """A 32-bit counter arrives as a low and a high register."""
        assert energy_balance({1: 0x0005, 2: 0x0001}, add=((1, 2),)) == 0x10005

    def test_missing_register_is_not_zero(self):
        assert energy_balance({1: 10}, add=(1,), subtract=(2,)) is None

    def test_missing_half_of_a_split_counter_is_not_zero(self):
        assert energy_balance({1: 5}, add=((1, 2),)) is None

    def test_zero_is_a_real_value(self):
        """0 is what the counters read at midnight, not a missing register."""
        assert energy_balance({1: 0, 2: 0}, add=(1,), subtract=(2,)) == 0


class TestHomeConsumptionSensors:
    """The descriptions that use it."""

    def test_today_matches_the_documented_formula(self):
        extract = description_for("Home Consumption Today Calculated")["extract"]

        # 12.0 + 30.0 + 1.0 - 5.0 - 8.0 = 30.0 kWh, in units of 0.1 kWh
        assert extract(DAY_REGISTERS, None) == 300

    def test_today_is_unknown_on_a_partial_poll(self):
        extract = description_for("Home Consumption Today Calculated")["extract"]
        partial = dict(DAY_REGISTERS)
        del partial[I_ETOUSER_DAY]

        assert extract(partial, None) is None

    def test_total_is_unknown_on_a_partial_poll(self):
        extract = description_for("Home Consumption Total Calculated")["extract"]

        assert extract({}, None) is None

    @pytest.mark.parametrize(
        "name", ["Home Consumption Today Calculated", "Home Consumption Total Calculated"]
    )
    def test_every_source_register_is_declared_as_a_dependency(self, name):
        """depends_on drives the update filter; a missing entry means a stale sensor."""
        desc = description_for(name)
        registers = dict.fromkeys(desc["depends_on"], 0)

        # All declared dependencies present -> a value, not None.
        assert desc["extract"](registers, None) is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
