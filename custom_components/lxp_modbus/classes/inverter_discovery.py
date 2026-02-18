"""Inverter model discovery via Modbus connection."""
import asyncio

from .lxp_request_builder import LxpRequestBuilder
from .lxp_response import LxpResponse
from ..utils import decode_model_from_registers

# Discovery-specific constants
MODEL_REGISTER_START = 7
MODEL_REGISTER_COUNT = 2
HOLD_REGISTER_READ_FUNCTION = 3
DISCOVERY_BUFFER_SIZE = 512


async def get_inverter_model_from_device(host, port, dongle_serial, inverter_serial):
    """Attempt to connect to the inverter and read the model."""
    try:
        reader, writer = await asyncio.open_connection(host, port)
        req = LxpRequestBuilder.prepare_packet_for_read(
            dongle_serial.encode(), inverter_serial.encode(),
            MODEL_REGISTER_START, MODEL_REGISTER_COUNT, HOLD_REGISTER_READ_FUNCTION
        )
        writer.write(req)
        await writer.drain()
        response_buf = await reader.read(DISCOVERY_BUFFER_SIZE)
        writer.close()
        await writer.wait_closed()
        if not response_buf:
            return None
        response = LxpResponse(response_buf)
        if response.packet_error:
            return None
        model = decode_model_from_registers(response.parsed_values_dictionary)
        return model
    except Exception:
        return None
