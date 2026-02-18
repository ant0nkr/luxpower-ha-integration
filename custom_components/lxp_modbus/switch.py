import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX
from .entity import ModbusBridgeEntity
from .entity_descriptions.switch_types import SWITCH_TYPES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up switch entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entity_prefix = hass.data[DOMAIN][entry.entry_id]['settings'].get(CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX)
    api_client = hass.data[DOMAIN][entry.entry_id]["api_client"]

    entities = [
        ModbusBridgeSwitch(coordinator, entry, desc, entity_prefix, api_client)
        for desc in SWITCH_TYPES
    ]
    async_add_entities(entities)

class ModbusBridgeSwitch(ModbusBridgeEntity, SwitchEntity):
    """Represents a switch entity that controls a bit in a register."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry, desc: dict, entity_prefix: str, api_client):
        """Initialize the switch."""
        super().__init__(coordinator, entry, desc, entity_prefix, api_client)
        # Store the functions for reading and writing the bit
        self._extract = desc["extract"]
        self._compose = desc["compose"]
        self._attr_icon = desc.get("icon")
        self._attr_device_class = desc.get("device_class")
        self._api_client = api_client

    @property
    def is_on(self) -> bool | None:
        """Return the state of the switch."""
        # Get the full register value from the coordinator's data
        register_value = self.coordinator.data.get(self._register_type, {}).get(self._register)
        if register_value is None:
            return None
        # Use the extract function to get the single bit's state (0 or 1)
        return bool(self._extract(register_value))

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._set_bit_value(1)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._set_bit_value(0)

    async def _set_bit_value(self, value: int) -> None:
        """Compose the new register value and write it to the inverter."""
        # Get the shared API client from hass.data
        if not self._api_client:
            _LOGGER.error("API client not found, cannot write to switch '%s'", self.name)
            return

        # Get the current value of the entire register to modify it
        original_register_value = self.coordinator.data.get(self._register_type, {}).get(self._register, 0)

        # Use the compose function to set the desired bit within the register value
        new_register_value = self._compose(original_register_value, value)

        # Call the new write method on the API client
        success = await self._api_client.async_write_register(self._register, new_register_value)
        
        if success:
            # Optimistically update the coordinator's data with the new register value
            self.coordinator.data[self._register_type][self._register] = new_register_value
            # Tell HA to update the state of this entity immediately
            self.async_write_ha_state()