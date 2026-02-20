"""Parser for battery information blocks from register range 5000."""
import logging

from .lxp_response import LxpResponse
from ..constants.battery_registers import B_SERIAL_START, B_SERIAL_LEN
from ..const import BATTERY_INFO_START_REGISTER

_LOGGER = logging.getLogger(__name__)


class LxpBatteries:
    """Parses battery data from a response covering register range 5000+.

    The inverter returns up to 4 battery blocks per response, each 30 registers wide.
    Batteries are identified by their serial number embedded in each block.
    """

    def __init__(self, response: LxpResponse):
        self.response = response

    def parse_bat_info_block(self, block: int) -> dict:
        """Parse a single 30-register battery block.

        Args:
            block: Block index (0-3), each representing one battery.

        Returns:
            Dictionary with battery data keyed by register offset, plus 'serial'.
        """
        if self.response.register != BATTERY_INFO_START_REGISTER:
            return {}

        start_reg = BATTERY_INFO_START_REGISTER + (block * 30)
        start = (start_reg - BATTERY_INFO_START_REGISTER) * 2
        data = {}
        parsed = self.response.parsed_values_dictionary

        # Extract serial number (zero-terminated UTF-8 string)
        serial_bytes = self.response.value[start + (B_SERIAL_START * 2):start + (B_SERIAL_START * 2) + B_SERIAL_LEN + 1]
        zero_index = serial_bytes.find(b'\x00')
        data['serial'] = (serial_bytes if zero_index == -1 else serial_bytes[:zero_index]).decode("utf-8")

        # Remove serial registers from parsed dict (they're not numeric values)
        for n in range(B_SERIAL_START, 27):
            parsed.pop(start_reg + n, None)

        # Keep remaining block registers as numeric data
        for reg in range(start_reg, start_reg + 30):
            if reg in parsed:
                data[reg - start_reg] = parsed[reg]

        return data

    def get_battery_info(self) -> dict:
        """Parse all battery blocks and return data keyed by serial number.

        Returns:
            Dictionary mapping battery serial -> battery data dict.
        """
        result = {}
        for bat_block in range(4):
            bat_data = self.parse_bat_info_block(bat_block)
            serial = bat_data.get('serial', '')
            if serial:
                result[serial] = bat_data

        return result
