from typing import Final
from homeassistant.const import Platform

DOMAIN = "lxp_modbus"

PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.TIME,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.SWITCH,
]

CONF_HOST = "host"
CONF_PORT = "port"
CONF_DONGLE_SERIAL = "dongle_serial"
CONF_INVERTER_SERIAL = "inverter_serial"
CONF_POLL_INTERVAL = "poll_interval"
CONF_ENTITY_PREFIX = "entity_prefix"
CONF_RATED_POWER = "rated_power"
CONF_READ_ONLY = "read_only"
CONF_REGISTER_BLOCK_SIZE = "register_block_size"
CONF_CONNECTION_RETRIES = "connection_retries"
CONF_ENABLE_DEVICE_GROUPING = "enable_device_grouping"
CONF_PROTOCOL_TYPE = "protocol_type"

INTEGRATION_TITLE = "LuxPower Inverter (Modbus)"


DEFAULT_POLL_INTERVAL = 60  # or whatever default you prefer, in seconds
DEFAULT_ENTITY_PREFIX = ""
DEFAULT_RATED_POWER = 5000
DEFAULT_READ_ONLY = False
DEFAULT_PORT = 8000
DEFAULT_REGISTER_BLOCK_SIZE = 125
DEFAULT_CONNECTION_RETRIES = 3
DEFAULT_ENABLE_DEVICE_GROUPING = True
DEFAULT_PROTOCOL_TYPE = "lxp"

# Protocol type options
PROTOCOL_TYPE_LXP = "lxp"
PROTOCOL_TYPE_DEFAULT = "default"

# Legacy firmware may only support smaller block sizes
LEGACY_REGISTER_BLOCK_SIZE = 40
TOTAL_REGISTERS = 300 # Total number of registers available

# Packet recovery constants
MAX_PACKET_RECOVERY_ATTEMPTS = 3
MAX_PACKET_SIZE = 1024  # Maximum reasonable packet size in bytes
PACKET_RECOVERY_TIMEOUT = 2  # Timeout for packet recovery operations

RESPONSE_OVERHEAD: Final = 37 # minimum resposne length received from inverter (technical information)
WRITE_RESPONSE_LENGTH = 76 # Based on documentation for a single write ack