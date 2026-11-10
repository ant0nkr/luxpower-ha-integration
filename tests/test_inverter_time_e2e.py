"""The Inverter Time sensor through the whole integration.

The sensor tests in test_inverter_clock.py build coordinator.data by hand. These run the
real chain instead: the integration's own setup, the real client talking frames to a fake
dongle, the real coordinator and the real sensor platform, with the clock registers
packed from a clock the test controls. They show that the read times the client records
actually arrive at the sensor, and what the sensor does when the source is read, cached,
silent, or recovering.

Only time is faked. time.time() in the client and the sensor's own clock are replaced by
a hand-wound clock, which is not Home Assistant's freezer: that freezes the monotonic
clock too, which stops the client's asyncio timeouts and hangs the test.
"""

import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from fake_dongle import FakeDongle
from custom_components.lxp_modbus.const import (
    CONF_BATTERY_ENTITIES,
    CONF_CONNECTION_RETRIES,
    CONF_DONGLE_SERIAL,
    CONF_ENTITY_PREFIX,
    CONF_HOST,
    CONF_INVERTER_SERIAL,
    CONF_POLL_INTERVAL,
    CONF_PORT,
    CONF_RATED_POWER,
    DOMAIN,
)

LONDON = ZoneInfo("Europe/London")
UNIQUE_ID = "lxp_12_13_14_inverter_time"           # entity prefix "lxp", registers 12-14
START = datetime(2026, 10, 27, 9, 45, 59, tzinfo=timezone.utc).timestamp()   # GMT, so London time too
POLL = 60                                          # the default poll interval, in seconds


class Clock:
    def __init__(self):
        self.now = START

    def tick(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    clock = Clock()
    with patch("custom_components.lxp_modbus.classes.modbus_client.time_lib",
               SimpleNamespace(time=lambda: clock.now)), \
            patch("custom_components.lxp_modbus.sensor.dt_util",
                  SimpleNamespace(utcnow=lambda: datetime.fromtimestamp(clock.now, timezone.utc))), \
            patch("custom_components.lxp_modbus.classes.connection_manager.INITIAL_DATA_TIMEOUT", 0.01), \
            patch("custom_components.lxp_modbus.classes.modbus_client.READ_TIMEOUT", 0.05):
        yield clock


def make_dongle(clock):
    """A dongle whose clock registers (12-14) show the test clock in London time."""
    def value_of(function, register):
        if function == 3 and register in (12, 13, 14):
            moment = datetime.fromtimestamp(clock.now, LONDON).replace(tzinfo=None)
            return {12: (moment.year - 2000) | (moment.month << 8),
                    13: moment.day | (moment.hour << 8),
                    14: moment.minute | (moment.second << 8)}[register]
        return 0
    return FakeDongle(dongle=b"BA0000000A", serial=b"0000000001", value_of=value_of)


async def set_up(hass, dongle, enabled=True):
    """Set the integration up as Home Assistant would, and return its coordinator."""
    await hass.config.async_set_time_zone("Europe/London")
    entry = MockConfigEntry(domain=DOMAIN, title="Inverter", data={
        CONF_HOST: "192.0.2.1", CONF_PORT: 8000, CONF_DONGLE_SERIAL: "BA0000000A",
        CONF_INVERTER_SERIAL: "0000000001", CONF_POLL_INTERVAL: POLL,
        CONF_ENTITY_PREFIX: "lxp", CONF_RATED_POWER: 5000, CONF_CONNECTION_RETRIES: 1,
        CONF_BATTERY_ENTITIES: "none", "read_only": True,
    })
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    if enabled:
        # A user who turned the entity on: the description itself is disabled by default.
        registry.async_get_or_create("sensor", DOMAIN, UNIQUE_ID, config_entry=entry,
                                     suggested_object_id="lxp_inverter_time")
    with patch("asyncio.open_connection", return_value=(dongle, dongle)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id]["coordinator"]


def state(hass):
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, UNIQUE_ID)
    return hass.states.get(entity_id)


async def poll(hass, coordinator, dongle=None, refuse=False):
    """Run one coordinator refresh against the dongle, or with the connection refused."""
    if refuse:
        with patch("asyncio.open_connection", side_effect=ConnectionRefusedError("refused")):
            await coordinator.async_refresh()
    else:
        with patch("asyncio.open_connection", return_value=(dongle, dongle)):
            await coordinator.async_refresh()
    await hass.async_block_till_done()


def clock_now(clock):
    """What the sensor should say: the test clock to the nearest minute, as Home Assistant publishes it."""
    moment = datetime.fromtimestamp(clock.now + 30, timezone.utc).replace(second=0, microsecond=0)
    return moment.isoformat()


async def test_the_clock_through_a_settings_pass_cached_polls_and_a_silent_inverter(
        hass, enable_custom_integrations, clock):
    dongle = make_dongle(clock)
    coordinator = await set_up(hass, dongle)

    # The settings pass at setup reads the clock, and the client says when.
    assert {12, 13, 14} <= set(coordinator.data["hold_read_at"])
    assert state(hass).state == clock_now(clock)

    # Four minutes on, a poll that does not read settings: the clock has kept running.
    clock.tick(240)
    await poll(hass, coordinator, dongle)
    assert coordinator.api_client._polls_since_hold == 1
    assert state(hass).state == clock_now(clock)

    # The connection is refused and the client serves its cache: the reading is old,
    # not fresh, and is advanced from the time it was really read.
    clock.tick(60)
    await poll(hass, coordinator, refuse=True)
    assert coordinator.last_update_success
    assert state(hass).state == clock_now(clock)

    # The inverter stops answering for settings while input registers still read. Polls
    # keep succeeding, so the coordinator never marks anything unavailable; only the age
    # of the clock registers shows that the clock is no longer being read.
    dongle.silent_functions = {3}
    for _ in range(20):
        clock.tick(70)
        await poll(hass, coordinator, dongle)
        assert coordinator.last_update_success
        if state(hass).state == "unavailable":
            break
    assert state(hass).state == "unavailable"

    # And it comes back as soon as the registers are read again.
    dongle.silent_functions = set()
    clock.tick(70)
    await poll(hass, coordinator, dongle)
    assert state(hass).state == clock_now(clock)


async def test_an_inverter_that_answers_nothing_is_caught_though_polls_succeed(
        hass, enable_custom_integrations, clock):
    """The dongle accepts the connection but the inverter does not reply to anything.

    The client swallows the timeouts and reports a successful poll with its cache, so the
    coordinator never raises. Only the age of the registers can say the data is dead.
    """
    dongle = make_dongle(clock)
    coordinator = await set_up(hass, dongle)

    dongle.silent_functions = {3, 4}
    for _ in range(20):
        clock.tick(70)
        await poll(hass, coordinator, dongle)
        if state(hass).state == "unavailable":
            break

    assert coordinator.last_update_success
    assert state(hass).state == "unavailable"


async def test_a_confirmed_write_keeps_the_read_times_flowing(hass, enable_custom_integrations, clock):
    """After a write the entity publishes the client's cache, which must still carry the stamps.

    The write is confirmed and the block holding the register is re-read, so that block is
    stamped afresh, and nothing else is."""
    dongle = make_dongle(clock)
    coordinator = await set_up(hass, dongle)
    clock.tick(300)

    with patch("asyncio.open_connection", return_value=(dongle, dongle)):
        assert await coordinator.api_client.async_write_register(21, 0)
    data = coordinator.api_client.get_cached_data()

    stamps = data["hold_read_at"]
    assert stamps[21] == clock.now             # the confirmed register is fresh
    assert stamps[12] == clock.now             # and so is the clock: the re-read is of the whole block
    assert stamps[300] < clock.now             # while a register in another block was not re-read
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert state(hass).state == clock_now(clock)


async def test_disabled_by_default_through_the_integration(hass, enable_custom_integrations, clock):
    """Set up by the integration itself, the entity is registered but disabled, with no state."""
    dongle = make_dongle(clock)
    await set_up(hass, dongle, enabled=False)

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, UNIQUE_ID)

    assert entity_id is not None
    assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(entity_id) is None
