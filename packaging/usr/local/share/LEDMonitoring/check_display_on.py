#!/usr/bin/env python3

from base_monitoring import *
# ------------------------------------------------------------------------------------------------------------
# MAIN
def main():
   global sleep_time
   global flash_wait_time
   global status 
   global ser
   global last_updated
   global data
   global no_of_receiver_cards
   global receiver_card_found
   module_status_info = {}
   EXIT_CODE = UNKNOWN
   
   my_logger = methods.get_logger(LOGGER_NAME,LOG_FILE,FORMATTER,LOGGER_SCHEDULE,LOGGER_INTERVAL,LOGGER_BACKUPS) # Set up the logging
   my_logger.info("*********************************************************************************************************************************************")
   my_logger.info("5Eyes - Starting Display Status Checks")
   config = loadConfig(LOGGER_NAME) # Load the configuration information
   my_logger.info("Version: {}, Baudrate: {}, Sleep Time: {}, Flash Timeout: {}".format(config["version"],config["baudrate"],config["sleepTime"],config["flashWaitTime"]))
   last_updated = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
   sleep_time = float(config["sleepTime"])
   flash_wait_time = float(config["flashWaitTime"])
   data = read_data(STATUS_FILE,LOGGER_NAME)
   status = {} # Initialise variable to store status data\
   modules_ok = True # assume all modules are ok to start off
   ser = methods.setupSerialPort(config["baudrate"],LOGGER_NAME) # Initialise serial port
   device_found, valid_ports = search_devices()
   start_time = time.time()
   #Validate device found on player
   if (device_found == 0):
      message = "NO DEVICE - make sure a valid controller is connected, that the correct baudrate is defined in config.json and ensure the NOVA LCT is not running on the host system \nThis can also mean that you don't run the tool as administrator"
      EXIT_CODE = CRITICAL
      my_logger.info ("EXIT CODE: {}, {}".format(EXIT_CODE, message))
      end_time = time.time()
      icinga_output(message, EXIT_CODE)
   
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
         EXIT_CODE = CRITICAL
         my_logger.error(message)
         icinga_output(message, EXIT_CODE)
         
      # -------------------------------------
      # RETRIEVE PARAMETERS FROM SENDER CARDS
      # -------------------------------------
      receiver_card_found = True
      no_of_receiver_cards = 0
      status[serial_port]["receiverCard"]={}
      display_on = True
      message, EXIT_CODE = get_cabinet_kill_mode(ser.port) 
      ser.close() #closing 
      my_logger.info("Writing to JSON file")
      
      # -------------------------------------------------------------
      # TO DO
      # Include checks for brightness >0. This should be a WARNING.
      # -------------------------------------------------------------
   
      my_logger.info ("EXIT CODE: {}, {}".format(EXIT_CODE, message))
      
      # ----------------------------------------------------------------
      # TO DO
      # Consider including EXIT_CODE and output message into status.json     
      # ----------------------------------------------------------------
      
      icinga_output(message, EXIT_CODE)
    
# ------------------------------------------------------------------------------------------------------------
# FUNCTION DEFINITIONS
def get_cabinet_kill_mode(port):
#-------------------------------------------------------------------------
# CHECK KILL MODE (CABINET STATUS)
# This is essentially information about whether the display is ON or OFF
#-------------------------------------------------------------------------
   global no_of_receiver_cards
   logger = logging.getLogger(LOGGER_NAME)
   logger.info("Getting cabinet kill mode (on/off)")
   kill_mode[8] = no_of_receiver_cards
   kill_mode_send = methods.checksum(kill_mode)
   logger.debug("Sending command: "+' '.join('{:02X}'.format(a) for a in kill_mode_send))
   ser.write (kill_mode_send)
   time.sleep (sleep_time)
   inWaiting = ser.inWaiting()
   if inWaiting>0:
      response = ser.read(size=inWaiting)
      rx_data = list(response)
      logger.debug("Received data: "+' '.join('{:02X}'.format(a) for a in rx_data))
      rx_data_18 = rx_data[18]
      if check_response(rx_data):
         if (rx_data_18==0x00):
            logger.info ("Cabinet Operating Status (Kill mode): ON")
            kill=GOOD
            cabinet_on = True
         elif (rx_data_18==0xFF):
               logger.info ("Cabinet Operating Status (Kill mode): OFF")
               kill=WARNING
               cabinet_on = False
         else:
            logger.info ("Cabinet Operating Status (Kill mode): UNKNOWN")
            kill=UNKNOWN
            cabinet_on = False
      else:
         kill=UNKNOWN
         cabinet_on = False

   else:
         logger.info ("No data available at the input buffer")
         kill=UNKNOWN
         cabinet_on = False
   if cabinet_on: message = "Display On"
   else: message= "Display unknown"
   return message, kill


# ------------------------------------------------------------------------------------------------------------
# PROGRAM ENTRY POINT - this won't be run only when imported from external module
# ------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
   asyncio.run(communicate_with_server(main, "CHECK_RECEIVING_CARDS_TEMPERATURE"))
