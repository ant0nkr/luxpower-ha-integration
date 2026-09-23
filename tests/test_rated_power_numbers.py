"""Settings the inverter stores as a percentage of rated power.

Registers 66 (AC charge) and 82 (forced discharge) hold 0-100 %, but the LuxPower
app and web portal show the same settings in kW, which is what users compare
against — the cause of #94, #104 and #128. The percentage entity stays, and a
second entity converts, so the conversion depends on the configured rated power
instead of assuming a 10 kW inverter (where % and 0.1 kW happen to coincide).
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.const import CONF_RATED_POWER, DOMAIN
from custom_components.lxp_modbus.entity_descriptions.number_types import NUMBER_TYPES
from custom_components.lxp_modbus.number import ModbusBridgeNumber, rated_power

ENTRY_ID = "test_entry_id"


@pytest.fixture
def api_client():
    client = AsyncMock()
    client.async_write_register = AsyncMock(return_value=True)
    client.get_cached_data = MagicMock(return_value={"hold": {}, "input": {}, "battery": {}})
    return client


@pytest.fixture
def coordinator():
    coord = MagicMock()
    coord.data = {"hold": {}, "input": {}}
    coord.async_set_updated_data = MagicMock()
    coord.hass = MagicMock()
    coord.hass.data = {DOMAIN: {ENTRY_ID: {"write_lock": asyncio.Lock()}}}
    return coord


def make_entry(rated_watts):
    entry = MagicMock()
    entry.entry_id = ENTRY_ID
    entry.title = "Test Inverter"
    entry.data = {CONF_RATED_POWER: rated_watts} if rated_watts is not None else {}
    return entry


def description_for(name):
    matches = [desc for desc in NUMBER_TYPES if desc["name"] == name]
    assert len(matches) == 1, f"expected exactly one '{name}', found {len(matches)}"
    return matches[0]


def make_number(coordinator, entry, api_client, name):
    entity = ModbusBridgeNumber(
        coordinator, entry, dict(description_for(name)), "lxp", api_client
    )
    entity.async_write_ha_state = MagicMock()
    return entity


KW_ENTITIES = ["AC Charge Power (kW)", "Forced Discharge Power (kW)"]


class TestRatedPowerHelper:
    def test_missing_rated_power(self):
        assert rated_power(make_entry(None)) is None

    def test_zero_rated_power_is_unusable(self):
        assert rated_power(make_entry(0)) is None

    def test_configured_rated_power(self):
        assert rated_power(make_entry(5000)) == 5000


class TestKilowattConversion:
    @pytest.mark.parametrize("name", KW_ENTITIES)
    def test_percentage_entity_still_exists_for_the_same_register(self, name):
        """Existing automations and history use the percentage entity."""
        kw_desc = description_for(name)
        percentage = [
            desc for desc in NUMBER_TYPES
            if desc.get("register") == kw_desc["register"]
            and not desc.get("percent_of_rated_power")
        ]

        assert len(percentage) == 1
        assert percentage[0]["unit"] == "%"

    @pytest.mark.parametrize("name", KW_ENTITIES)
    def test_range_follows_rated_power(self, coordinator, api_client, name):
        entity = make_number(coordinator, make_entry(5000), api_client, name)

        assert entity.native_unit_of_measurement == "kW"
        assert entity.native_min_value == 0
        assert entity.native_max_value == 5.0

    @pytest.mark.parametrize("name", KW_ENTITIES)
    def test_reading_scales_by_rated_power(self, coordinator, api_client, name):
        """51 % is 5.1 kW on a 10 kW inverter but 2.55 kW on a 5 kW one.

        Treating the register as 0.1 kW — as PR #104 proposed — is right only for
        the 10 kW case, which is why it looked verified.
        """
        register = description_for(name)["register"]
        coordinator.data["hold"][register] = 51

        assert make_number(coordinator, make_entry(10000), api_client, name).native_value == 5.1
        assert make_number(coordinator, make_entry(5000), api_client, name).native_value == 2.55

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", KW_ENTITIES)
    async def test_writing_converts_back_to_a_percentage(
        self, coordinator, api_client, name
    ):
        register = description_for(name)["register"]
        coordinator.data["hold"][register] = 0
        entity = make_number(coordinator, make_entry(10000), api_client, name)

        await entity.async_set_native_value(2.0)

        api_client.async_write_register.assert_awaited_once_with(register, 20)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", KW_ENTITIES)
    async def test_write_never_exceeds_the_register_range(
        self, coordinator, api_client, name
    ):
        """The register is 0-100; a larger value is rejected by the inverter."""
        register = description_for(name)["register"]
        coordinator.data["hold"][register] = 0
        entity = make_number(coordinator, make_entry(5000), api_client, name)

        await entity.async_set_native_value(25.0)  # far above the 5 kW maximum

        api_client.async_write_register.assert_awaited_once_with(register, 100)

    @pytest.mark.parametrize("name", KW_ENTITIES)
    @pytest.mark.parametrize("rated_watts", [3600, 5000, 8000, 10000, 12000])
    def test_what_is_set_is_what_is_shown(
        self, coordinator, api_client, name, rated_watts
    ):
        """A value the user sets must read back as the same value.

        That holds only because the step is one percent of rated power. With a
        fixed 0.1 kW step, a 12 kW inverter would accept 0.3 kW and show 0.24.
        """
        entity = make_number(coordinator, make_entry(rated_watts), api_client, name)

        for step_count in range(0, 101):
            kilowatts = round(entity.native_step * step_count, 3)
            percent = entity._kw_to_percent(kilowatts)
            assert entity._percent_to_kw(percent) == pytest.approx(kilowatts)

    @pytest.mark.parametrize("name", KW_ENTITIES)
    def test_step_is_one_percent_of_rated_power(self, coordinator, api_client, name):
        """Every position on the slider is a value the register can hold."""
        entity = make_number(coordinator, make_entry(12000), api_client, name)

        assert entity.native_step == 0.12
        assert entity.native_max_value == 12.0
