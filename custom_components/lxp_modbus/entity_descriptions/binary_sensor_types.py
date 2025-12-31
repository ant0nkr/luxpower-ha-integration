from ..constants.input_registers import *
from ..utils import get_bits

BINARY_SENSOR_TYPES = [
    {
        "name": "BMS Charge Allowed",
        "register": I_BMS_BAT_STATUS_INV,
        "register_type": "input",
        "extract": lambda value: get_bits(value, 0, 1) != 0,
        "icon": "mdi:battery",
        "enabled": True,
        "visible": True,
        "device_group": "Battery",
        "master_only": True,
    },
    {
        "name": "BMS Discharge Allowed",
        "register": I_BMS_BAT_STATUS_INV,
        "register_type": "input",
        "extract": lambda value: get_bits(value, 1, 1) != 0,
        "icon": "mdi:battery",
        "enabled": True,
        "visible": True,
        "device_group": "Battery",
        "master_only": True,
    },

]
