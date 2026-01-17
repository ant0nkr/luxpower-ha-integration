from .lxp_response import LxpResponse
from ..constants.battery_registers import B_SERIAL_START, B_SERIAL_LEN
from ..const import BATTERY_INFO_START_REGISTER

class LxpBatteries:
   
   def __init__(self, response: LxpResponse):
      self.response = response
      
   def parse_bat_info_block(self, block):
       if self.response.register != BATTERY_INFO_START_REGISTER:
           return {}
        
       start_reg = BATTERY_INFO_START_REGISTER + (block * 30)        
       start = (start_reg - BATTERY_INFO_START_REGISTER) * 2
       data = {}
       dict = self.response.parsed_values_dictionary
       # Missing data that appear on web interface
       # - identification of cells with max/min voltage/temp

       # + 0 - all zero
       # + 1 - all 8192 (maybe bitmask)
       # + 2 - all 1 
       # + 3 - battery capacity
       # + 4 - all 565
       # + 5 - max charge current
       # + 6 - max discharge current
       # + 7 - variable values most of times 472, 3850, 3852 (maybe bitmask)
       # + 8 - voltage
       # + 9 - current
       # + 10 - soc_soh
       # + 11 - cycles
       # + 12 - max_temp
       # + 13 - min_temp
       # + 14 - max_cell_v
       # + 15 - min_cell_v
       # + 16 - cells with min/max temp
       # + 17 - cells with min/max voltage
       # + 18 - firmware version
       
       # received some messages with zeroed serial, then consider that it can be a zero terminated string also       
       serial_bytes = self.response.value[start+(B_SERIAL_START*2):(start+(B_SERIAL_START*2)+B_SERIAL_LEN+1)]
       zero_index = serial_bytes.find(b'\x00')
       data['serial'] = (serial_bytes if zero_index == -1 else serial_bytes[:zero_index]).decode("utf-8")
       for n in range(B_SERIAL_START, 27):
          dict.pop(start_reg + n)

       # maybe this remaining is part of battery serial string ?
       # + 27 - zero
       # + 28 - zero
       # + 29 - zero

       # keep other block registers until we decode all data    
       for reg in range(start_reg, start_reg+30):
          if reg in dict:
              data[reg - start_reg] = dict[reg]

       return data

   def get_battery_info(self):
       dict = {}
       for bat_block in range(0,4):
           bat_dict = self.parse_bat_info_block(bat_block)
           # TODO need to test better to see how they will came and ignore empty data
           # for now only found empty zeroed serial
           if len(bat_dict.get('serial','')):
               dict[bat_dict['serial']] = bat_dict

       return dict
        
      
