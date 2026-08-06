"""Inverter model discovery via Modbus connection."""
import asyncio
import logging

from .lxp_request_builder import LxpRequestBuilder
from .lxp_response import LxpResponse
from ..utils import decode_model_from_registers

_LOGGER = logging.getLogger(__name__)

# Discovery-specific constants
MODEL_REGISTER_START = 7
MODEL_REGISTER_COUNT = 2
HOLD_REGISTER_READ_FUNCTION = 3
DISCOVERY_BUFFER_SIZE = 512
DISCOVERY_CONNECT_TIMEOUT = 10
DISCOVERY_READ_TIMEOUT = 5


class InverterDiscoveryError(Exception):
    """Base error for inverter discovery failures."""


class CannotConnect(InverterDiscoveryError):
    """The dongle could not be reached."""


class InvalidResponse(InverterDiscoveryError):
    """The dongle answered, but not with a usable model."""


async def get_inverter_model_from_device(host, port, dongle_serial, inverter_serial) -> str:
    """Connect to the inverter and read the model.

    Raises CannotConnect if the dongle is unreachable and InvalidResponse if it
    answers with something unusable, so the config flow can tell the user which of
    the two happened instead of one catch-all message.
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=DISCOVERY_CONNECT_TIMEOUT
        )
    except (asyncio.TimeoutError, TimeoutError) as err:
        raise CannotConnect(f"Timed out connecting to {host}:{port}") from err
    except OSError as err:
        raise CannotConnect(f"Could not connect to {host}:{port}: {err}") from err

    try:
        req = LxpRequestBuilder.prepare_packet_for_read(
            dongle_serial.encode(), inverter_serial.encode(),
            MODEL_REGISTER_START, MODEL_REGISTER_COUNT, HOLD_REGISTER_READ_FUNCTION
        )
        writer.write(req)
        await writer.drain()
        response_buf = await asyncio.wait_for(
            reader.read(DISCOVERY_BUFFER_SIZE), timeout=DISCOVERY_READ_TIMEOUT
        )
    except (asyncio.TimeoutError, TimeoutError) as err:
        raise CannotConnect(f"{host}:{port} did not answer the model request") from err
    except OSError as err:
        raise CannotConnect(f"Connection to {host}:{port} failed: {err}") from err
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError as err:
            _LOGGER.debug("Error closing discovery connection: %s", err)

    if not response_buf:
        raise InvalidResponse("The dongle closed the connection without answering")

    response = LxpResponse(response_buf)
    if response.packet_error:
        raise InvalidResponse(f"Malformed response: {response.error_type}")

    model = decode_model_from_registers(response.parsed_values_dictionary)
    if not model:
        raise InvalidResponse("Response did not contain a model identifier")

    return model
