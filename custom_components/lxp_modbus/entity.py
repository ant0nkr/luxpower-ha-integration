"""Base class for LuxPower Modbus entities."""
import logging  # Add this import
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity import generate_entity_id
from .utils import format_firmware_version
from .const import DOMAIN, INTEGRATION_TITLE, CONF_INVERTER_SERIAL, CONF_ENABLE_DEVICE_GROUPING, DEFAULT_ENABLE_DEVICE_GROUPING
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
        self._register_type = self._desc.get("register_type","")
        id_name = self._desc['name'].replace(' ', '_').lower()
        if self._register_type.startswith("battery") :
            self._attr_name = f"{self._desc['name']}"
            #TODO check the correct domain, but currently battery data are all from sensor domain
            self.entity_id = generate_entity_id("sensor.{}", f"{entity_prefix}_{self._battery_serial}_{id_name}", hass=coordinator.hass)
        else:
            self._attr_name = f"{entity_prefix} {self._desc['name']}"
        self._attr_entity_registry_enabled_default = self._desc.get("enabled", True)
        self._attr_entity_registry_visible_default = self._desc.get("visible", True)
        
        is_master_only_control = self._desc.get("master_only", False)
        if is_master_only_control and not self.is_master:
            self._attr_entity_registry_enabled_default = False

        # Generate unique ID based on whether it's a register-based or calculated entity
        if self._register_type == "calculated":
            dependencies_str = '_'.join(map(str, self._desc['depends_on']))
            self._attr_unique_id = f"{entity_prefix}_{dependencies_str}_{id_name}"
            self._register = None
        elif self._register_type == "battery_calculated":
            dependencies_str = '_'.join(map(str, self._desc['depends_on']))
            self._attr_unique_id = f"{entity_prefix}_batt_{self._battery_serial}_{dependencies_str}_{id_name}"
            self._register = None
        else:
            self._register = self._desc["register"]
            if self._register_type == "battery":
                # batteries can be moved between inverters, using entity preffix will not keep the history when user move a battery
                # but this way user can have separate history of the battery when connected to each inverter
                self._attr_unique_id = f"{entity_prefix}_batt_{self._battery_serial}_{self._register}_{id_name}"
            else:
                #TODO check if this is correct because same register can be on hold or input, maybe register_type should be included in unique_id
                # but changing this will break old data history....
                self._attr_unique_id = f"{entity_prefix}_{self._register}_{id_name}"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self._register_type.endswith("calculated"):
            return {"dependencies": self._desc.get("depends_on")}
        return {
            "register": self._register,
            "register_type": self._register_type,
        }

    
    @property
    def device_info(self):
        """Return device information for all entities."""
        
        # Get the hold registers from the coordinator's data
        hold_registers = self.coordinator.data.get("hold", {})
        
        # Specifically check for the registers required for the firmware version
        required_fw_regs = {k: hold_registers.get(k) for k in [7, 8, 9, 10]}

        # Use the helper function to format the firmware version
        firmware_version = format_firmware_version(hold_registers)

        # Check if device grouping is enabled in configuration
        enable_device_grouping = self._entry.data.get(CONF_ENABLE_DEVICE_GROUPING, DEFAULT_ENABLE_DEVICE_GROUPING)
        
        # Check if entity has a device group (sub-device) and if grouping is enabled
        device_group = self._desc.get("device_group")
        
        if device_group and enable_device_grouping:
            # Create sub-device grouped under main inverter
            main_device_id = (DOMAIN, self._entry.entry_id)
            sub_device_id = (DOMAIN, f"{self._entry.entry_id}_{device_group}")
            
            return {
                "identifiers": {sub_device_id},
                "name": f"{self._entry.title or INTEGRATION_TITLE} - {device_group}",
                "manufacturer": "LuxpowerTek",
                "model": self._entry.data.get("model") or "Unknown",
                "via_device": main_device_id,  # Link to parent device
            }
        else:
            # Main inverter device (either no device_group or grouping disabled)
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
