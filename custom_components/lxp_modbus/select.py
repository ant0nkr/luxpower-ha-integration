import logging

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX
from .entity import ModbusBridgeEntity
from .entity_descriptions.selectbox_types import SELECTBOX_TYPES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up select entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entity_prefix = hass.data[DOMAIN][entry.entry_id]['settings'].get(CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX)
    api_client = hass.data[DOMAIN][entry.entry_id]["api_client"]
    
    entities = [
        ModbusBridgeSelect(coordinator, entry, desc, entity_prefix, api_client)
        for desc in SELECTBOX_TYPES
    ]
    async_add_entities(entities)

class ModbusBridgeSelect(ModbusBridgeEntity, SelectEntity):
    """Represents a select entity that maps a register value to a list of options."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry, desc: dict, entity_prefix: str, api_client):
        """Initialize the select entity."""
        super().__init__(coordinator, entry, desc, entity_prefix, api_client)
        # Store functions and options specific to the select entity
        self._extract = desc["extract"]
        self._compose = desc["compose"]
        self._attr_options = list(desc["options"].values())
        self._option_keys = {v: k for k, v in desc["options"].items()}
        self._attr_icon = desc.get("icon")

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        register_value = self.coordinator.data.get(self._register_type, {}).get(self._register)
        if register_value is None:
            return None
        
        # Use the extract function to get the numerical index from the register
        index = self._extract(register_value)
        # Find the matching string option from the description
        return self._desc["options"].get(index)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Get the numerical index for the chosen string option
        index = self._option_keys.get(option)
        if index is None:
            _LOGGER.warning("Invalid option selected for %s: %s", self.name, option)
            return

        if not self._api_client:
            _LOGGER.error("API client not found, cannot write to select '%s'", self.name)
            return
            
        # Get the current value of the entire register to modify it
        original_register_value = self.coordinator.data.get(self._register_type, {}).get(self._register, 0)

        # Use the compose function to create the new register value
        new_register_value = self._compose(original_register_value, index)

        # Call the write method on the API client
        success = await self._api_client.async_write_register(self._register, new_register_value)
        
        if success:
            # Optimistically update the coordinator's data and refresh the entity
            self.coordinator.data[self._register_type][self._register] = new_register_value
            self.async_write_ha_state()