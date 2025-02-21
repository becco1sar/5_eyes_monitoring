#!/usr/bin/python3
import asyncio, logging, sys, os, datetime, serial, serial.tools.list_ports, methods
from sys import platform
from serial import SerialException
from methods import *
from command import *

# EXIT CODES
GOOD = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3

# LOGGER
FORMATTER = logging.Formatter('%(asctime)s %(name)s %(levelname)-8s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
LOG_FILE = "debug.log"
STATUS_FILE = "status.json"
LOGGER_NAME = 'display_status'
LOGGER_SCHEDULE = 'midnight'
LOGGER_BACKUPS = 7
LOGGER_INTERVAL = 1

# DEFINITIONS AND INITIALISATIONS
if platform == "linux":
   dir = r"/data/opt/LEDMonitoring"
else:
   dir = r"C:\LEDMonitoring"
os.chdir(dir)
 
async def init(log_file):
   global sleep_time
   global flash_wait_time
   global status 
   global ser
   global last_updated
   global data
   global number_of_modules
   global device_found
   global logger
   global valid_ports

   module_status_info = {}
   exit_code = UNKNOWN
   logger = methods.get_logger(LOGGER_NAME,log_file,FORMATTER,LOGGER_SCHEDULE,LOGGER_INTERVAL,LOGGER_BACKUPS) # Set up the logging
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
   number_of_modules = config["modules"]
   ser = methods.setupSerialPort(config["baudrate"],LOGGER_NAME) # Initialise serial port
   device_found, valid_ports = search_devices(ser)
    
async def communicate_with_server(func, log_file):
    await init(log_file)
    """Asynchronous client communication with the server."""
    logger.info("ESTABLISHING CONNECTION WITH LOCAL SERVER QUEUE")
    reader, writer = await asyncio.open_connection("127.0.0.1",8888)
    if not reader and not writer:
        logger.error("COULD NOT ESTABLISH CONNECTION WITH 127.0.0.1 ON PORT 8888")
    writer.write("check_dvi". encode())
    await writer.drain()
    logger.info("AWAITING PERMISSION TO USE COM PORTS FROM LOCAL SERVER")
    data = await reader.read(1024)
    if not data.decode().strip() == "START":
        logger.error("")
        await icinga_output("Could not make connection with localserver to access com port", UNKNOWN,reader, writer)
    logger.info("PERMISSION TO USE COM PORT GRANTED STARTING CHECK_DVI SCRIPT")
    await func(reader, writer, logger,valid_ports, ser)
    
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
# FUNCTION DEFINITIONS
def search_devices(ser): # Searches for all sender cards connected to each USB port (/dev/ttyUSBX) on the system
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
                  time.sleep(sleep_time) # allow some time for the device to respond        
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
 #----------------------------------------------------------------------------------------------
def check_response(received_data):
   logger = logging.getLogger(LOGGER_NAME)
   try:
      if (received_data[2]==0):   
         return True
      else:
         if (received_data[2]==1):
            logger.error('Command failed due to time out (tiout on trying to access devices connected to a sending card)')
         else:
            if (received_data[2]==2):
               logger.error('Command failed due to check erron request data package')
            else:
                  if (received_data[2]==3):
                     logger.error('Command failed due to cheerror on acknowledge data package')
                  else:
                        if (received_data[2]==4):
                           logger.error('Command failed due to invalid command')
                        else:
                           logger.error('Command failed due to unkown error')
         return False
   except Exception as e:
      logger.error('Command failed due to error: {}'.format(e))
      return False
#----------------------------------------------------------------