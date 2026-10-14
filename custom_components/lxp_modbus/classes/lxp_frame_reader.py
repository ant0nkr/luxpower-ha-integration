"""Split the dongle byte stream into whole A1 1A frames."""
import asyncio
import logging

from .lxp_request_builder import LxpRequestBuilder
from ..const import MAX_PACKET_SIZE

_LOGGER = logging.getLogger(__name__)

HEADER_LENGTH = 6  # prefix(2) + protocol(2) + frame length(2)
MIN_FRAME_LENGTH = 8
READ_CHUNK_SIZE = MAX_PACKET_SIZE


class LxpFrameReader:
    """Reads one complete dongle frame at a time.

    The dongle does not only answer our requests: it also pushes frames of its
    own (it relays its cloud polling to local clients) and a single TCP read can
    return part of a frame or several frames at once. Treating "one read" as
    "one answer" made every reply land one request late (#167, #169). Framing
    on the A1 1A header and its length field keeps the stream aligned, so the
    caller can look at each frame and drop the ones that are not its answer.
    """

    def __init__(self, reader: asyncio.StreamReader):
        self._reader = reader
        self._buf = bytearray()
        self.discarded_bytes = 0

    @property
    def reader(self) -> asyncio.StreamReader:
        return self._reader

    async def async_read_frame(self, timeout: float) -> bytes | None:
        """Return the next whole frame, or None if the connection closed.

        Raises asyncio.TimeoutError if no whole frame arrives within ``timeout``.
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout

        while True:
            frame = self._extract_frame()
            if frame is not None:
                return frame

            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError("No complete frame received")

            chunk = await asyncio.wait_for(self._reader.read(READ_CHUNK_SIZE), timeout=remaining)
            if not chunk:
                if self._buf:
                    _LOGGER.debug("Connection closed with %d bytes of an incomplete frame: %s",
                                  len(self._buf), self._buf.hex())
                return None
            self._buf += chunk

    def _discard(self, count: int) -> None:
        if count <= 0:
            return
        _LOGGER.debug("Discarding %d bytes that are not part of a frame: %s",
                      count, self._buf[:count].hex())
        self.discarded_bytes += count
        del self._buf[:count]

    def _extract_frame(self) -> bytes | None:
        """Pop a whole frame off the buffer if one is available."""
        prefix = LxpRequestBuilder.PREFIX

        while True:
            start = self._buf.find(prefix)
            if start < 0:
                # Keep a trailing first prefix byte: the header may be split across reads.
                keep = 1 if self._buf[-1:] == prefix[:1] else 0
                self._discard(len(self._buf) - keep)
                return None

            self._discard(start)
            if len(self._buf) < HEADER_LENGTH:
                return None

            frame_length = int.from_bytes(self._buf[4:6], "little") + HEADER_LENGTH
            if not MIN_FRAME_LENGTH <= frame_length <= MAX_PACKET_SIZE:
                # Not a real header, just the prefix bytes appearing in data.
                self._discard(len(prefix))
                continue

            if len(self._buf) < frame_length:
                return None

            frame = bytes(self._buf[:frame_length])
            del self._buf[:frame_length]
            return frame
