#!/usr/bin/env python3
#------------------------------------------------------------------------------------------------------------
# CHECK DISPLAY STATUS VIA NOVASTAR SENDER AND RECEIVER
# Please read the README.TXT file for further information and details.
#
# USAGE
# Windows: python display_status.py & echo %errorlevel%
# Linux: python display_status.py ;echo $?
#
# DESCRIPTION
# - A one-shot Python script which queries a number of parameters from a Novstar sender/control system
# - Script should be run at regular intervals, for example every 20 minutes
# - (TELEMETRY) Resulting values written into status.json file
# - (STATUS) Script outputs a string indicating current screen status and and exit code corresponding to the monitoring agent (e.g. Icinga) expected codes (0,1,2,3)
# - Additional data is written into debug.log and allows deep investigation on issues (mainly communications with controller)
# - The display configuration is stored into config.json file
# - The communications protocol configuration data is stored in config.json
# - ALS transition take circa 2m 30s (per step? TBC)
#
# ERROR CODES
# - 0 = OK - display is in normal working order: all vital parameters as expected
# - 1 = WARNING - vital parameters returning abnormal values or anomaly
#       ! sender card not detected
#       ! DVI input not valid
#       ! receiver cards not detected or missing
#       ! kill mode OFF
#       ! faulty modules
#       + ribbon cables
#       + brightness sensor not detected
#       + brightness level low
#       + temperature warning
#       + voltage warning
#       + test mode
# - 2 = CRITICAL - display is not showing content correctly or at all
# - 3 = UNKNOWN - any other event
#
# KNOWN BUGS OR ISSUES
#
# ---------------------------------------------------------------f---------------------------------------------
# IMPORTS

import serial, sys, os, time, logging, datetime, json, methods, asyncio
from serial import SerialException
import serial.tools.list_ports
from sys import platform
from logging.handlers import TimedRotatingFileHandler
from methods import read_data, write_data, loadConfig
from command import *
# ------------------------------------------------------------------------------------------------------------
# DEFINITIONS AND INITIALISATIONS
if platform == "linux":
   dir = "/data/opt/LEDMonitoring"
else:
   dir = r"C:\LEDMonitoring"
os.chdir(dir)

# LOGGER
FORMATTER = logging.Formatter('%(asctime)s %(name)s %(levelname)-8s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
LOG_FILE = "debug_receiving_cards.log"
STATUS_FILE = "status.json"
LOGGER_NAME = 'display_status'
LOGGER_SCHEDULE = 'midnight'
LOGGER_BACKUPS = 7
LOGGER_INTERVAL = 1

MODEL_6XX = "MSD600/MCTRL600/MCTRL610/MCTRL660"

# EXIT CODES
GOOD = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3
async def communicate_with_server():
   global data
   global logger
   logger = methods.get_logger(LOGGER_NAME,LOG_FILE,FORMATTER,LOGGER_SCHEDULE,LOGGER_INTERVAL,LOGGER_BACKUPS) # Set up the logging
   """Asynchronous client communication with the server."""
   logger.info("ESTABLISHING CONNECTION WITH LOCAL SERVER QUEUE")
   reader, writer = await asyncio.open_connection("127.0.0.1",8888)
   if not reader and not writer:
      logger.error("COULD NOT ESTABLISH CONNECTION WITH 127.0.0.1 ON PORT 8888")
   writer.write("check_receiving_cards". encode())
   await writer.drain()
   logger.info("AWAITING PERMISSION TO USE COM PORTS FROM LOCAL SERVER")
   data = await reader.read(1024)
   if not data.decode().strip() == "START":
      logger.error("")
      await icinga_output("Could not make connection with localserver to access com port", UNKNOWN,reader, writer)
   logger.info("PERMISSION TO USE COM PORT GRANTED STARTING check_receiving_cards SCRIPT")
   await main(reader, writer)
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
   device_found, valid_ports = search_devices()
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
      
      while receiver_card_found != False: 
         my_logger.info("=============================================================================================================================================")
         my_logger.info ("Connecting to receiver number: {}".format(no_of_receiver_cards+1))    
         try:     
            if not get_receiver_connected(ser.port):
               break
            no_of_receiver_cards += 1
            
         except Exception as e:
            message = e
            exit_code = UNKNOWN
            await icinga_output(message, exit_code, reader, writer)
      if no_of_receiver_cards != total_receiver_cards: message, exit_code = f"NO of receiver cards {no_of_receiver_cards} EXPECTED {total_receiver_cards}", CRITICAL
      else: message, exit_code = f"NO of receiver cards {no_of_receiver_cards} EXPECTED {total_receiver_cards}", GOOD
      ser.close() #closing 
      my_logger.info("Writing to JSON file")
      
      # -------------------------------------------------------------
      # TO DO
      # Include checks for brightness >0. This should be a WARNING.
      # -------------------------------------------------------------
   
      my_logger.info ("EXIT CODE: {}, {}".format(exit_code, message))
      
      # ----------------------------------------------------------------
      # TO DO
      # Consider including exit_code and output message into status.json     
      # ----------------------------------------------------------------
      
      await icinga_output(message, exit_code, reader, writer)
    
# ------------------------------------------------------------------------------------------------------------
# FUNCTION DEFINITIONS

def search_devices(): # Searches for all sender cards connected to each USB port (/dev/ttyUSBX) on the system
    logger = logging.getLogger(LOGGER_NAME)
    ports = serial.tools.list_ports.comports()
    logger.info("Found {} serial ports".format(len(ports)))
    device_found = 0
    valid_ports = []
    for port, desc, hwid in sorted(ports):
         logger.info("Searching sender card on port: " + port)
         ser.port = port
         try: 
               ser.open()
         except Exception as e:
               logger.error(str(e))
         if ser.isOpen():
               logger.info("{} opened".format(port)) # remove at production
               try:
                  ser.flushInput() # flush input buffer, discarding all its contents
                  ser.flushOutput() # flush output buffer, aborting current output and discard all that is in buffer
                  ser.write (connection) # send CONNECTION command to check whether any devices are connected
                  logger.debug("Sending command: " + ' '.join('{:02X}'.format(a) for a in connection))
                  time.sleep (sleep_time) # allow some time for the device to respond        
                  if ser.inWaiting()>0: # there should be something at the serial input
                     response = ser.read(size=ser.inWaiting()) # read all the data available
                     rx_data = list(response)
                     logger.debug("Received data:"+' '.join('{:02X}'.format(a) for a in rx_data))
                     if check_response(rx_data):                        
                        if (rx_data[18]!=0 or rx_data [19]!=0): # if ACKNOWLEDGE data is not equal to zero then a device is connected
                              # **********************************************************
                              status[port] = {} 
                              status[port]["lastUpdated"] = last_updated
                              status[port]["connectedControllers"] = device_found
                              status[port]["targetPort"] = port
                              status[port]["controllerDescription"] = desc
                              status[port]["controllerHardware"] = hwid
                              # **********************************************************
                              device_found =  device_found + 1
                              connected_port = port
                              valid_ports.append(port)
                              logger.info("Device found on port: {} | {} | {}".format(port, desc, hwid))                       
                        else:
                              logger.info("Device not connected")
               except Exception as e1:
                  logger.error("Error communicating with device: " + str(e1))
               ser.close()
               logger.info("{} closed".format(port)) # remove at production?
    logger.info("Found {} device(s)".format(device_found))
    return device_found, valid_ports

def check_response(received_data):
   logger = logging.getLogger(LOGGER_NAME)
   try:
      if (received_data[2]==0):   
         return True
      else:
         if (received_data[2]==1):
            logger.error('Command failed due to time out (time out on trying to access devices connected to a sending card)')
         else:
            if (received_data[2]==2):
               logger.error('Command failed due to check error on request data package')
            else:
                  if (received_data[2]==3):
                     logger.error('Command failed due to check error on acknowledge data package')
                  else:
                        if (received_data[2]==4):
                           logger.error('Command failed due to invalid command')
                        else:
                           logger.error('Command failed due to unkown error')
         return False
   except Exception as e:
      logger.error('Command failed due to error: {}'.format(e))
      return False

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


async def icinga_output(message, exit_status, reader, writer):
    """Outputs the result to Icinga and notifies the server."""
    print(message)
    try:
        writer.write(b"Done")
        await writer.drain()
        await reader.read(1024)
        writer.close()
        await writer.wait_closed()
        logger.info("Sent 'done' to server.")
    except Exception as e:
        logger.error(f"Error sending completion message: {e}")
    sys.exit(exit_status)
# ------------------------------------------------------------------------------------------------------------
# PROGRAM ENTRY POINT - this won't be run only when imported from external module
# ------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
   try:      
      asyncio.run(communicate_with_server())
   except KeyboardInterrupt:
      logger.info("Client shut down manually.")
      sys.exit(UNKNOWN)
   except Exception as e:
      logger.exception(f"Client encountered an error: {e}")
      sys.exit(UNKNOWN)