"""Behavioral coverage for the AFCI diagnostic sensor block."""

import os
import sys
from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.lxp_modbus.entity_descriptions.sensor_types import SENSOR_TYPES
from custom_components.lxp_modbus.sensor import ModbusBridgeSensor


AFCI_READINGS = [
    ("AFCI Current CH1", 140, 1244, "mA"),
    ("AFCI Current CH2", 141, 1242, "mA"),
    ("AFCI Current CH3", 142, 74, "mA"),
    ("AFCI Current CH4", 143, 45, "mA"),
    ("AFCI Flag", 144, 120, None),
    ("AFCI Arc CH1", 145, 18956, None),
    ("AFCI Arc CH2", 146, 7, None),
    ("AFCI Arc CH3", 147, 0, None),
    ("AFCI Arc CH4", 148, 2305, None),
    ("AFCI Max Arc CH1", 149, 0, None),
    ("AFCI Max Arc CH2", 150, 0, None),
    ("AFCI Max Arc CH3", 151, 4, None),
    ("AFCI Max Arc CH4", 152, 26624, None),
]


@pytest.mark.parametrize("name,register,raw_value,unit", AFCI_READINGS)
def test_afci_sensor_maps_reported_register_and_is_opt_in(
    name, register, raw_value, unit
):
    """Each cloud-export reading maps unchanged to an opt-in diagnostic entity."""
    matches = [desc for desc in SENSOR_TYPES if desc.get("name") == name]
    assert len(matches) == 1

    coordinator = MagicMock()
    coordinator.data = {"input": {register: raw_value}, "hold": {}}
    coordinator.hass = MagicMock()
    entry = MagicMock(entry_id="entry", title="Inverter", data={})
    sensor = ModbusBridgeSensor(
        coordinator, entry, dict(matches[0]), "lxp", api_client=None
    )

    assert sensor.native_value == raw_value
    assert sensor._register == register
    assert sensor._attr_native_unit_of_measurement == unit
    assert sensor._attr_entity_category is EntityCategory.DIAGNOSTIC
    assert sensor._attr_entity_registry_enabled_default is False
