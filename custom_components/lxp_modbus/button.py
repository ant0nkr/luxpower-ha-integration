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
        # The press function may need the current register value, so it composes under
        # the shared write lock and the coordinator is refreshed afterwards.
        await self._async_write_register(lambda current: self._press(current))
