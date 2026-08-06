"""Pins number entity ranges against the published LuxPower/EG4 Modbus protocol.

Ranges in the entity descriptions are easy to get wrong and hard to notice: a
wrong min/max only shows up when a user cannot set a value the inverter accepts,
or sets one it does not. The rows below were read directly out of the protocol
document (see docs/protocol-registers.md), so a future edit that drifts away from
the documented range fails here instead of shipping.

Only registers the document actually covers are pinned. Registers above 198 are
not in it and are deliberately absent — do not add guesses to this table.
"""

import re
import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.entity_descriptions.number_types import NUMBER_TYPES
import custom_components.lxp_modbus.constants.hold_registers as hold_registers

# register -> (unit as printed in the document, raw min, raw max)
DOCUMENTED_RANGES = {
    160: ("%", 0, 90),       # ACChgStartSOC
    161: ("%", 20, 100),     # ACChgEndSOC
    162: ("0.1V", 400, 500),  # BatLowVoltage
    163: ("0.1V", 420, 520),  # BatLowBackVoltage
    164: ("%", 0, 90),       # BatLowSOC
    165: ("%", 20, 100),     # BatLowBackSOC
    166: ("0.1V", 444, 514),  # BatLowtoUtilityVoltage
    167: ("%", 0, 100),      # BatLowtoUtilitySOC
    168: ("A", 0, 140),      # ACChargeBatCurrent
    169: ("0.1V", 400, 560),  # OngridEOD_Voltage
    171: ("0.1V", 400, 600),  # SOCCurve_BatVolt1
    172: ("0.1V", 400, 600),  # SOCCurve_BatVolt2
}

# Ranges we knowingly keep wider than the document, with the reason. Anything not
# listed here must match the document exactly.
KNOWN_DIVERGENCES = {
    161: (
        (0, 100),
        "Pre-existing: description allows 0 where the document says 20. Not yet "
        "confirmed against hardware.",
    ),
    165: (
        (0, 100),
        "Hardware reports 0 in this register when the feature is not configured, "
        "and the floor was lowered so the value can be written back. The document "
        "says 20-100.",
    ),
}


def _register_numbers():
    """Map hold register constant names to their numbers."""
    return {
        name: value
        for name, value in vars(hold_registers).items()
        if name.startswith("H_") and isinstance(value, int)
    }


def _documented_descriptions():
    """Yield (register, description) for whole-register numbers we have docs for."""
    numbers = _register_numbers()
    for desc in NUMBER_TYPES:
        if desc.get("register_type") != "hold":
            continue
        register = desc.get("register")
        if register not in DOCUMENTED_RANGES:
            continue
        # Entities that extract a packed byte cover part of a register, so the
        # whole-register range in the document does not apply to them.
        if desc.get("extract"):
            continue
        yield register, desc


@pytest.mark.parametrize("register,expected", sorted(DOCUMENTED_RANGES.items()))
def test_documented_register_has_an_entity(register, expected):
    """Each documented register still has a number entity."""
    registers = [reg for reg, _ in _documented_descriptions()]
    assert register in registers


def test_ranges_match_the_protocol_document():
    """Declared ranges must match the document, or be a listed divergence."""
    problems = []

    for register, desc in _documented_descriptions():
        _unit, doc_min, doc_max = DOCUMENTED_RANGES[register]
        multiplier = desc.get("multiplier", 1)
        raw_min = desc["min"] * multiplier
        raw_max = desc["max"] * multiplier

        if register in KNOWN_DIVERGENCES:
            allowed, _reason = KNOWN_DIVERGENCES[register]
            expected_min, expected_max = allowed
            if (desc["min"], desc["max"]) != (expected_min, expected_max):
                problems.append(
                    f"register {register} ({desc['name']}): listed as a known "
                    f"divergence at {expected_min}-{expected_max} but is now "
                    f"{desc['min']}-{desc['max']}; update KNOWN_DIVERGENCES or "
                    f"restore the documented range {doc_min}-{doc_max} raw"
                )
            continue

        if (raw_min, raw_max) != (doc_min, doc_max):
            problems.append(
                f"register {register} ({desc['name']}): declared "
                f"{raw_min:g}-{raw_max:g} raw (min {desc['min']}, max {desc['max']}, "
                f"multiplier {multiplier}) but the document says {doc_min}-{doc_max}"
            )

    assert not problems, "\n".join(problems)


def test_divergences_are_still_divergences():
    """A divergence that has been brought back in line should be removed here."""
    stale = []
    for register, (allowed, _reason) in KNOWN_DIVERGENCES.items():
        _unit, doc_min, doc_max = DOCUMENTED_RANGES[register]
        if allowed == (doc_min, doc_max):
            stale.append(register)
    assert not stale, (
        f"registers {stale} now match the document; drop them from KNOWN_DIVERGENCES"
    )


def test_every_divergence_has_a_reason():
    """A divergence without a stated reason is indistinguishable from a mistake."""
    for register, (_allowed, reason) in KNOWN_DIVERGENCES.items():
        assert reason and len(reason) > 20, f"register {register} needs a real reason"


def test_undocumented_registers_are_not_pinned():
    """Registers above the document's coverage must not be added to the table.

    Guessing a range for them is what produced the ranges this file exists to
    catch.
    """
    assert not [reg for reg in DOCUMENTED_RANGES if reg > 198]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
