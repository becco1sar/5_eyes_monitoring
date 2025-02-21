#!/usr/bin/env python3

from base_monitoring import *
# ------------------------------------------------------------------------------------------------------------
# DEFINITIONS AND INITIALISATIONS


# ------------------------------------------------------------------------------------------------------------
# MAIN
#
async def main(reader, writer):
   global sleep_time
   global flash_wait_time
   global status 
   global ser
   global last_updated
   global data
   global no_of_receiver_cards
   global receiver_card_found
   global logger
   module_status_info = {}
   exit_code = UNKNOWN
   output = list()
   exit_codes = list()
   my_logger = methods.get_logger(LOGGER_NAME,LOG_FILE,FORMATTER,LOGGER_SCHEDULE,LOGGER_INTERVAL,LOGGER_BACKUPS) # Set up the logging
   my_logger.info("*********************************************************************************************************************************************")
   my_logger.info("5Eyes - Starting Display Status Checks")
   config = loadConfig(LOGGER_NAME) # Load the configuration information
   my_logger.info("Version: {}, Baudrate: {}, Sleep Time: {}, Flash Timeout: {}".format(config["version"],config["baudrate"],config["sleepTime"],config["flashWaitTime"]))
   last_updated = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
   sleep_time = float(config["sleepTime"])
   flash_wait_time = float(config["flashWaitTime"])
   total_receiver_cards = float(config["receiver_cards"])
   data = read_data(STATUS_FILE,LOGGER_NAME)
   status = {} # Initialise variable to store status data\
   modules_ok = True # assume all modules are ok to start off
   ser = methods.setupSerialPort(config["baudrate"],LOGGER_NAME) # Initialise serial port
   device_found, valid_ports = search_devices(ser, sleep_time, status)
   start_time = time.time()
   #Validate device found on player
   if (device_found == 0):
      message = "NO DEVICE - make sure a valid controller is connected, that the correct baudrate is defined in config.json and ensure the NOVA LCT is not running on the host system \nThis can also mean that you don't run the tool as administrator"
      exit_code = CRITICAL
      my_logger.info ("EXIT CODE: {}, {}".format(exit_code, message))
      end_time = time.time()
      await icinga_output(message, exit_code, reader, writer)
   
   #looping through each sender card found
   i=0
   for serial_port in sorted(valid_ports):
      my_logger.info("*******************    DEVICE {}   *******************".format(i))
      my_logger.info("Connecting to device on {}".format(serial_port))
      ser.port = serial_port      
      try: 
         if ser.isOpen() == False:
            ser.open()
         ser.flushInput() #flush input buffer, discarding all its contents
         ser.flushOutput() #flush output buffer, aborting current output and discard all that is in buffer
         my_logger.info("Opened device on port: " + ser.name) # remove at production
      except SerialException as e:
         message = f"Error opening serial port: {ser.name} - {str(e)}"
         exit_code = CRITICAL
         my_logger.error(message)
         await icinga_output(message, exit_code, reader, writer)         
      # -------------------------------------
      # RETRIEVE PARAMETERS FROM SENDER CARDS
      # -------------------------------------
      receiver_card_found = True
      no_of_receiver_cards = 0
      status[serial_port]["receiverCard"]={}
      display_on = True
      voltage_per_receiving_card = {}
      while receiver_card_found != False: 
         my_logger.info("=============================================================================================================================================")
         my_logger.info ("Connecting to receiver number: {}".format(no_of_receiver_cards+1))    
         try:  
             if not get_receiver_connected(ser.port):
               break
             temp_valid, temperature, voltage_valid, voltage, monitoring_card = get_receiver_temp_voltage(no_of_receiver_cards)
             _status = 1
             if voltage_valid:
                 _status = 0;                
             voltage_per_receiving_card[f"{no_of_receiver_cards + 1}"] = {"voltage":voltage, "status":_status}
             no_of_receiver_cards += 1            
         except Exception as e:
            pass
      exit_code = GOOD
      for k in voltage_per_receiving_card.keys():
         if voltage_per_receiving_card[k]["status"] == 0:
            exit_code = CRITICAL
            break      
      message = [f"receiver card {k} VOLTAGE {voltage_per_receiving_card[k]['voltage']}" for k in voltage_per_receiving_card.keys()]
      print(serial_port)
      [print(msg) for msg in message]
      exit_codes.append(exit_code)
      output.append(message)
      ser.close() #closing 
     
   my_logger.info ("EXIT CODE: {}, {}".format(exit_code, message))      
   await icinga_output(output, exit_codes, reader, writer)
          
# ------------------------------------------------------------------------------------------------------------
# FUNCTION DEFINITIONS

def get_receiver_connected(port):
   global data
   global logger
# ---------------------------------------------------------------------------------------
# CHECK CONNECTION TO RECEIVER CARD
# ---------------------------------------------------------------------------------------   
   logger = logging.getLogger(LOGGER_NAME)
   global receiver_card_found
   global no_of_receiver_cards
   check_receiver_model [8] = no_of_receiver_cards
   check_receiver_model_send = methods.checksum (check_receiver_model)
   ser.write (check_receiver_model_send)
   time.sleep (sleep_time)
   inWaiting = ser.inWaiting()
   if inWaiting>0:
      response = ser.read(size=inWaiting)
      rx_data = list(response)
      logger.debug("Received data: "+' '.join('{:02X}'.format(a) for a in rx_data))
      if check_response(rx_data):
         receiver_card_found = True
      else:
         receiver_card_found = False          
   else:
      logger.warning("No data available at the input buffer")
      receiver_card_found = False
   return receiver_card_found
#Get receiving card gets one parameter (receiving_card) that represent the physical receiving card found per sender card
def get_receiver_temp_voltage(no_of_receiver_cards):
# ---------------------------------------------------------------------------------------
# CHECK TEMPERATURE, VOLTAGE & MONITORING
# Retrieve data for receiver cards
# Maximum resolution: 512 x 384 px @60Hz
# AC/DC: MEGMEET MCP260WL-4.5 / Output 4.5VDC 40A (4.2~5.0V)
# A5s PLUS
# Input voltage: 3.8 to 5.5 V
# Rated current: 0.6A
# Rated power consumption: 3.0 W
# Operating Temperature: -20C to 70C
#
# Device: Receiving Card 
# Base Address: 0a000000 H 
# Data Length: 100H
# ---------------------------------------------------------------------------------------
   global data
   global logger
   logger = logging.getLogger(LOGGER_NAME)
   logger.info("Getting receiver card monitoring, temperature and voltage")
   check_monitoring [8] = no_of_receiver_cards
   check_monitoring_send = methods.checksum (check_monitoring)
   logger.debug("Sending command: "+' '.join('{:02X}'.format(a) for a in check_monitoring_send))
   ser.write(check_monitoring_send)
   time.sleep(sleep_time)
   if ser.inWaiting()>0:
         response = ser.read(size=ser.inWaiting())
         rx_data = list (response)
         logger.debug("Received data: "+' '.join('{:02X}'.format(a) for a in rx_data))
         if check_response(rx_data):
            if ((rx_data[18] & 0x80))==0x80:
               if (rx_data[18]&0x1)==0:
                  sign = ""
               else:
                  sign = "-"
               logger.info("Temperature (valid): {}{:.1f}°C ({})".format(sign,(rx_data[19]&0xFE)*0.5,hex(rx_data[19])))
               temp_valid="Yes"
               temperature = sign+str((rx_data[19]&0xFE)*0.5)
               temperature = round(float(temperature), 2)
            else:
               logger.info ("Temperature data invalid")
               temp_valid="No"
               temperature="N/A"
            
            if ((rx_data[21]) & 0x80)==0x80:
               logger.info("Voltage (valid): {:.1f}V ({})".format(0.1*(rx_data[21]&0x7F),hex(rx_data[21])))
               voltage_valid="Yes"
               voltage=0.1*(rx_data[21]&0x7F)
               voltage = round(float(voltage), 2)#
            else:
               logger.info ("Voltage data invalid")
               voltage_valid="No"
               voltage="N/A"

            if (rx_data[50]==0xFF):
               logger.info ("Monitoring card available ({})".format(hex(rx_data[50])))
               monitoring_card="Yes"
            else:
               logger.info ("Monitoring card unavailable ({})".format(hex(rx_data[50])))
               monitoring_card="No"
         else:
            temp_valid="N/A"
            temperature="N/A"
            voltage_valid="N/A"
            voltage="N/A"
            monitoring_card="N/A"          
   else:
         logger.info ("No data available at the input buffer")
         temp_valid="N/A"
         temperature="N/A"
         voltage_valid="N/A"
         voltage="N/A"
         monitoring_card="N/A"
   return temp_valid, temperature, voltage_valid, voltage, monitoring_card

# ------------------------------------------------------------------------------------------------------------
# PROGRAM ENTRY POINT - this won't be run only when imported from external module
# ------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
   asyncio.run(communicate_with_server(main, "CHECK_RECEIVING_CARDS_TEMPERATURE"))
