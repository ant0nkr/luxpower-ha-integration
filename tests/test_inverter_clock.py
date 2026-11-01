"""The Inverter Time sensor, and the held-sensor path it is built on.

An inverter's clock is plain wall-clock time with no timezone, and its charge and
discharge windows follow it. After the UK clocks went back an inverter that had been
left on BST ran an hour fast, and Predbat started charging 30 minutes before the cheap
window without anyone being told. Predbat's inverter_time setting needs a sensor to
read, and this is it.

The clock lives in settings (hold) registers, which are only re-read every few polls.
A sensor derived from them is *held*: the value is carried between reads, optionally
advanced by the time since the read, and goes unavailable if the registers stop being
read, so that a dead connection does not look healthy.
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lxp_modbus.const import (
    CONF_POLL_INTERVAL,
    DOMAIN,
    HELD_POLL_ALLOWANCE_SECONDS,
    HELD_SOURCE_STALE_CYCLES,
    HOLD_REGISTER_POLL_EVERY,
)
from custom_components.lxp_modbus.constants.hold_registers import (
    H_TIME_YEAR_MONTH, H_TIME_DATE_HOUR, H_TIME_MINUTE_SECOND,
)
from custom_components.lxp_modbus.entity_descriptions.sensor_types import SENSOR_TYPES
from custom_components.lxp_modbus.sensor import ModbusBridgeSensor
from custom_components.lxp_modbus.utils import advance_inverter_clock, decode_inverter_clock

ENTRY_ID = "test_entry_id"
LONDON = ZoneInfo("Europe/London")
NOW = "2026-10-27T09:45:59+00:00"                 # when the clock below was read: GMT, so also 09:45:59 in London
CLOCK = datetime(2026, 10, 27, 9, 45, 59)
CLOCK_REGISTERS = (H_TIME_YEAR_MONTH, H_TIME_DATE_HOUR, H_TIME_MINUTE_SECOND)

# A real reading from a LuxPower inverter: 2026-10-27 09:45:59
REAL_READING = {H_TIME_YEAR_MONTH: 2586, H_TIME_DATE_HOUR: 2331, H_TIME_MINUTE_SECOND: 15149}


def pack(moment: datetime) -> dict:
    """Pack a datetime into the three clock registers (two fields each, low byte first)."""
    return {
        H_TIME_YEAR_MONTH: (moment.year - 2000) | (moment.month << 8),
        H_TIME_DATE_HOUR: moment.day | (moment.hour << 8),
        H_TIME_MINUTE_SECOND: moment.minute | (moment.second << 8),
    }


def stale_limit(poll_interval=60) -> int:
    """Seconds after which a source that has not been read is stale."""
    return HELD_SOURCE_STALE_CYCLES * HOLD_REGISTER_POLL_EVERY * (poll_interval + HELD_POLL_ALLOWANCE_SECONDS)


def fresh_read(moment: datetime, read_ago: float = 0) -> dict:
    """The hold part of coordinator.data for a clock read ``read_ago`` seconds ago."""
    stamp = dt_util.utcnow().timestamp() - read_ago
    registers = pack(moment)
    return {"hold": registers, "hold_read_at": {register: stamp for register in registers}}


def clock_description(**overrides) -> dict:
    description = next(d for d in SENSOR_TYPES if d["name"] == "Inverter Time")
    return {**description, **overrides}


class TestDecodeInverterClock:
    def test_decodes_a_real_reading(self):
        assert decode_inverter_clock(REAL_READING) == CLOCK

    def test_round_trips_every_field(self):
        moment = datetime(2031, 12, 31, 23, 59, 58)

        assert decode_inverter_clock(pack(moment)) == moment

    def test_result_is_naive(self):
        """The inverter reports wall-clock time with no zone of its own."""
        assert decode_inverter_clock(REAL_READING).tzinfo is None

    @pytest.mark.parametrize("missing", CLOCK_REGISTERS)
    def test_a_missing_register_gives_none(self, missing):
        """A poll that returned some register blocks and not others must not make a time."""
        registers = {k: v for k, v in REAL_READING.items() if k != missing}

        assert decode_inverter_clock(registers) is None

    def test_no_hold_data_gives_none(self):
        assert decode_inverter_clock({}) is None

    def test_all_zero_registers_give_none(self):
        """Month 0 and day 0 are not a date, which is what an unset inverter reports."""
        assert decode_inverter_clock(
            {H_TIME_YEAR_MONTH: 0, H_TIME_DATE_HOUR: 0, H_TIME_MINUTE_SECOND: 0}
        ) is None

    @pytest.mark.parametrize("year_month,date_hour,minute_second", [
        (26 | (13 << 8), 1 | (0 << 8), 0),        # month 13
        (26 | (2 << 8), 30 | (0 << 8), 0),         # 30 February
        (26 | (10 << 8), 27 | (24 << 8), 0),       # hour 24
        (26 | (10 << 8), 27 | (9 << 8), 60),       # minute 60
        (26 | (10 << 8), 27 | (9 << 8), 60 << 8),  # second 60
    ])
    def test_impossible_dates_give_none(self, year_month, date_hour, minute_second):
        registers = {
            H_TIME_YEAR_MONTH: year_month,
            H_TIME_DATE_HOUR: date_hour,
            H_TIME_MINUTE_SECOND: minute_second,
        }

        assert decode_inverter_clock(registers) is None

    def test_leap_day(self):
        assert decode_inverter_clock(pack(datetime(2028, 2, 29, 12, 0, 0))) == datetime(2028, 2, 29, 12, 0, 0)
        assert decode_inverter_clock(
            {H_TIME_YEAR_MONTH: 27 | (2 << 8), H_TIME_DATE_HOUR: 29, H_TIME_MINUTE_SECOND: 0}
        ) is None   # 2027 is not a leap year


class TestAdvanceInverterClock:
    """The clock's presentation: advanced, to the minute, in Home Assistant's zone, DST-aware."""

    @pytest.fixture(autouse=True)
    def london_zone(self):
        previous = dt_util.get_default_time_zone()
        dt_util.set_default_time_zone(LONDON)
        yield
        dt_util.set_default_time_zone(previous)

    def advance(self, reading, age=0, now="2026-10-27T09:46:00+00:00"):
        return advance_inverter_clock(reading, timedelta(seconds=age), datetime.fromisoformat(now))

    def test_is_aware_in_the_home_assistant_zone(self):
        value = self.advance(CLOCK)

        assert value == datetime(2026, 10, 27, 9, 46, 0, tzinfo=LONDON)       # 09:45:59 to the minute
        assert value.utcoffset() == timedelta(0)                               # GMT after the clocks went back

    def test_moves_on_by_the_age_of_the_reading(self):
        assert self.advance(CLOCK, age=240) == datetime(2026, 10, 27, 9, 50, 0, tzinfo=LONDON)

    @pytest.mark.parametrize("seconds,expected_minute", [(0, 45), (29, 45), (30, 46), (59, 46)])
    def test_is_to_the_nearest_minute(self, seconds, expected_minute):
        """Predbat's thresholds are minutes; a state that moves every second is only recorder load."""
        value = self.advance(datetime(2026, 10, 27, 9, 45, seconds))

        assert (value.minute, value.second, value.microsecond) == (expected_minute, 0, 0)

    def test_summer_time_offset_is_applied(self):
        value = self.advance(datetime(2026, 6, 15, 12, 0, 0), now="2026-06-15T11:00:00+00:00")

        assert value.utcoffset() == timedelta(hours=1)
        assert value.isoformat() == "2026-06-15T12:00:00+01:00"

    def test_an_inverter_still_on_bst_reads_an_hour_ahead(self):
        """The failure this exists to show: the real time is 08:45:59 GMT."""
        real_now = datetime(2026, 10, 27, 8, 45, 59, tzinfo=LONDON)

        value = self.advance(CLOCK, now="2026-10-27T08:45:59+00:00")

        assert abs((value - real_now) - timedelta(hours=1)) <= timedelta(seconds=30)    # to the minute

    def test_repeated_hour_when_the_clocks_go_back(self):
        """01:30 happens twice on 25 Oct 2026. A correct clock at the second one is 01:30 GMT.

        Reading it as the first (BST) would make it an hour slow, past Predbat's 30 minute
        error threshold, for the whole hour.
        """
        value = self.advance(datetime(2026, 10, 25, 1, 30, 0), now="2026-10-25T01:30:00+00:00")

        assert value.isoformat() == "2026-10-25T01:30:00+00:00"

    def test_the_first_occurrence_of_the_repeated_hour_is_still_bst(self):
        value = self.advance(datetime(2026, 10, 25, 1, 30, 0), now="2026-10-25T00:30:00+00:00")

        assert value.isoformat() == "2026-10-25T01:30:00+01:00"


class TestDescription:
    def test_is_one_held_sensor_among_calculated_ones(self):
        held = [d["name"] for d in SENSOR_TYPES if d.get("source") == "hold"]

        assert held == ["Inverter Time"]

    def test_depends_on_the_three_clock_registers(self):
        assert clock_description()["depends_on"] == list(CLOCK_REGISTERS)

    def test_is_a_timestamp_derived_from_hold_registers(self):
        desc = clock_description()

        assert desc["register_type"] == "calculated"
        assert desc["source"] == "hold"
        assert desc["device_class"] == "timestamp"
        assert desc["extract"](REAL_READING, MagicMock()) == CLOCK
        assert desc["advance"] is advance_inverter_clock

    def test_disabled_by_default(self):
        """Advancing it every minute is about 1,440 state changes an installation a day."""
        assert clock_description()["enabled"] is False


class HeldSensorCase:
    """Shared setup for sensors built on the held path, with the clock frozen."""

    @pytest.fixture(autouse=True)
    def frozen_london(self, freezer):
        freezer.move_to(NOW)
        previous = dt_util.get_default_time_zone()
        dt_util.set_default_time_zone(LONDON)
        self.freezer = freezer
        yield
        dt_util.set_default_time_zone(previous)

    @pytest.fixture
    def coordinator(self):
        coord = MagicMock()
        coord.async_request_refresh = AsyncMock()
        coord.last_update_success = True
        coord.hass = MagicMock()
        coord.hass.data = {DOMAIN: {ENTRY_ID: {"write_lock": MagicMock()}}}
        coord.data = {"input": {}, **fresh_read(CLOCK)}
        return coord

    @pytest.fixture
    def entry(self):
        cfg = MagicMock()
        cfg.entry_id = ENTRY_ID
        cfg.title = "Test Inverter"
        cfg.data = {}
        return cfg

    def sensor(self, coordinator, entry, desc=None):
        return ModbusBridgeSensor(coordinator, entry, dict(desc or clock_description()), "lxp", None)


class TestClockSensor(HeldSensorCase):
    def test_value_is_the_clock_to_the_minute_in_the_home_assistant_zone(self, coordinator, entry):
        value = self.sensor(coordinator, entry).native_value

        assert value == datetime(2026, 10, 27, 9, 46, 0, tzinfo=LONDON)

    def test_advances_between_settings_reads(self, coordinator, entry):
        """Registers last read four minutes ago: the clock has kept running since."""
        coordinator.data = {"input": {}, **fresh_read(CLOCK, read_ago=240)}

        assert self.sensor(coordinator, entry).native_value == datetime(2026, 10, 27, 9, 50, 0, tzinfo=LONDON)

    def test_a_stopped_clock_is_reported_as_stopped(self, coordinator, entry):
        """A source that is read but not changing must not be advanced past the read.

        Extrapolating from the first reading would carry on telling the time, hiding the
        stopped clock. Each read resets the age, so the reported time falls back to the
        reading, and the difference from the real time grows.
        """
        sensor = self.sensor(coordinator, entry)
        first = sensor.native_value
        self.freezer.tick(timedelta(seconds=75))
        coordinator.data = {"input": {}, **fresh_read(CLOCK)}       # read again: the same registers

        assert sensor.native_value == first

    def test_is_available_while_the_source_is_fresh(self, coordinator, entry):
        assert self.sensor(coordinator, entry).available is True

    @pytest.mark.parametrize("data", [
        None,
        {},
        {"hold": {}},
        {"input": {}},
        {"hold": dict(REAL_READING)},        # registers cached, but with no record of when they were read
    ])
    def test_unknown_until_the_clock_has_been_read(self, coordinator, entry, data):
        coordinator.data = data
        sensor = self.sensor(coordinator, entry)

        assert sensor.native_value is None
        assert sensor.available is False

    def test_every_poll_is_written(self, coordinator, entry):
        """No update-filter fingerprint, or the clock would freeze or never expire.

        depends_on names hold registers 12-14, but the filter looks a calculated sensor's
        dependencies up in the input registers, where 12-14 are the grid voltages.
        """
        assert self.sensor(coordinator, entry)._source_fingerprint() is None


class TestStaleSource(HeldSensorCase):
    """Once the registers have not been read for too long the sensor stops, not just advances."""

    # The limit is three settings passes of five polls, each poll taking the interval plus
    # 10 seconds. The numbers are written out so that a change to the formula is noticed.
    @pytest.mark.parametrize("poll_interval,limit", [(15, 375), (60, 1050), (600, 9150)])
    def test_still_fresh_just_inside_the_limit(self, coordinator, entry, poll_interval, limit):
        entry.data = {CONF_POLL_INTERVAL: poll_interval}
        coordinator.data = {"input": {}, **fresh_read(CLOCK, read_ago=limit - 1)}
        sensor = self.sensor(coordinator, entry)

        assert sensor.native_value is not None
        assert sensor.available is True

    @pytest.mark.parametrize("poll_interval,limit", [(15, 375), (60, 1050), (600, 9150)])
    def test_stale_just_outside_the_limit(self, coordinator, entry, poll_interval, limit):
        entry.data = {CONF_POLL_INTERVAL: poll_interval}
        coordinator.data = {"input": {}, **fresh_read(CLOCK, read_ago=limit + 1)}
        sensor = self.sensor(coordinator, entry)

        assert sensor.native_value is None
        assert sensor.available is False

    def test_the_limit_is_several_settings_passes(self, coordinator, entry):
        """One missed pass must not make the sensor flap."""
        one_pass = HOLD_REGISTER_POLL_EVERY * (60 + HELD_POLL_ALLOWANCE_SECONDS)
        coordinator.data = {"input": {}, **fresh_read(CLOCK, read_ago=2 * one_pass)}

        assert self.sensor(coordinator, entry).available is True

    def test_a_register_with_no_read_time_makes_it_stale(self, coordinator, entry):
        del coordinator.data["hold_read_at"][H_TIME_MINUTE_SECOND]

        assert self.sensor(coordinator, entry).available is False

    def test_the_oldest_register_decides(self, coordinator, entry):
        """The clock is only as fresh as its stalest register, e.g. one block whose read failed."""
        coordinator.data["hold_read_at"][H_TIME_YEAR_MONTH] -= stale_limit() + 1

        sensor = self.sensor(coordinator, entry)

        assert sensor.native_value is None
        assert sensor.available is False

    def test_a_fresh_read_brings_it_back(self, coordinator, entry):
        sensor = self.sensor(coordinator, entry)
        coordinator.data = {"input": {}, **fresh_read(CLOCK, read_ago=stale_limit() + 1)}
        assert sensor.available is False

        coordinator.data = {"input": {}, **fresh_read(CLOCK)}

        assert sensor.available is True
        assert sensor.native_value is not None


class TestGenericHeldPath(HeldSensorCase):
    """The held behaviour belongs to the path, not to the clock: any calculated sensor can use it."""

    def held(self, **overrides):
        return {
            "name": "Held Test", "register_type": "calculated", "source": "hold",
            "depends_on": [20, 21],
            "extract": lambda registers, entry: (
                None if registers.get(20) is None or registers.get(21) is None
                else registers[20] + registers[21]),
            "state_class": None, "unit": "", "enabled": True, "visible": True, "master_only": False,
            **overrides,
        }

    @pytest.fixture
    def data(self):
        stamp = dt_util.utcnow().timestamp()
        return {"input": {}, "hold": {20: 3, 21: 4}, "hold_read_at": {20: stamp, 21: stamp}}

    def test_derives_from_the_hold_registers(self, coordinator, entry, data):
        coordinator.data = data

        assert self.sensor(coordinator, entry, self.held()).native_value == 7

    def test_without_an_advance_the_value_is_held_between_reads(self, coordinator, entry, data):
        coordinator.data = data
        sensor = self.sensor(coordinator, entry, self.held())

        self.freezer.tick(timedelta(seconds=stale_limit() - 1))

        assert sensor.native_value == 7
        assert sensor.available is True

    def test_it_expires_when_the_source_goes_stale(self, coordinator, entry, data):
        coordinator.data = data
        sensor = self.sensor(coordinator, entry, self.held())

        self.freezer.tick(timedelta(seconds=stale_limit() + 1))

        assert sensor.native_value is None
        assert sensor.available is False

    def test_advance_receives_the_value_its_age_and_now(self, coordinator, entry, data):
        seen = []

        def advance(value, age, now):
            seen.append((value, age, now))
            return value + age.total_seconds()

        coordinator.data = data
        sensor = self.sensor(coordinator, entry, self.held(advance=advance))
        self.freezer.tick(timedelta(seconds=30))

        assert sensor.native_value == 37
        assert seen == [(7, timedelta(seconds=30), datetime.fromisoformat(NOW) + timedelta(seconds=30))]

    def test_a_value_the_extractor_cannot_make_is_unknown(self, coordinator, entry, data):
        data["hold"].pop(21)
        coordinator.data = data

        assert self.sensor(coordinator, entry, self.held()).native_value is None

    def test_is_written_on_every_poll(self, coordinator, entry, data):
        coordinator.data = data

        assert self.sensor(coordinator, entry, self.held())._source_fingerprint() is None

    def test_calculated_sensors_from_input_registers_are_untouched(self, coordinator, entry):
        """Held behaviour is opt-in: other calculated sensors keep reading the input registers."""
        desc = next(d for d in SENSOR_TYPES if d["name"] == "Battery Flow")
        coordinator.data = {"input": {10: 300, 11: 0}, "hold": {}}
        sensor = self.sensor(coordinator, entry, desc)

        assert "source" not in desc
        assert sensor.native_value is not None
        assert sensor.available is True
        assert sensor._source_fingerprint() == (300, 0)


class TestInHomeAssistant:
    """The sensor added to a real Home Assistant, driven by coordinator updates.

    Calling native_value directly cannot see how often the state is written, when the
    entity goes unavailable, or what state string Home Assistant publishes.
    """

    GRID_VOLTAGES = {12: 2400, 13: 0, 14: 0}    # the same numbers, as input registers

    @pytest.fixture(autouse=True)
    def frozen(self, freezer):
        freezer.move_to(NOW)
        self.freezer = freezer

    async def _add_sensor(self, hass, enabled=True):
        await hass.config.async_set_time_zone("Europe/London")
        entry = MockConfigEntry(domain=DOMAIN, data={}, title="Inverter")
        entry.add_to_hass(hass)
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"write_lock": None}

        coordinator = DataUpdateCoordinator(
            hass, logging.getLogger(__name__), config_entry=entry, name="test")
        coordinator.data = {"input": dict(self.GRID_VOLTAGES), **fresh_read(CLOCK)}

        desc = clock_description()
        if enabled:
            desc["enabled"] = True       # the description is disabled by default
        sensor = ModbusBridgeSensor(coordinator, entry, desc, "lxp", None)
        await EntityComponent(logging.getLogger(__name__), "sensor", hass).async_add_entities([sensor])
        await hass.async_block_till_done()
        return coordinator, sensor

    async def _poll(self, hass, coordinator, **changes):
        coordinator.async_set_updated_data({**coordinator.data, **changes})
        await hass.async_block_till_done()

    def _state(self, hass, sensor):
        return hass.states.get(sensor.entity_id).state

    async def test_published_state_parses_with_predbats_time_format(self, hass):
        """Predbat parses '%Y-%m-%dT%H:%M:%S%z', and there is no unit to trip a non-numeric class."""
        _, sensor = await self._add_sensor(hass)

        state = hass.states.get(sensor.entity_id)

        assert state.state == "2026-10-27T09:46:00+00:00"
        assert "unit_of_measurement" not in state.attributes
        assert datetime.strptime(state.state, "%Y-%m-%dT%H:%M:%S%z") == datetime(
            2026, 10, 27, 9, 46, 0, tzinfo=ZoneInfo("UTC"))

    async def test_new_clock_reading_is_published_when_grid_voltage_is_unchanged(self, hass):
        """The grid voltage is what registers 12-14 mean as input registers.

        It is constant when the grid is down, and the clock must keep moving then.
        """
        coordinator, sensor = await self._add_sensor(hass)

        for minute in (50, 55):
            self.freezer.tick(timedelta(minutes=5))
            await self._poll(hass, coordinator, **fresh_read(datetime(2026, 10, 27, 9, minute, 59)))

        assert self._state(hass, sensor) == "2026-10-27T09:56:00+00:00"

    async def test_clock_advances_between_settings_reads(self, hass):
        """Settings registers are re-read every 5th poll; the clock must not look 4 minutes slow."""
        coordinator, sensor = await self._add_sensor(hass)

        self.freezer.tick(timedelta(seconds=240))
        await self._poll(hass, coordinator)          # an input-only poll: the hold data is as it was

        assert self._state(hass, sensor) == "2026-10-27T09:50:00+00:00"

    async def test_a_fresh_settings_read_replaces_the_advanced_clock(self, hass):
        coordinator, sensor = await self._add_sensor(hass)
        self.freezer.tick(timedelta(seconds=240))
        await self._poll(hass, coordinator)

        # The settings read shows the inverter an hour ahead of the real 09:49:59.
        await self._poll(hass, coordinator, **fresh_read(datetime(2026, 10, 27, 10, 49, 59)))

        assert self._state(hass, sensor) == "2026-10-27T10:50:00+00:00"

    async def test_state_changes_once_a_minute_however_often_it_polls(self, hass):
        """The point of minute resolution: 15 second polls must not mean a row every 15 seconds."""
        coordinator, sensor = await self._add_sensor(hass)
        changes = []
        hass.bus.async_listen(
            "state_changed",
            lambda event: changes.append(event.data["new_state"].state)
            if event.data["entity_id"] == sensor.entity_id else None,
        )

        polls = 8                                      # two minutes of 15 second polls
        for _ in range(polls):
            self.freezer.tick(timedelta(seconds=15))
            await self._poll(hass, coordinator)

        assert changes == ["2026-10-27T09:47:00+00:00", "2026-10-27T09:48:00+00:00"]
        assert len(changes) < polls

    async def test_goes_unavailable_when_the_source_goes_stale(self, hass):
        """A dead connection serves cached registers; it must not keep telling the time."""
        coordinator, sensor = await self._add_sensor(hass)
        assert self._state(hass, sensor) != "unavailable"

        self.freezer.tick(timedelta(seconds=stale_limit() + 1))
        await self._poll(hass, coordinator)              # polls go on, but nothing new is read

        assert self._state(hass, sensor) == "unavailable"

    async def test_still_available_just_inside_the_limit(self, hass):
        coordinator, sensor = await self._add_sensor(hass)

        self.freezer.tick(timedelta(seconds=stale_limit() - 1))
        await self._poll(hass, coordinator)

        assert self._state(hass, sensor) != "unavailable"

    async def test_comes_back_when_the_registers_are_read_again(self, hass):
        coordinator, sensor = await self._add_sensor(hass)
        self.freezer.tick(timedelta(seconds=stale_limit() + 1))
        await self._poll(hass, coordinator)
        assert self._state(hass, sensor) == "unavailable"

        await self._poll(hass, coordinator, **fresh_read(datetime(2026, 10, 27, 10, 3, 0)))

        assert self._state(hass, sensor) == "2026-10-27T10:03:00+00:00"

    async def test_repeated_hour_when_the_clocks_go_back(self, hass):
        """01:30 happens twice on 25 Oct 2026. A correct clock at the second one is 01:30 GMT."""
        self.freezer.move_to("2026-10-25T01:30:00+00:00")
        coordinator, sensor = await self._add_sensor(hass)

        await self._poll(hass, coordinator, **fresh_read(datetime(2026, 10, 25, 1, 30, 0)))

        assert self._state(hass, sensor) == "2026-10-25T01:30:00+00:00"

    async def test_disabled_by_default_in_the_entity_registry(self, hass):
        """Registered, but disabled until someone turns it on, with no state until then."""
        _, sensor = await self._add_sensor(hass, enabled=False)

        entry = er.async_get(hass).async_get(sensor.entity_id)

        assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
        assert hass.states.get(sensor.entity_id) is None
