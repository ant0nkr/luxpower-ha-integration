import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_DONGLE_SERIAL,
    CONF_INVERTER_SERIAL,
    CONF_POLL_INTERVAL,
    CONF_ENTITY_PREFIX,
    CONF_RATED_POWER,
    CONF_READ_ONLY,
    CONF_REGISTER_BLOCK_SIZE,
    CONF_CONNECTION_RETRIES,
    CONF_ENABLE_DEVICE_GROUPING,
    CONF_BATTERY_ENTITIES,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_ENTITY_PREFIX,
    DEFAULT_RATED_POWER,
    DEFAULT_READ_ONLY,
    DEFAULT_REGISTER_BLOCK_SIZE,
    DEFAULT_CONNECTION_RETRIES,
    DEFAULT_ENABLE_DEVICE_GROUPING,
    DEFAULT_BATTERY_ENTITIES,
    LEGACY_REGISTER_BLOCK_SIZE,
    SERIAL_LENGTH,
)
from .classes.inverter_discovery import get_inverter_model_from_device

_LOGGER = logging.getLogger(__name__)


def validate_serial(value):
    """Validate that the serial number is exactly SERIAL_LENGTH characters."""
    value = str(value)
    if len(value) != SERIAL_LENGTH:
        raise vol.Invalid(f"Serial number must be exactly {SERIAL_LENGTH} characters.")
    return value

def validate_connection_retries(value):
    """Validate that the connection retries value is between 1 and 10."""
    value = int(value)
    if value < 1 or value > 10:
        raise vol.Invalid("Connection retry attempts must be between 1 and 10.")
    return value

class LxpModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup flow for the component."""
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return LxpModbusOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                validate_serial(user_input[CONF_DONGLE_SERIAL])
                validate_serial(user_input[CONF_INVERTER_SERIAL])
                
                # Validate connection retries
                try:
                    validate_connection_retries(user_input.get(CONF_CONNECTION_RETRIES, DEFAULT_CONNECTION_RETRIES))
                except vol.Invalid:
                    errors[CONF_CONNECTION_RETRIES] = "invalid_connection_retries"
                
                if not errors:
                    model = await get_inverter_model_from_device(user_input[CONF_HOST], user_input[CONF_PORT], user_input[CONF_DONGLE_SERIAL], user_input[CONF_INVERTER_SERIAL])
                    if not model:
                        errors["base"] = "model_fetch_failed"
                    else:
                        user_input["model"] = model
                        title = user_input.get(CONF_ENTITY_PREFIX) or "Luxpower Inverter"
                        return self.async_create_entry(title=title, data=user_input)
            except vol.Invalid:
                errors["base"] = "invalid_serial"
        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=8000): int,
            vol.Required(CONF_DONGLE_SERIAL): str,
            vol.Required(CONF_INVERTER_SERIAL): str,
            vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(int, vol.Range(min=2, max=600)),
            vol.Optional(CONF_ENTITY_PREFIX, default=DEFAULT_ENTITY_PREFIX): str,
            vol.Required(CONF_RATED_POWER, default=DEFAULT_RATED_POWER): vol.All(int, vol.Range(min=1000, max=100000)),
            vol.Optional(CONF_READ_ONLY, default=DEFAULT_READ_ONLY): bool,
            vol.Optional(CONF_REGISTER_BLOCK_SIZE, default=DEFAULT_REGISTER_BLOCK_SIZE): vol.In([DEFAULT_REGISTER_BLOCK_SIZE, LEGACY_REGISTER_BLOCK_SIZE]),
            vol.Required(CONF_CONNECTION_RETRIES, default=DEFAULT_CONNECTION_RETRIES): vol.All(int, vol.Range(min=1, max=10)),
            vol.Optional(CONF_ENABLE_DEVICE_GROUPING, default=DEFAULT_ENABLE_DEVICE_GROUPING): bool,
            vol.Optional(CONF_BATTERY_ENTITIES, default=DEFAULT_BATTERY_ENTITIES): str,
        })
        return self.async_show_form(step_id="user", data_schema=self.add_suggested_values_to_schema(data_schema, user_input), errors=errors)

class LxpModbusOptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow (reconfiguration) for the component."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        # self.config_entry is automatically available here
        current_config = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            try:
                validate_serial(user_input[CONF_DONGLE_SERIAL])
                validate_serial(user_input[CONF_INVERTER_SERIAL])
                
                # Validate connection retries
                try:
                    validate_connection_retries(user_input.get(CONF_CONNECTION_RETRIES, DEFAULT_CONNECTION_RETRIES))
                except vol.Invalid:
                    errors[CONF_CONNECTION_RETRIES] = "invalid_connection_retries"
                
                if not errors:
                    model = await get_inverter_model_from_device(
                        user_input[CONF_HOST],
                        user_input[CONF_PORT],
                        user_input[CONF_DONGLE_SERIAL],
                        user_input[CONF_INVERTER_SERIAL]
                    )
                    if not model:
                        errors["base"] = "model_fetch_failed"
                    else:
                        new_data = {**current_config, **user_input}
                        new_data["model"] = model
                        
                        self.hass.config_entries.async_update_entry(
                            self.config_entry, data=new_data, options={}
                        )
                        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                        return self.async_create_entry(title="", data={})

            except vol.Invalid:
                errors["base"] = "invalid_serial"
        
        options_schema = vol.Schema({
            vol.Required(CONF_HOST, default=current_config.get(CONF_HOST)): str,
            vol.Required(CONF_PORT, default=current_config.get(CONF_PORT)): int,
            vol.Required(CONF_DONGLE_SERIAL, default=current_config.get(CONF_DONGLE_SERIAL)): str,
            vol.Required(CONF_INVERTER_SERIAL, default=current_config.get(CONF_INVERTER_SERIAL)): str,
            vol.Required(CONF_POLL_INTERVAL, default=current_config.get(CONF_POLL_INTERVAL)): vol.All(int, vol.Range(min=2, max=600)),
            vol.Optional(CONF_ENTITY_PREFIX, default=current_config.get(CONF_ENTITY_PREFIX, '')): vol.All(str),
            vol.Required(CONF_RATED_POWER, default=current_config.get(CONF_RATED_POWER)): vol.All(int, vol.Range(min=1000, max=100000)),
            vol.Optional(CONF_READ_ONLY, default=DEFAULT_READ_ONLY): bool,
            vol.Optional(CONF_REGISTER_BLOCK_SIZE, default=current_config.get(CONF_REGISTER_BLOCK_SIZE, DEFAULT_REGISTER_BLOCK_SIZE)): vol.In([DEFAULT_REGISTER_BLOCK_SIZE, LEGACY_REGISTER_BLOCK_SIZE]),
            vol.Required(CONF_CONNECTION_RETRIES, default=current_config.get(CONF_CONNECTION_RETRIES, DEFAULT_CONNECTION_RETRIES)): vol.All(int, vol.Range(min=1, max=10)),
            vol.Optional(CONF_ENABLE_DEVICE_GROUPING, default=current_config.get(CONF_ENABLE_DEVICE_GROUPING, DEFAULT_ENABLE_DEVICE_GROUPING)): bool,
            vol.Optional(CONF_BATTERY_ENTITIES, default=current_config.get(CONF_BATTERY_ENTITIES, DEFAULT_BATTERY_ENTITIES)): str,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(options_schema, current_config),
            errors=errors,
        )