from ..constants.hold_registers import *
from ..utils import get_bits, set_bits

BUTTON_TYPES = [
    # Register 11: H_RESET_SETTINGS
    {
        "name": "Reboot Inverter",
        "register": H_RESET_SETTINGS, # 11
        "register_type": "hold",
        "press": lambda orig: set_bits(orig, 7, 1, 1),
        "icon": "mdi:restart-alert",
        "enabled": True,
        "visible": True,
        "master_only": False,
    },
    {
        "name": "Clear Detected Phases",
        "register": H_SET_COMPOSED_PHASE,
        "register_type": "hold",
        "icon": "mdi:eraser",
        # The press action ignores the original value and always writes 0
        "press": lambda orig: 0,
        "enabled": True,
        "visible": True,
        "master_only": False,
        "device_group": "Grid",
    },
    {
        "name": "Clear Parallel Alarm",
        "register": H_CLEAR_FUNCTION,
        "register_type": "hold",
        "icon": "mdi:alert-remove",
        "press": lambda orig: 1,
        "enabled": True,
        "visible": True,
        "master_only": True,
    },
    {
        "name": "Reset G100 Lockout",
        "register": H_RESET_RECORD,
        "register_type": "hold",
        "icon": "mdi:lock-reset",
        "press": lambda orig: set_bits(orig, 0, 1, 1),
        "enabled": True,
        "visible": True,
        "master_only": True,
        "device_group": "Grid",
    },

]