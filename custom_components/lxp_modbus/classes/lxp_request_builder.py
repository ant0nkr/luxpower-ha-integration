from .lxp_packet_utils import LxpPacketUtils

class LxpRequestBuilder:
    PREFIX = bytes([0xA1, 0x1A])
    PROTOCOL = 1
    FRAME_LENGTH = 32
    DATA_LENGTH = 18
    TRANSLATED_DATA = 194
    ACTION_WRITE = 0
    WRITE_SINGLE = 6

    @staticmethod
    def prepare_packet_for_read(
        dongle_serial: bytes, serial_number: bytes,
        start_register: int, register_count: int = 1, function_code: int = 3
    ) -> bytes:
        if len(dongle_serial) != 10:
            raise ValueError("dongle_serial must be 10 bytes")
        if len(serial_number) != 10:
            raise ValueError("serial_number must be 10 bytes")

        buf = bytearray()
        buf += LxpRequestBuilder.PREFIX
        buf += LxpRequestBuilder.PROTOCOL.to_bytes(2, 'little')
        buf += LxpRequestBuilder.FRAME_LENGTH.to_bytes(2, 'little')
        buf += (1).to_bytes(1, 'little')
        buf += LxpRequestBuilder.TRANSLATED_DATA.to_bytes(1, 'little')
        buf += dongle_serial
        buf += LxpRequestBuilder.DATA_LENGTH.to_bytes(2, 'little')

        buf += LxpRequestBuilder.ACTION_WRITE.to_bytes(1, 'little')
        buf += function_code.to_bytes(1, 'little')
        buf += serial_number
        buf += start_register.to_bytes(2, 'little')
        buf += register_count.to_bytes(2, 'little')

        data_frame = bytes(buf[20:36])  # always 16 bytes
        crc = LxpPacketUtils.compute_crc(data_frame)
        buf += crc.to_bytes(2, 'little')
        return bytes(buf)

    @staticmethod
    def prepare_packet_for_write(
        dongle_serial: bytes, serial_number: bytes, register: int, value: int
    ) -> bytes:
        if len(dongle_serial) != 10:
            raise ValueError("dongle_serial must be 10 bytes")
        if len(serial_number) != 10:
            raise ValueError("serial_number must be 10 bytes")

        buf = bytearray()
        buf += LxpRequestBuilder.PREFIX
        buf += LxpRequestBuilder.PROTOCOL.to_bytes(2, 'little')
        buf += LxpRequestBuilder.FRAME_LENGTH.to_bytes(2, 'little')
        buf += (1).to_bytes(1, 'little')
        buf += LxpRequestBuilder.TRANSLATED_DATA.to_bytes(1, 'little')
        buf += dongle_serial
        buf += LxpRequestBuilder.DATA_LENGTH.to_bytes(2, 'little')

        buf += LxpRequestBuilder.ACTION_WRITE.to_bytes(1, 'little')
        buf += LxpRequestBuilder.WRITE_SINGLE.to_bytes(1, 'little')
        buf += serial_number
        buf += register.to_bytes(2, 'little')
        buf += value.to_bytes(2, 'little')

        data_frame = bytes(buf[20:36])  # always 16 bytes
        crc = LxpPacketUtils.compute_crc(data_frame)
        buf += crc.to_bytes(2, 'little')
        return bytes(buf)
