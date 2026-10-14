"""A stand-in dongle that speaks real A1 1A frames, for transport tests."""

import asyncio

from custom_components.lxp_modbus.classes.lxp_packet_utils import LxpPacketUtils
from custom_components.lxp_modbus.classes.lxp_request_builder import LxpRequestBuilder

# A framed packet whose content does not matter, for tests that patch LxpResponse.
DUMMY_FRAME = LxpRequestBuilder.PREFIX + b"\x02\x00" + (70).to_bytes(2, "little") + b"\x00" * 70


def build_frame(dongle: bytes, serial: bytes, function: int, register: int,
                values=None, write_value=None, exception=None, protocol: int = 2) -> bytes:
    """Build an inverter reply as the dongle relays it."""
    data = bytes([1, function]) + serial + register.to_bytes(2, "little")
    if exception is not None:
        data += bytes([exception])
    elif write_value is not None:
        data += write_value.to_bytes(2, "little")
    else:
        payload = b"".join(v.to_bytes(2, "little") for v in values)
        data += bytes([len(payload)]) + payload

    crc = LxpPacketUtils.compute_crc(data).to_bytes(2, "little")
    body = bytes([1, LxpRequestBuilder.TRANSLATED_DATA]) + dongle + (len(data) + 2).to_bytes(2, "little")
    frame_length = len(body) + len(data) + len(crc)
    return (LxpRequestBuilder.PREFIX + protocol.to_bytes(2, "little")
            + frame_length.to_bytes(2, "little") + body + data + crc)


class FakeDongle:
    """Answers each request with a matching frame; extra frames can be queued.

    ``value_of(function, register)`` supplies register values. ``chunk`` limits
    how many bytes one read() returns, to exercise frames split across reads.
    """

    def __init__(self, dongle=b"BA0000000A", serial=b"0000000001", value_of=None, chunk=None):
        self.dongle = dongle
        self.serial = serial
        self.value_of = value_of or (lambda function, register: register)
        self.chunk = chunk
        self.requests = []
        self.exceptions = {}  # (function, register) -> exception code
        self.silent_functions = set()  # requests that never get an answer
        self._pending = bytearray()
        self._data = asyncio.Event()

    def push(self, frame: bytes) -> None:
        """Queue bytes the dongle sends without being asked."""
        self._pending += frame
        self._data.set()

    # StreamWriter side
    def write(self, req: bytes) -> None:
        function = req[21]
        register = int.from_bytes(req[32:34], "little")
        count_or_value = int.from_bytes(req[34:36], "little")
        self.requests.append((function, register, count_or_value))

        if function in self.silent_functions:
            return
        if (function, register) in self.exceptions:
            self.push(build_frame(self.dongle, self.serial, function | 0x80, register,
                                  exception=self.exceptions[(function, register)]))
        elif function == LxpRequestBuilder.WRITE_SINGLE:
            self.push(build_frame(self.dongle, self.serial, function, register,
                                  write_value=count_or_value))
        else:
            values = [self.value_of(function, r) & 0xFFFF
                      for r in range(register, register + count_or_value)]
            self.push(build_frame(self.dongle, self.serial, function, register, values=values))

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        return None

    async def wait_closed(self) -> None:
        return None

    # StreamReader side
    async def read(self, n: int = -1) -> bytes:
        while not self._pending:
            self._data.clear()
            await self._data.wait()
        size = len(self._pending) if n < 0 else n
        if self.chunk:
            size = min(size, self.chunk)
        out = bytes(self._pending[:size])
        del self._pending[:size]
        return out
