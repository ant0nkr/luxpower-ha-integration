from .lxp_packet_utils import LxpPacketUtils
from .lxp_request_builder import LxpRequestBuilder

from ..const import RESPONSE_OVERHEAD


class LxpResponse:

    def __init__(self, packet: bytes):
        self.packet_error = True
        self.error_type = "No Error"
        self.protocol_number = -1
        self.tcp_function = -1
        self.register = -1
        self.device_function = -1
        self.frame_length = -1
        self.data_length = -1
        self.packet_length_calced = -1
        self.value = bytes()  # Initialize empty value to prevent AttributeError

        if len(packet) < 8:
            self.error_type = "Packet too small"
            return

        if packet[0:2] != LxpRequestBuilder.PREFIX:
            self.error_type = "Missing A11A header"
            return

        self.protocol_number = int.from_bytes(packet[2:4], 'little')
        self.frame_length = int.from_bytes(packet[4:6], 'little')
        self.packet_length_calced = self.frame_length + 6

        if len(packet) < self.packet_length_calced:
            self.error_type = f"Wrong packet length expected={self.packet_length_calced} received={len(packet)}"
            return

        self.tcp_function = packet[7]
        if self.tcp_function == LxpRequestBuilder.TRANSLATED_DATA:
            if len(packet) < RESPONSE_OVERHEAD:
                self.error_type = "Translated data packet too small"
                return

            self.dongle_serial = packet[8:18]
            self.data_length = int.from_bytes(packet[18:20], 'little')

            if not self.__get_data_frame(packet, 20):
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
#        elif self.tcp_function == 193:
#            Found on messages sent from/to dongle to luxpower servers
#            need to understand if needs specific behaviour
        else:
            self.packet_error = True
            # Unknown how the crc is calculated on other packet types
            # the function is called but returning wrong, at this moment cant know if it came with a CRC....
            if not self.__get_data_frame(packet, 8):
               self.error_type = f"Unsupported tcp_function={self.tcp_function} {self.error_type}"
               return
               
            self.error_type = f"Unsupported tcp_function={self.tcp_function}"
            return

        self.packet_error = False

    def __get_data_frame(self, packet, data_frame_start):
        data_frame_len = self.packet_length_calced - 2 - data_frame_start
        self.data_frame = packet[data_frame_start:data_frame_start+data_frame_len]

        self.crc_modbus = int.from_bytes(packet[self.packet_length_calced-2:self.packet_length_calced], 'little')
        calculated_crc = LxpPacketUtils.compute_crc(self.data_frame)
        if calculated_crc != self.crc_modbus:
            self.error_type = f"Wrong CRC received, calculated={calculated_crc:04x} received={self.crc_modbus:04x}"
            self.packet_error = True
            return False
            
        return True

    @property
    def parsed_values(self):
        if len(self.value) % 2 != 0:
            return []
        return [self.value[i] | (self.value[i+1] << 8) for i in range(0, len(self.value), 2)]

    @property
    def parsed_values_dictionary(self):
        if len(self.value) % 2 != 0:
            return {}
        start_register = self.register
        return {
            start_register + i: self.value[2*i] | (self.value[2*i+1] << 8)
            for i in range(len(self.value) // 2)
        }

    @property
    def info(self):
        return (
                ((self.error_type + " ") if self.packet_error else "") +
                f"protocol={self.protocol_number} " + 
                f"frame_len={self.frame_length} " + 
                f"data_len={self.data_length} " + 
                f"packet_len={self.packet_length_calced} " + 
                f"tcp_function={self.tcp_function} " +
                f"function={self.device_function} " +
                f"register={self.register}" + 
                (f"-{self.register + len(self.parsed_values_dictionary) - 1} " if len(self.parsed_values_dictionary) > 0 else " ")
               )

