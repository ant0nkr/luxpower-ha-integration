import logging
from datetime import time as dt_time

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import *
from .entity import ModbusBridgeEntity
# Import ALL entity description types
from .entity_descriptions.sensor_types import SENSOR_TYPES, BATTERY_SENSOR_TYPES
from .entity_descriptions.number_types import NUMBER_TYPES
from .entity_descriptions.selectbox_types import SELECTBOX_TYPES
from .entity_descriptions.switch_types import SWITCH_TYPES
from .entity_descriptions.time_types import TIME_TYPES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensor entities from a config entry."""
    is_read_only = entry.data.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entity_prefix = hass.data[DOMAIN][entry.entry_id]['settings'].get(CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX)
    api_client = hass.data[DOMAIN][entry.entry_id].get("api_client")
    battery_entities = set(hass.data[DOMAIN][entry.entry_id]["settings"].get(CONF_BATTERY_ENTITIES, DEFAULT_BATTERY_ENTITIES).replace(" ","").split(","))

    # Create a list to hold all the entities we're about to create
    entities = [
        ModbusBridgeSensor(coordinator, entry, desc, entity_prefix, api_client)
        for desc in SENSOR_TYPES
    ]

    # If in read-only mode, create read-only sensors for all the control types
    if is_read_only:
        _LOGGER.info("Read-only mode: creating sensors for numbers, switches, selects, and times.")
        
        # Combine all control type descriptions into one list to iterate through
        readonly_types = (
            (NUMBER_TYPES, Platform.NUMBER),
            (SWITCH_TYPES, Platform.SWITCH),
            (SELECTBOX_TYPES, Platform.SELECT),
            (TIME_TYPES, Platform.TIME),
        )
        
        for descriptions, platform in readonly_types:
            for desc in descriptions:
                entities.append(ModbusBridgeReadOnlySensor(coordinator, entry, desc, entity_prefix, platform))

    # Inverter does not give battery data all time
    # Because of this we should create when possible the entities at startup
    # for some use cases this is not a problem, but if user wants the entities defined at startup 
    # can define the serial numbers on configuration instead of auto, or user auto,SERIAL to create at startup just some of the batteries
    known_batteries = set()

    def _create_battery_sensors(serial) -> None:
        known_batteries.add(serial)
        battery_entities = []
        for generic_desc in BATTERY_SENSOR_TYPES:
            # To create a device for each battery, we have to use specific device group using the serial
            desc = dict(generic_desc)
            desc["device_group"] = "Battery " + serial

            battery_entities.append(ModbusBridgeBatterySensor(coordinator, entry, desc, entity_prefix, api_client, serial))

        _LOGGER.info(f"Creating battery {len(battery_entities)} entities for {serial}")
        return battery_entities
    
    def _check_for_new_batteries() -> None:
        battery = coordinator.data.get("battery", {})
        if len(battery):
            for serial, value in battery.items():
                if not serial in known_batteries:
                    async_add_entities(_create_battery_sensors(serial))

                # Until we discover all the fields keep this debug 
                _LOGGER.debug(f"check_for_new_batteries -> battery info: {serial} {value}")
        
    # create entities for specific batteries
    # this allow to keep only specific batteries if user don't want all battery data
    for serial in battery_entities:
        if serial not in ('auto','none'):
           entities.extend(_create_battery_sensors(serial))
           
    async_add_entities(entities)
    if 'auto' in battery_entities:
        _LOGGER.info("battery discovery enabled")
        entry.async_on_unload(
           coordinator.async_add_listener(_check_for_new_batteries)
        )

class ModbusBridgeSensor(ModbusBridgeEntity, SensorEntity):
    """Represents a standard sensor entity that gets its data from the coordinator."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry, desc: dict, entity_prefix: str, api_client):
        """Initialize the sensor."""
        # Call the parent __init__ to handle all the common setup
        super().__init__(coordinator, entry, desc, entity_prefix, api_client)
        
        # Set sensor-specific attributes from the description dictionary
        self._attr_state_class = self._desc.get("state_class")
        self._attr_suggested_display_precision = self._desc.get("suggested_display_precision")
        
        if "options" in self._desc:
            # This is a text sensor (like Inverter State), so it doesn't have a unit
            self._attr_device_class = None
            self._attr_native_unit_of_measurement = None
        else:
            # This is a numerical sensor
            self._attr_device_class = self._desc.get("device_class")
            self._attr_native_unit_of_measurement = self._desc.get("unit")

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # Don't return a value until the coordinator has fetched data for the first time
        if not self.coordinator.data:
            return None

        raw_val = None

        # Determine the raw (unscaled) value based on the sensor type
        if self._register_type == "calculated":
            # For calculated sensors, call the special 'extract' lambda
            input_data = self.coordinator.data.get("input", {})
            calculation_func = self._desc["extract"]
            raw_val = calculation_func(input_data, self._entry)
        elif self._register_type == "battery": 
            battery_data = self.coordinator.data.get("battery", {}).get(self._battery_serial, {})
            value = battery_data.get(self._register)
            if value is not None:
                # Use the 'extract' lambda to parse the value (e.g., for packed bits)
                raw_val = self._desc["extract"](value)
        elif self._register_type == "battery_calculated": 
            battery_data = self.coordinator.data.get("battery", {}).get(self._battery_serial, {})
            calculation_func = self._desc["extract"]
            raw_val = calculation_func(battery_data, self._entry)
            
        else:
            # For standard register-based sensors, get the value from the coordinator's data
            registers = self.coordinator.data.get(self._register_type, {})
            value = registers.get(self._register)
            if value is not None:
                # Use the 'extract' lambda to parse the value (e.g., for packed bits)
                raw_val = self._desc["extract"](value)

        # If we still couldn't determine a raw value, return an unknown state
        if raw_val is None:
            return None

        # If the sensor has an 'options' map, use it to return a text state
        if "options" in self._desc:
            return self._desc["options"].get(raw_val, self._desc.get("default", "Unknown"))

        # If the sensor has a 'scale' factor, apply it
        if "scale" in self._desc:
            scale = self._desc["scale"]
            scaled_value = raw_val * scale
            # Return a clean integer if it's a whole number, otherwise return the float
            return int(scaled_value) if scaled_value == int(scaled_value) else scaled_value

        # For any other sensor (like a code), return the raw value directly
        return raw_val

class ModbusBridgeBatterySensor(ModbusBridgeSensor):
    """Represents a Battery sensor entity that gets its data from the coordinator."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry, desc: dict, entity_prefix: str, api_client, battery_serial):
        """Initialize the sensor."""
        self._battery_serial = battery_serial
        # Call the parent __init__ to handle all the common setup
        super().__init__(coordinator, entry, desc, entity_prefix, api_client)



class ModbusBridgeReadOnlySensor(ModbusBridgeEntity, SensorEntity):
    """A sensor that displays the read-only state of a control entity."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry, desc: dict, entity_prefix: str, platform: Platform):
        """Initialize the read-only sensor."""
        # Pass None for api_client as this entity is read-only
        super().__init__(coordinator, entry, desc, entity_prefix, None) 
        self._platform = platform # Store the original platform (number, switch, etc.)
        self._attr_icon = self._desc.get("icon")
        # Add a suffix to the unique_id to prevent clashes with the real entity
        self._attr_unique_id = f"{super().unique_id}_readonly"

    @property
    def native_value(self):
        """Return the state of the sensor, formatted correctly for its original type."""
        register_value = self.coordinator.data.get(self._register_type, {}).get(self._register)
        if register_value is None: 
            return None

        # Determine how to display the value based on its original platform type
        if self._platform == Platform.NUMBER:
            multiplier = self._desc.get("multiplier", 1)
            scaled_value = register_value / multiplier
            return int(scaled_value) if scaled_value == int(scaled_value) else scaled_value
        
        elif self._platform == Platform.SWITCH:
            is_on = bool(self._desc["extract"](register_value))
            return "On" if is_on else "Off"

        elif self._platform == Platform.SELECT:
            index = self._desc["extract"](register_value)
            return self._desc["options"].get(index)

        elif self._platform == Platform.TIME:
            hour, minute = self._desc["extract"](register_value)
            if not (0 <= hour <= 23 and 0 <= minute <= 59): 
                return None
            return dt_time(hour=hour, minute=minute).strftime("%H:%M:%S")

        return register_value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement if it was originally a number entity."""
        if self._platform == Platform.NUMBER:
            return self._desc.get("unit")
        return None
