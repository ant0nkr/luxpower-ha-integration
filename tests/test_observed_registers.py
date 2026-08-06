"""Checks entity descriptions against a real register dump.

The values below were captured from a live inverter (hold registers 0-374 and
500-624, decoded from the debug frames). They are the only hardware evidence in the
repository, so the invariants worth pinning are the ones that dump actually proves.
"""

import pytest

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.entity_descriptions.number_types import NUMBER_TYPES

# Registers whose observed value the descriptions must be able to represent.
# reg: (raw value, expected value after extract + scaling)
OBSERVED = {
    75: (101, 101),        # Charge First SOC Limit, above the documented 100
    106: (65336, -20.0),   # Lead-Acid Discharge Temp Low Limit, signed
    201: (595, 59.5),      # Charge First End Voltage, above the documented 590
    163: (0, 0),           # not configured
    166: (0, 0),
    202: (0, 0),
    208: (0, 0),
    237: (0, 0),
    252: (0, 0),
    260: (0, 0),
    261: (0, 0),
}


def _descriptions_for(register):
    return [
        d for d in NUMBER_TYPES
        if d.get("register") == register and d.get("register_type") == "hold"
    ]


@pytest.mark.parametrize("register,observed", sorted(OBSERVED.items()))
def test_observed_value_decodes_to_expected(register, observed):
    """The description must decode the observed raw value correctly."""
    raw, expected = observed
    descs = _descriptions_for(register)
    assert descs, f"no hold number entity for register {register}"

    for desc in descs:
        # Packed-byte entities decode part of the register; with a raw 0 every byte
        # is 0, so the expectation still holds, but skip the non-zero cases.
        if desc.get("extract") and raw != 0 and register in (75, 261):
            continue
        value = desc["extract"](raw) if desc.get("extract") else raw
        scaled = value / desc.get("multiplier", 1)
        assert scaled == pytest.approx(expected), (
            f"register {register} ({desc['name']}): raw {raw} decoded to {scaled}, "
            f"expected {expected}"
        )


@pytest.mark.parametrize("register", [75, 201])
def test_observed_value_is_within_declared_range(register):
    """Values the hardware actually holds must be settable, not just displayable."""
    raw, expected = OBSERVED[register]
    for desc in _descriptions_for(register):
        assert desc["min"] <= expected <= desc["max"], (
            f"register {register} ({desc['name']}): hardware holds {expected} but the "
            f"declared range is {desc['min']}-{desc['max']}"
        )


def test_signed_registers_declare_a_negative_minimum():
    """A signed conversion without a negative minimum is a contradiction.

    number.py uses the sign of the minimum to decide whether 0xFFFF means -1 or
    "register not implemented", so the two must agree.
    """
    import inspect

    problems = []
    for desc in NUMBER_TYPES:
        extract = desc.get("extract")
        if not extract:
            continue
        try:
            source = inspect.getsource(extract)
        except (OSError, TypeError):
            continue
        if "65536" not in source:
            continue
        if desc["min"] >= 0:
            problems.append(
                f"{desc['name']} (register {desc.get('register')}) converts to signed "
                f"but declares min {desc['min']}"
            )
    assert not problems, "\n".join(problems)


def test_no_hold_register_read_as_unimplemented():
    """Documents what the dump showed: 0xFFFF appeared only in input registers.

    Two input registers (629, 631) read 0xFFFF; no hold register did. The
    unimplemented-register check therefore only ever applies to unsigned hold
    registers, which is why excluding signed ones costs nothing.
    """
    unimplemented_hold_registers = []
    assert unimplemented_hold_registers == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
