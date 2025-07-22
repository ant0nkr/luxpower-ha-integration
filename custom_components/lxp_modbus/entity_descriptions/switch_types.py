from ..constants.hold_registers import *
from ..utils import get_bits, set_bits

from ..utils import get_bits, set_bits

SWITCH_TYPES = [
    # Register 21: H_FUNCTION_ENABLE_1
    {
        "name": "Off-Grid Mode",
        "register": H_FUNCTION_ENABLE_1, # 21
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 0, 1),
        "compose": lambda orig, value: set_bits(orig, 0, 1, value),
        "icon": "mdi:power-plug-off",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "Over-Frequency Load Reduction",
        "register": H_FUNCTION_ENABLE_1, # 21
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 1, 1),
        "compose": lambda orig, value: set_bits(orig, 1, 1, value),
        "icon": "mdi:chart-bell-curve",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "DRMS",
        "register": H_FUNCTION_ENABLE_1, # 21
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 2, 1),
        "compose": lambda orig, value: set_bits(orig, 2, 1, value),
        "icon": "mdi:grid",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "AC Charging",
        "register": H_FUNCTION_ENABLE_1, # 21
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 7, 1),
        "compose": lambda orig, value: set_bits(orig, 7, 1, value),
        "icon": "mdi:battery-charging",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "Forced Discharge",
        "register": H_FUNCTION_ENABLE_1, # 21
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 10, 1),
        "compose": lambda orig, value: set_bits(orig, 10, 1, value),
        "icon": "mdi:battery-arrow-down",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    # Register 22: H_FUNCTION_ENABLE_2_AND_PV_START_VOLT
    {
        "name": "Feed-In Grid",
        "register": H_FUNCTION_ENABLE_2_AND_PV_START_VOLT, # 22
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 15, 1),
        "compose": lambda orig, value: set_bits(orig, 15, 1, value),
        "icon": "mdi:transmission-tower-export",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    # Register 110: H_FUNCTION_ENABLE_3
    {
        "name": "Fast Zero Export",
        "register": H_FUNCTION_ENABLE_3, # 110
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 1, 1),
        "compose": lambda orig, value: set_bits(orig, 1, 1, value),
        "icon": "mdi:meter-electric-outline",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "Micro-Grid",
        "register": H_FUNCTION_ENABLE_3, # 110
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 2, 1),
        "compose": lambda orig, value: set_bits(orig, 2, 1, value),
        "icon": "mdi:grid",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "Buzzer",
        "register": H_FUNCTION_ENABLE_3, # 110
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 7, 1),
        "compose": lambda orig, value: set_bits(orig, 7, 1, value),
        "icon": "mdi:bell",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "Green Mode",
        "register": H_FUNCTION_ENABLE_3, # 110
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 14, 1),
        "compose": lambda orig, value: set_bits(orig, 14, 1, value),
        "icon": "mdi:leaf",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "Eco Mode",
        "register": H_FUNCTION_ENABLE_3, # 110
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 15, 1),
        "compose": lambda orig, value: set_bits(orig, 15, 1, value),
        "icon": "mdi:sprout",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    # Register 120: H_SYSTEM_ENABLE_2
    {
        "name": "Half Hour AC Charge Start",
        "register": H_SYSTEM_ENABLE_2,   # 120
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 0, 1),
        "compose": lambda orig, value: set_bits(orig, 0, 1, value),
        "icon": "mdi:power",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    # Register 179: H_FUNCTION_ENABLE_4
    {
        "name": "Volt-Watt Function",
        "register": H_FUNCTION_ENABLE_4, # 179
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 4, 1),
        "compose": lambda orig, value: set_bits(orig, 4, 1, value),
        "icon": "mdi:chart-line",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "Grid Peak Shaving",
        "register": H_FUNCTION_ENABLE_4, # 179
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 7, 1),
        "compose": lambda orig, value: set_bits(orig, 7, 1, value),
        "icon": "mdi:chart-gantt",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "AC Coupling",
        "register": H_FUNCTION_ENABLE_4, # 179
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 11, 1),
        "compose": lambda orig, value: set_bits(orig, 11, 1, value),
        "icon": "mdi:power-plug",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "PV Arc Detection",
        "register": H_FUNCTION_ENABLE_4, # 179
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 12, 1),
        "compose": lambda orig, value: set_bits(orig, 12, 1, value),
        "icon": "mdi:flash-alert",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "On-Grid Always On",
        "register": H_FUNCTION_ENABLE_4, # 179
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 15, 1),
        "compose": lambda orig, value: set_bits(orig, 15, 1, value),
        "icon": "mdi:power-cycle",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    # Register 232: H_GRID_PEAK_SHAVING_POWER_1_AND_FUNC_EN
    {
        "name": "Quick Charge Start",
        "register": H_GRID_PEAK_SHAVING_POWER_1_AND_FUNC_EN, # 232
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 0, 1),
        "compose": lambda orig, value: set_bits(orig, 0, 1, value),
        "icon": "mdi:battery-plus",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "Battery Backup",
        "register": H_GRID_PEAK_SHAVING_POWER_1_AND_FUNC_EN, # 232
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 1, 1),
        "compose": lambda orig, value: set_bits(orig, 1, 1, value),
        "icon": "mdi:battery-heart-variant",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "Battery Maintenance",
        "register": H_GRID_PEAK_SHAVING_POWER_1_AND_FUNC_EN, # 232
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 2, 1),
        "compose": lambda orig, value: set_bits(orig, 2, 1, value),
        "icon": "mdi:wrench",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "WattNode CT1 Direction",
        "register": H_WATTNODE_CT_DIRECTIONS,
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 0, 1),
        "compose": lambda orig, value: set_bits(orig, 0, 1, value),
        "icon": "mdi:arrow-left-right",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "WattNode CT2 Direction",
        "register": H_WATTNODE_CT_DIRECTIONS,
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 1, 1),
        "compose": lambda orig, value: set_bits(orig, 1, 1, value),
        "icon": "mdi:arrow-left-right",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
    {
        "name": "WattNode CT3 Direction",
        "register": H_WATTNODE_CT_DIRECTIONS,
        "register_type": "hold",
        "extract": lambda reg: get_bits(reg, 2, 1),
        "compose": lambda orig, value: set_bits(orig, 2, 1, value),
        "icon": "mdi:arrow-left-right",
        "device_class": "switch",
        "enabled": True,
        "visible": True,
    },
]