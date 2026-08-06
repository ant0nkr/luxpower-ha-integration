ALL_PV_STRINGS = frozenset(range(1, 7))

# Hold register 20 (PVInputModel) says which PV inputs are in use, but two mappings
# exist. The generic one is 0:NoPV 1:PV1 2:PV2 3:PV1&2 parallel 4:PV1&2 separate, and
# the 12K Hybrid one is 0:NoPV 1:PV1 2:PV2 3:PV3 4:PV1&2 5:PV1&3 6:PV2&3 7:PV1&2&3.
#
# Only value 3 disagrees between them, so every other value gives a definite answer
# without having to identify the model — and values 5-7 exist only in the 12K
# mapping. Value 3 is deliberately absent here: unknown is safer than wrong, because
# hiding a working string is worse than showing an unused one.
PV_INPUT_MODEL_STRINGS = {
    0: frozenset(),
    1: frozenset({1}),
    2: frozenset({2}),
    4: frozenset({1, 2}),
    5: frozenset({1, 3}),
    6: frozenset({2, 3}),
    7: frozenset({1, 2, 3}),
}


def active_pv_strings(pv_input_model: int | None) -> frozenset[int] | None:
    """Return the PV strings the inverter reports, or None if it cannot be told.

    None means "assume every string", which is the historical behaviour.
    """
    if pv_input_model is None:
        return None
    return PV_INPUT_MODEL_STRINGS.get(pv_input_model)


def sum_pv_registers(registers: dict, string_registers: dict, strings) -> int:
    """Sum one register per PV string, skipping strings that are not present.

    string_registers maps a string number (1-6) to its register.
    """
    return sum(
        registers.get(register, 0)
        for string, register in string_registers.items()
        if string in strings
    )


def decode_model_from_registers(registers: dict) -> str:
    """
    Decode inverter model from 2 HOLD registers (7 and 8).
    Each register holds 2 ASCII chars: HighByte and LowByte.
    """
    chars = []
    for reg in (7, 8):
        value = registers.get(reg, 0)
        chars.append(chr((value >> 8) & 0xFF))  # High byte
        chars.append(chr(value & 0xFF))         # Low byte
    return ''.join(chars).strip('\x00').strip()

def get_bits(value: int, start_bit: int, bit_count: int) -> int:
    """Extract bit field from value."""
    mask = (1 << bit_count) - 1
    return (value >> start_bit) & mask

def set_bits(orig_value: int, start_bit: int, bit_count: int, new_bits: int) -> int:
    """Set bit field in orig_value to new_bits, return new integer value."""
    mask = (1 << bit_count) - 1
    # Clear bits in original value
    cleared = orig_value & ~(mask << start_bit)
    # Set new bits
    return cleared | ((new_bits & mask) << start_bit)

def decode_bitmask_to_string(value, code_map, default_string="OK"):
    """Decodes a 32-bit bitmask into a comma-separated string."""
    if value is None or value == 0:
        return default_string
    active_messages = []
    for bit, message in code_map.items():
        if (value >> bit) & 1:
            active_messages.append(message)
    return ", ".join(active_messages) if active_messages else default_string

def format_firmware_version(hold_registers: dict) -> str | None:
    """Formats the firmware version string from hold registers to match the app's format."""
    try:
        # Check if all required registers are present
        if not all(k in hold_registers for k in [7, 8, 9, 10]):
            return None

        # Unpack the ASCII characters from Hold Registers 7 and 8
        fw_code0 = hold_registers[7] & 0xFF
        fw_code1 = hold_registers[7] >> 8
        fw_code2 = hold_registers[8] & 0xFF
        fw_code3 = hold_registers[8] >> 8
        
        # Unpack the version numbers from Hold Registers 9 and 10
        slave_ver = hold_registers[9] & 0xFF
        com_ver = hold_registers[9] >> 8
        cntl_ver = hold_registers[10] & 0xFF
        
        # Combine the text part (and force to uppercase to match the app)
        fw_string = f"{chr(fw_code0)}{chr(fw_code1)}{chr(fw_code2)}{chr(fw_code3)}".upper()
        
        # Combine the version bytes into a single hex string
        version_string = f"{slave_ver:02X}{com_ver:02X}{cntl_ver:02X}"
        
        return f"{fw_string}-{version_string}"
    except Exception:
        return None

def get_highest_set_bit(value: int) -> int | None:
    """Finds the position of the highest set bit in an integer."""
    if not isinstance(value, int) or value == 0:
        return None
    # Calculate the position of the most significant bit.
    return value.bit_length() - 1