from .lxp_packet_utils import LxpPacketUtils

class LxpResponse:
    def __init__(self, packet: bytes):
        self.packet_error = True

        if len(packet) < 37:
            return

        if packet[0:2] != bytes([0xA1, 0x1A]):
            return

        self.protocol_number = int.from_bytes(packet[2:4], 'little')
        self.frame_length = int.from_bytes(packet[4:6], 'little')
        packet_length_calced = self.frame_length + 6

        if len(packet) < packet_length_calced:
            return

        self.tcp_function = packet[7]
        self.dongle_serial = packet[8:18]
        self.data_length = int.from_bytes(packet[18:20], 'little')

        data_frame_start = 20
        data_frame_len = packet_length_calced - 2 - data_frame_start
        self.data_frame = packet[data_frame_start:data_frame_start+data_frame_len]

        self.crc_modbus = int.from_bytes(packet[packet_length_calced-2:packet_length_calced], 'little')
        if LxpPacketUtils.compute_crc(self.data_frame) != self.crc_modbus:
            return

        self.address_action = self.data_frame[0]
        self.device_function = self.data_frame[1]
        self.serial_number = self.data_frame[2:12]
        self.register = int.from_bytes(self.data_frame[12:14], 'little')

        self.value_length_byte_present = (
            self.protocol_number in [2, 5] and self.device_function != 6
        )
        if self.value_length_byte_present:
            self.value_length = self.data_frame[14]
            self.value = self.data_frame[15:15+self.value_length]
        else:
            self.value_length = 2
            self.value = self.data_frame[14:16]

        self.packet_error = False

    @property
    def parsed_values(self):
        if self.packet_error or (len(self.value) % 2 != 0):
            return []
        return [self.value[i] | (self.value[i+1] << 8) for i in range(0, len(self.value), 2)]

    @property
    def parsed_values_dictionary(self):
        if self.packet_error or len(self.value) % 2 != 0:
            return {}
        start_register = self.register
        return {
            start_register + i: self.value[2*i] | (self.value[2*i+1] << 8)
            for i in range(len(self.value) // 2)
        }
