import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX
from .entity import ModbusBridgeEntity
from .entity_descriptions.button_types import BUTTON_TYPES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up button entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entity_prefix = hass.data[DOMAIN][entry.entry_id]['settings'].get(CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX)
    api_client = hass.data[DOMAIN][entry.entry_id]["api_client"]
    
    entities = [
        ModbusBridgeButton(coordinator, entry, desc, entity_prefix, api_client)
        for desc in BUTTON_TYPES
    ]
    async_add_entities(entities)

class ModbusBridgeButton(ModbusBridgeEntity, ButtonEntity):
    """Represents a button entity that writes a value to a register."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry, desc: dict, entity_prefix: str, api_client):
        """Initialize the button entity."""
        super().__init__(coordinator, entry, desc, entity_prefix, api_client)
        
        # Store the function that determines the value to write when pressed
        self._press = desc["press"]
        self._attr_icon = desc.get("icon")

    async def async_press(self) -> None:
        """Handle the button press action."""
        if not self._api_client:
            _LOGGER.error("API client not found, cannot press button '%s'", self.name)
            return

        # Get the current value of the register, as the press action might need it
        original_register_value = self.coordinator.data.get(self._register_type, {}).get(self._register, 0)

        # Use the press function from the description to determine the new value to write
        new_register_value = self._press(original_register_value)

        # Call the write method on the API client
        success = await self._api_client.async_write_register(self._register, new_register_value)
        
        if success:
            # After a successful write, request an immediate refresh from the coordinator.
            # This makes the UI update quickly with any state changes caused by the button press.
            await self.coordinator.async_request_refresh()