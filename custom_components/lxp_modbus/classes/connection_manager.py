"""TCP connection management for Modbus communication."""
import asyncio
import logging
from contextlib import suppress

from .lxp_response import LxpResponse

_LOGGER = logging.getLogger(__name__)

# Connection constants
CONNECTION_TIMEOUT = 10
CLOSE_TIMEOUT = 5
INITIAL_DATA_READ_SIZE = 300
INITIAL_DATA_TIMEOUT = 1


class ModbusConnectionManager:
    """Manages TCP connection lifecycle for Modbus communication."""

    def __init__(self, host: str, port: int, connection_retries: int,
                 skip_initial_data: bool = True):
        """Initialize the connection manager."""
        self._host = host
        self._port = port
        self._connection_retries = connection_retries
        self._skip_initial_data = skip_initial_data

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def connection_retries(self) -> int:
        return self._connection_retries

    async def async_connect(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Establish a TCP connection with timeout."""
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self._host, self._port),
            timeout=CONNECTION_TIMEOUT
        )
        return reader, writer

    async def async_close(self, writer: asyncio.StreamWriter) -> None:
        """Close connection gracefully with timeout protection."""
        if not writer:
            return
        try:
            writer.close()
            await asyncio.wait_for(writer.wait_closed(), timeout=CLOSE_TIMEOUT)
        except (asyncio.TimeoutError, ConnectionError) as e:
            _LOGGER.warning("Error closing connection: %s", e)

    async def async_discard_initial_data(self, reader: asyncio.StreamReader) -> None:
        """Discard any initial data sent by dongle after connection."""
        if not self._skip_initial_data:
            return
        with suppress(asyncio.TimeoutError):
            ignored = await asyncio.wait_for(
                reader.read(INITIAL_DATA_READ_SIZE),
                timeout=INITIAL_DATA_TIMEOUT
            )
            if ignored:
                response = LxpResponse(ignored)
                _LOGGER.debug("ignored start data from dongle response=%s %s", response.info, ignored.hex())
