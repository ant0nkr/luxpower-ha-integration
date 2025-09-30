"""Base class for LuxPower Modbus entities."""
import logging  # Add this import
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from .utils import format_firmware_version
from .const import DOMAIN, INTEGRATION_TITLE, CONF_INVERTER_SERIAL
from .constants.input_registers import I_MASTER_SLAVE_PARALLEL_STATUS

_LOGGER = logging.getLogger(__name__)

class ModbusBridgeEntity(CoordinatorEntity):
    """A base class for all LuxPower Modbus entities."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry, desc: dict, entity_prefix: str, api_client):

        """Initialize the entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._desc = desc
        self._entity_prefix = entity_prefix
        self._api_client = api_client

        # Set common attributes
        self._attr_name = f"{entity_prefix} {self._desc['name']}"
        self._attr_entity_registry_enabled_default = self._desc.get("enabled", True)
        self._attr_entity_registry_visible_default = self._desc.get("visible", True)
        
        is_master_only_control = self._desc.get("master_only", False)
        if is_master_only_control and not self.is_master:
            self._attr_entity_registry_enabled_default = False

        # Generate unique ID based on whether it's a register-based or calculated entity
        if self._desc.get("register_type") == "calculated":
            dependencies_str = '_'.join(map(str, self._desc['depends_on']))
            self._attr_unique_id = f"{entity_prefix}_{dependencies_str}_{self._desc['name'].replace(' ', '_').lower()}"
            self._register = None
            self._register_type = "calculated"
        else:
            self._register = self._desc["register"]
            self._register_type = self._desc.get("register_type")
            self._attr_unique_id = f"{entity_prefix}_{self._register}_{self._desc['name'].replace(' ', '_').lower()}"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self._register_type == "calculated":
            return {"dependencies": self._desc.get("depends_on")}
        return {
            "register": self._register,
            "register_type": self._register_type,
        }

    
    @property
    def device_info(self):
        """Return device information for all entities."""
        
        if "sub_device" in self._desc:
            sub_device = self._desc.get("sub_device")
            return {
                "identifiers": {(DOMAIN, self._entry.entry_id, sub_device)},
                "via_device": (DOMAIN, self._entry.entry_id),
                "name": (self._entry.title or INTEGRATION_TITLE) + " " + sub_device,
                "manufacturer": "LuxpowerTek",
                "model": self._entry.data.get("model") or "Unknown",
            }
        else:
            # Get the hold registers from the coordinator's data
            hold_registers = self.coordinator.data.get("hold", {})
        
            # Specifically check for the registers required for the firmware version
            required_fw_regs = {k: hold_registers.get(k) for k in [7, 8, 9, 10]}

            # Use the helper function to format the firmware version
            firmware_version = format_firmware_version(hold_registers)

            return {
                "identifiers": {(DOMAIN, self._entry.entry_id)},
                "name": self._entry.title or INTEGRATION_TITLE,
                "manufacturer": "LuxpowerTek",
                "model": self._entry.data.get("model") or "Unknown",
                "serial_number": self._entry.data.get(CONF_INVERTER_SERIAL),
                "sw_version": firmware_version,
            }

    @property
    def is_master(self) -> bool:
        """Return True if the inverter is the master or standalone."""
        parallel_status = self.coordinator.data.get("input", {}).get(I_MASTER_SLAVE_PARALLEL_STATUS)
        if parallel_status is None:
            return True # Assume master if status is unavailable
        role = parallel_status & 3 # Extract bits 0-1
        return role != 2 # Not a slave