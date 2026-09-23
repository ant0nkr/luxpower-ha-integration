"""Byte layout of the registers that pack an SOC limit beside a start hour.

Registers 75 and 83 are the same shape: SOC limit in the low byte, start hour in
the high byte. Getting this backwards makes the entity read 0 and makes a write
corrupt the schedule instead of the limit, which is what #123 and #140 reported.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.constants.hold_registers import (
    H_CHARGE_FIRST_SOC_LIMIT,
    H_FORCED_DISCHARGE_SOC_LIMIT_AND_START_TIME,
)
from custom_components.lxp_modbus.entity_descriptions.number_types import NUMBER_TYPES

PACKED_SOC_LIMITS = {
    "Charge First SOC Limit": H_CHARGE_FIRST_SOC_LIMIT,
    "Forced Discharge SOC Limit": H_FORCED_DISCHARGE_SOC_LIMIT_AND_START_TIME,
}


def description_for(name):
    """Return the single entity description with this name."""
    matches = [desc for desc in NUMBER_TYPES if desc["name"] == name]
    assert len(matches) == 1, f"expected exactly one '{name}', found {len(matches)}"
    return matches[0]


@pytest.mark.parametrize("name,register", PACKED_SOC_LIMITS.items())
def test_soc_limit_is_on_the_expected_register(name, register):
    """Guard against the description drifting onto another register."""
    assert description_for(name)["register"] == register


@pytest.mark.parametrize("name", PACKED_SOC_LIMITS)
def test_soc_limit_reads_the_low_byte(name):
    """Start hour 14 (0x0E) with an 80% limit reads back as 80, not 14."""
    extract = description_for(name)["extract"]

    assert extract((14 << 8) | 80) == 80


@pytest.mark.parametrize("name", PACKED_SOC_LIMITS)
def test_soc_limit_write_preserves_the_start_hour(name):
    """Writing the limit must leave the scheduled start hour alone."""
    compose = description_for(name)["compose"]
    original = (14 << 8) | 80

    updated = compose(original, 55)

    assert updated & 0xFF == 55
    assert (updated >> 8) & 0xFF == 14


@pytest.mark.parametrize("name", PACKED_SOC_LIMITS)
def test_soc_limit_round_trips(name):
    """Every documented limit survives a write followed by a read."""
    desc = description_for(name)
    original = (9 << 8) | 0

    for value in range(0, 101):
        assert desc["extract"](desc["compose"](original, value)) == value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
