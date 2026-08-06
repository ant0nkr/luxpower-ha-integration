from typing import Final
from homeassistant.const import Platform

DOMAIN = "lxp_modbus"

PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
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
CONF_BATTERY_ENTITIES = "battery_entities"

INTEGRATION_TITLE = "LuxPower Inverter (Modbus)"


DEFAULT_POLL_INTERVAL = 60  # seconds
DEFAULT_ENTITY_PREFIX = ""
DEFAULT_RATED_POWER = 5000
DEFAULT_READ_ONLY = False
DEFAULT_PORT = 8000
DEFAULT_REGISTER_BLOCK_SIZE = 125
DEFAULT_CONNECTION_RETRIES = 3
DEFAULT_ENABLE_DEVICE_GROUPING = True
DEFAULT_BATTERY_ENTITIES = "none"  # User must explicitly enable; not all batteries provide data

# Legacy firmware may only support smaller block sizes
LEGACY_REGISTER_BLOCK_SIZE = 40
TOTAL_REGISTERS = 750 # Total number of registers available

# Packet recovery constants
MAX_PACKET_RECOVERY_ATTEMPTS = 3
MAX_PACKET_SIZE = 1024  # Maximum reasonable packet size in bytes
PACKET_RECOVERY_TIMEOUT = 2  # Timeout for packet recovery operations

RESPONSE_OVERHEAD: Final = 37  # Minimum response length from inverter (protocol overhead)
WRITE_RESPONSE_LENGTH = 76  # Based on documentation for a single write ack

BATTERY_INFO_START_REGISTER = 5000  # Start of battery info register range

# Communication timeouts (seconds)
READ_TIMEOUT = 3
WRITE_READ_TIMEOUT = 5  # Timeout waiting for a write acknowledgement
WRITE_RETRY_DELAY = 1
# Connection retries happen inside a single poll, so the total backoff has to stay
# well below the poll interval. The retry sleep is taken outside the shared lock so
# it never blocks a user-initiated write.
INITIAL_RETRY_DELAY = 2
MAX_RETRY_DELAY = 10
RETRY_BACKOFF_MULTIPLIER = 1.5

# Number of consecutive poll failures tolerated before entities are marked
# unavailable. Small window so a flaky dongle does not cause UI flapping, while
# stale values are never presented as live for long.
MAX_CACHED_DATA_FAILURES = 2

# Serial number validation
SERIAL_LENGTH = 10
