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
LOG_FILE = "debug_sender_cards.log"
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
   writer.write("check_cabinet". encode())
   await writer.drain()
   logger.info("AWAITING PERMISSION TO USE COM PORTS FROM LOCAL SERVER")
   data = await reader.read(1024)
   if not data.decode().strip() == "START":
      logger.error("")
      await icinga_output("Could not make connection with localserver to access com port", UNKNOWN,reader, writer)
   logger.info("PERMISSION TO USE COM PORT GRANTED STARTING CHECK_CABINET SCRIPT")
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
   module_status_info = {}
   exit_code = UNKNOWN
   
   logger.info("*********************************************************************************************************************************************")
   logger.info("5Eyes - Starting Display Status Checks")
   config = loadConfig(LOGGER_NAME) # Load the configuration information
   logger.info("Version: {}, Baudrate: {}, Sleep Time: {}, Flash Timeout: {}".format(config["version"],config["baudrate"],config["sleepTime"],config["flashWaitTime"]))
   last_updated = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
   sleep_time = float(config["sleepTime"])
   flash_wait_time = float(config["flashWaitTime"])
   data = read_data(STATUS_FILE,LOGGER_NAME)
   status = {} # Initialise variable to store status data\
   modules_ok = True # assume all modules are ok to start off
   ser = methods.setupSerialPort(config["baudrate"],LOGGER_NAME) # Initialise serial port
   device_found, valid_ports = search_devices()
   print(valid_ports)
   #Validate device found on player
   if (device_found == 0):
      message = "NO DEVICE - make sure a valid controller is connected, that the correct baudrate is defined in config.json and ensure the NOVA LCT is not running on the host system"
      exit_code = CRITICAL
      logger.info ("EXIT CODE: {}, {}".format(exit_code, message))
      await icinga_output(message, exit_code,reader, writer)
   
   #looping through each sender card found
   i=0
   for serial_port in sorted(valid_ports):
      logger.info("*******************    DEVICE {}   *******************".format(i))
      logger.info("Connecting to device on {}".format(serial_port))
      ser.port = serial_port
      
      try: 
         if ser.isOpen() == False:
            ser.open()
         ser.flushInput() #flush input buffer, discarding all its contents
         ser.flushOutput() #flush output buffer, aborting current output and discard all that is in buffer
         logger.info("Opened device on port: " + ser.name) # remove at production
      except SerialException as e:
         message = f"Error opening serial port: {ser.name} - {str(e)}"
         exit_code = CRITICAL
         logger.error(message)
         await icinga_output(message, exit_code,reader, writer)
      # -------------------------------------
      # RETRIEVE PARAMETERS FROM SENDER CARDS
      # -------------------------------------
      model = get_sender_card_model(ser.port)                 
      ser.close() #closing 
      i += 1
      logger.info("Writing to JSON file")
      write_data(STATUS_FILE, status, LOGGER_NAME) # This could go to the end to include exit_code and output message

      if (device_found < config["devices"]):# Check if a device is missing
         message = "DEVICE MISSING (SENDER CARD) - {} EXPECTED, {} FOUND".format(config["devices"],device_found)
         exit_code = CRITICAL
      else:
         message = f"SENDER CARD OK"
         exit_code = GOOD
      # -------------------------------------------------------------
      # TO DO
      # Include checks for brightness >0. This should be a WARNING.
      # -------------------------------------------------------------
   
      logger.info ("EXIT CODE: {}, {}".format(exit_code, message))
      # ----------------------------------------------------------------
      # TO DO
      # Consider including exit_code and output message into status.json     
      # ----------------------------------------------------------------
      
      await icinga_output(message, exit_code,reader, writer)

def get_sender_card_model(port):
# ---------------------------------------------------------------------------------------
# DETERMINE SENDER CARD MODEL
# Check which sender card hardware model is connected.
# NOTE - Different sender cards use different baud rates; may require a method for changing this
# Device: Sending Card 
# Base Address: 0x0000_0000H 
# Data Length: 2H
# -----------------------------
   logger = logging.getLogger(LOGGER_NAME)
   logger.info("Getting sender card model")
   sender_model_send = methods.checksum(sender_model)
   logger.debug("Sending command: "+' '.join('{:02X}'.format(a) for a in sender_model_send))
   ser.write (sender_model_send)
   time.sleep (sleep_time)
   if ser.inWaiting()>0:
      response = ser.read(size=ser.inWaiting())
      rx_data = list(response)
      logger.debug("Received data: "+' '.join('{:02X}'.format(a) for a in rx_data))
      if check_response(rx_data):
         if (rx_data[18]==1 and rx_data[19]==1):
            model="MCTRL500"
         elif (rx_data[18]==1 and rx_data[19]==0):
            model="MSD300/MCTRL300"
         elif (rx_data[18]==1 and rx_data[19]==0x11):
            model="MSD600/MCTRL600/MCTRL610/MCTRL660"
         else:
            model="UNKNOWN"
      else:
          model="N/A"
   else:
      logger.warning("No data available at the input buffer")
      model="N/A"
   status[port]["controllerModel"] = model
   logger.info("Sender card model: " + model)
   return (model)

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
   asyncio.run(communicate_with_server())
