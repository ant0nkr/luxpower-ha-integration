"""Base class for LuxPower Modbus entities."""
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity import generate_entity_id
from .utils import format_firmware_version
from .const import DOMAIN, INTEGRATION_TITLE, CONF_INVERTER_SERIAL, CONF_ENABLE_DEVICE_GROUPING, DEFAULT_ENABLE_DEVICE_GROUPING
from .constants.input_registers import I_MASTER_SLAVE_PARALLEL_STATUS

_LOGGER = logging.getLogger(__name__)

class ModbusBridgeEntity(CoordinatorEntity):
    """A base class for all LuxPower Modbus entities."""

    # Subclasses can set _battery_serial before calling super().__init__()
    _battery_serial = None

    def __init__(self, coordinator: DataUpdateCoordinator, entry, desc: dict, entity_prefix: str, api_client):

        """Initialize the entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._desc = desc
        self._entity_prefix = entity_prefix
        self._api_client = api_client

        # Set common attributes
        self._register_type = self._desc.get("register_type", "")
        id_name = self._desc['name'].replace(' ', '_').lower()

        if self._register_type.startswith("battery"):
            self._attr_name = self._desc['name']
            self.entity_id = generate_entity_id(
                "sensor.{}", f"{entity_prefix}_{self._battery_serial}_{id_name}",
                hass=coordinator.hass)
        else:
            self._attr_name = f"{entity_prefix} {self._desc['name']}"

        self._attr_entity_registry_enabled_default = self._desc.get("enabled", True)
        self._attr_entity_registry_visible_default = self._desc.get("visible", True)

        is_master_only_control = self._desc.get("master_only", False)
        if is_master_only_control and not self.is_master:
            self._attr_entity_registry_enabled_default = False

        # Generate unique ID based on register type
        if self._register_type in ("calculated", "battery_calculated"):
            dependencies_str = '_'.join(map(str, self._desc['depends_on']))
            if self._register_type == "battery_calculated":
                self._attr_unique_id = f"{entity_prefix}_batt_{self._battery_serial}_{dependencies_str}_{id_name}"
            else:
                self._attr_unique_id = f"{entity_prefix}_{dependencies_str}_{id_name}"
            self._register = None
        else:
            self._register = self._desc["register"]
            if self._register_type == "battery":
                # Use battery serial in unique_id so history is preserved per-battery
                self._attr_unique_id = f"{entity_prefix}_batt_{self._battery_serial}_{self._register}_{id_name}"
            else:
                self._attr_unique_id = f"{entity_prefix}_{self._register}_{id_name}"

    @property
    def _write_lock(self):
        """Return the per-entry lock that serialises read-modify-write cycles."""
        return self.coordinator.hass.data[DOMAIN][self._entry.entry_id]["write_lock"]

    async def _async_write_register(self, compose_value) -> bool:
        """Write this entity's register and re-sync from the inverter.

        ``compose_value`` receives the current register value and returns the value
        to write, so registers packing several controls keep their sibling bits.

        The lock matters because many registers back more than one entity: without
        it, two writes started within one poll interval would both compose from the
        same pre-write snapshot and the second would undo the first.
        """
        if not self._api_client:
            _LOGGER.error("API client not found, cannot write to '%s'", self.name)
            return False

        async with self._write_lock:
            registers = self.coordinator.data.setdefault(self._register_type, {})
            current_value = registers.get(self._register, 0)
            value_to_write = compose_value(current_value)

            if not await self._api_client.async_write_register(self._register, value_to_write):
                return False

            # Show the new value immediately, but treat it as provisional: only the
            # next poll proves what the inverter actually stored.
            registers[self._register] = value_to_write
            self.async_write_ha_state()

        # Requested outside the lock; the coordinator debounces concurrent requests.
        await self.coordinator.async_request_refresh()
        return True

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

        # Get the hold registers from the coordinator's data. This property is read
        # by Home Assistant before the first poll completes, so data may be missing.
        hold_registers = (self.coordinator.data or {}).get("hold", {})

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
        parallel_status = (self.coordinator.data or {}).get("input", {}).get(I_MASTER_SLAVE_PARALLEL_STATUS)
        if parallel_status is None:
            return True # Assume master if status is unavailable
        role = parallel_status & 3 # Extract bits 0-1
        return role != 2 # Not a slave
