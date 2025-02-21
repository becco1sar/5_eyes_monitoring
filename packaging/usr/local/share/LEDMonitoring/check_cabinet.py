#!/usr/bin/env python3
from base_monitoring import *
# ------------------------------------------------------------------------------------------------------------
# MAIN
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
   data = read_data(STATUS_FILE,LOGGER_NAME)
   status = {} # Initialise variable to store status data\
   modules_ok = True # assume all modules are ok to start off
   ser = methods.setupSerialPort(config["baudrate"],LOGGER_NAME) # Initialise serial port
   device_found, valid_ports = search_devices(ser, sleep_time,status)
   #Validate device found on player
   if (device_found == 0):
      message = "NO DEVICE - make sure a valid controller is connected, that the correct baudrate is defined in config.json and ensure the NOVA LCT is not running on the host system \nThis can also mean that you don't run the tool as administrator"
      exit_code = CRITICAL
      my_logger.info ("EXIT CODE: {}, {}".format(exit_code, message))
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
      while receiver_card_found != False: 
         my_logger.info("=============================================================================================================================================")
         my_logger.info ("Connecting to receiver number: {}".format(no_of_receiver_cards+1))    
         try:
            if not get_receiver_connected(ser.port):
               break
            # RETRIEVE PARAMETERS FROM RECEIVER CARDS
            # ---------------------------------------
            get_receiver_card_model(ser.port) #not necessary 
            get_receiver_card_firmware(ser.port) #not necessary 
            display_on = get_cabinet_kill_mode(ser.port) and display_on
            no_of_receiver_cards += 1
            receiver_card_found = get_receiver_connected(ser.port)
         except Exception as e:
            message = e
            exit_code = UNKNOWN
            await icinga_output(message, exit_code, reader, writer)
      print(serial_port)
      if(not display_on):
         message = "ONE OR MORE CABINETS OFF - DISPLAY NOK"
         
         exit_code = CRITICAL
      else:
         message = "All CABINETS OK - DISPLAY OK"
         exit_code = GOOD
      print(message)
      output.append(message)
      exit_codes.append(exit_code)
      ser.close() #closing 
      # -------------------------------------------------------------
      # TO DO
      # Include checks for brightness >0. This should be a WARNING.
      # -------------------------------------------------------------
   
      my_logger.info ("EXIT CODE: {}, {}".format(exit_code, message))
      

   await icinga_output(output, exit_codes, reader, writer)
    
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
            kill="On"
            cabinet_on = True
         elif (rx_data_18==0xFF):
               logger.info ("Cabinet Operating Status (Kill mode): OFF")
               kill="Off"
               cabinet_on = False
         else:
            logger.info ("Cabinet Operating Status (Kill mode): UNKNOWN")
            kill="UNKNOWN"
            cabinet_on = False
      else:
         kill="N/A"
         cabinet_on = False
   else:
         logger.info ("No data available at the input buffer")
         kill="N/A"
         cabinet_on = False
   status[port]["receiverCard"][no_of_receiver_cards]["kill"]=kill
   return cabinet_on
def get_receiver_connected(port):
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
def get_receiver_card_model(port):
   global no_of_receiver_cards
   global receiver_card_found
   logger = logging.getLogger(LOGGER_NAME)
   logger.info("Getting receiver card model")
   check_receiver_model[8] = no_of_receiver_cards
   check_receiver_model_send = methods.checksum (check_receiver_model)
   logger.debug("Sending command: "+' '.join('{:02X}'.format(a) for a in check_receiver_model_send))
   ser.write (check_receiver_model_send)
   time.sleep (sleep_time)
   inWaiting = ser.inWaiting()
   if inWaiting>0:
      status[port]["receiverCard"][no_of_receiver_cards]={}
      response = ser.read(size=inWaiting)
      rx_data = list(response)
      logger.debug("Received data: "+' '.join('{:02X}'.format(a) for a in rx_data))
      rx_data_18 = rx_data[18]
      rx_data_19 = rx_data[19]
      if check_response(rx_data):
         if (rx_data_19==0x45) and (rx_data_18==0x06):
            model = 'Nova A4s'
         elif (rx_data_19==0x45) and (rx_data_18==0x08):
            model = 'Nova A5s'
         elif (rx_data_19==0x45) and (rx_data_18==0x0A):
            model = 'Nova A7s'
         elif (rx_data_19==0x45) and (rx_data_18==0x09):
            model = 'Nova A8s'
         elif (rx_data_19==0x45) and (rx_data_18==0x0F):
            model = 'Nova MRV 366/ MRV 316'
         elif (rx_data_19==0x45) and (rx_data_18==0x10):
            model = 'Nova MRV 328'
         elif (rx_data_19==0x45) and (rx_data_18==0x0E):
            model = 'Nova MRV 308'
         elif (rx_data_19==0x46) and (rx_data_18==0x21):
            model = 'Nova A5s Plus'
         else:
            model =('{}'.format(hex(rx_data_19),hex(rx_data_19)))
      else:
          model = 'N/A'
      status[port]["receiverCard"][no_of_receiver_cards]["receiverModel"]=model
      logger.info ('Receiver card model: {}'.format(model))
   else:
      logger.warning("No data available at the input buffer")
      receiver_card_found = False
   return
def get_receiver_card_firmware(port):
# ---------------------------------------------------------------------------------------
# RECEIVER CARD FW VERSION
# ---------------------------------------------------------------------------------------
   global no_of_receiver_cards
   logger = logging.getLogger(LOGGER_NAME)
   logger.info("Getting receiver card firmware")
   check_receiver_fw [8] = no_of_receiver_cards
   check_receiver_fw_send = methods.checksum (check_receiver_fw)
   logger.debug("Sending command: "+' '.join('{:02X}'.format(a) for a in check_receiver_fw_send))
   ser.write (check_receiver_fw_send)
   time.sleep (sleep_time)
   inWaiting = ser.inWaiting()
   if inWaiting>0:
      response = ser.read(size=inWaiting)
      rx_data = list(response)
      logger.debug("Received data: "+' '.join('{:02X}'.format(a) for a in rx_data))
      rx_data_18 = rx_data[18]
      rx_data_19 = rx_data[19]
      rx_data_20 = rx_data[20]
      rx_data_21 = rx_data[21]
      if check_response(rx_data):
         FPGA=str(rx_data_18)+'.'+str(rx_data_19)+'.'+str(rx_data[20])+'.'+str("{:02x}".format(rx_data[21]))
      else:
         FPGA="N/A" 
   else:
         logger.warning("No data available at the input buffer")
         FPGA="N/A"
   status[port]["receiverCard"][no_of_receiver_cards]["receiverFPGA"]=FPGA
   logger.info('Receiver Card FPGA Firmware version: {}'.format(FPGA))
# ------------------------------------------------------------------------------------------------------------
# PROGRAM ENTRY POINT - this won't be run only when imported from external module
# ------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
   asyncio.run(communicate_with_server(main, "CHECK_CABINET"))
