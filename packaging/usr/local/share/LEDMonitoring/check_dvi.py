#!/usr/bin python3
import serial, sys, os, time, logging, datetime, methods, subprocess, asyncio
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
LOG_FILE = "debug_brightness.log"
STATUS_FILE = "status.json"
LOGGER_NAME = 'display_status'
LOGGER_SCHEDULE = 'midnight'
LOGGER_BACKUPS = 7
LOGGER_INTERVAL = 1
MAX_ATTEMPT = 5

MODEL_6XX = "MSD600/MCTRL600/MCTRL610/MCTRL660"
logger = methods.get_logger(LOGGER_NAME,LOG_FILE,FORMATTER,LOGGER_SCHEDULE,LOGGER_INTERVAL,LOGGER_BACKUPS) # Set up the logging
# EXIT CODES
GOOD = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3

async def communicate_with_server():
   global data
   global logger

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
   await main(reader, writer)
    
async def main(reader, writer):
    global sleep_time
    global flash_wait_time
    global status 
    global ser
    global last_updated
    global data
    global logger
    global no_of_receiver_cards
    global receiver_card_found
    """Main function to perform the display status check."""
    try:
        logger.info("*********************************************************************************************************************************************")
        logger.info("5Eyes - Starting Display Status Checks")
        
        # Load configuration
        config = loadConfig('display_status')  # Ensure 'display_status' is correct
        logger.info(f"Version: {config['version']}, Baudrate: {config['baudrate']}, Sleep Time: {config['sleepTime']}, Flash Timeout: {config['flashWaitTime']}")

        last_updated = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        sleep_time = float(config["sleepTime"])
        flash_wait_time = float(config["flashWaitTime"])
        data = read_data("status.json", 'display_status')
        status = {}  # Initialize variable to store status data
        modules_ok = True  # Assume all modules are ok to start off

        # Initialize serial port
        ser = methods.setupSerialPort(config["baudrate"], 'display_status')

        device_found, valid_ports = search_devices()

        # Validate device found on player
        if device_found == 0:
            message = (
                "NO DEVICE - make sure a valid controller is connected, that the correct baudrate is defined in config.json "
                "and ensure the NOVA LCT is not running on the host system.\nThis can also mean that you don't run the tool as administrator."
            )
            exit_code = CRITICAL
            logger.info(f"EXIT CODE: {exit_code}, {message}")
            await icinga_output(message, exit_code, reader, writer)

        # Looping through each sender card found
        for i, serial_port in enumerate(sorted(valid_ports)):
            logger.info(f"*******************    DEVICE {i}   *******************")
            logger.info(f"Connecting to device on {serial_port}")
            ser.port = serial_port      
            try: 
                if not ser.isOpen():
                    ser.open()
                ser.flushInput()  # Flush input buffer, discarding all its contents
                ser.flushOutput()  # Flush output buffer, aborting current output and discarding all that is in buffer
                logger.info(f"Opened device on port: {ser.name}")  # Remove in production
            except SerialException as e:
                message = f"Error opening serial port: {ser.name} - {str(e)}"
                exit_code = CRITICAL
                logger.error(message)
                await icinga_output(message, exit_code, reader, writer)
            
            # Retrieve parameters from sender cards
            DVI = get_DVI_signal_status(ser.port)
            ser.close()  # Closing 
            logger.info("Writing to JSON file")
            if DVI != "Valid":  # Check if a video input on DVI is valid
                message = "DVI SIGNAL MISSING" 
                exit_code = CRITICAL   
            else:
                message = "DVI SIGNAL OK"
                exit_code = GOOD
            # TODO: Include checks for brightness >0. This should be a WARNING.
        
            logger.info(f"EXIT CODE: {exit_code}, {message}")
            
            # TODO: Consider including exit_code and output message into status.json     
            
            await icinga_output(message, exit_code, reader, writer)

    except Exception as e:
        logger.exception(f"Error in main function: {e}")
        icinga_output("An error occurred during execution.", UNKNOWN, writer)

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
def get_DVI_signal_status(port):
# ---------------------------------------------------------------------------------------
# DVI SIGNAL CHECK
# Device: Sending Card
# Base Address: 02000000 H 
# Data Length: 1H
# Applicable to all sender cards
# ---------------------------------------------------------------------------------------
   logger = logging.getLogger(LOGGER_NAME)
   logger.info("Getting DVI signal")
   logger.debug("Sending command: "+' '.join('{:02X}'.format(a) for a in check_DVI_signal))
   ser.write (check_DVI_signal)
   time.sleep (sleep_time)
   if ser.inWaiting()>0:
      response = ser.read(size=ser.inWaiting())
      rx_data = list(response)
      logger.debug("Received data: "+' '.join('{:02X}'.format(a) for a in rx_data))
      if check_response(rx_data):
         if (rx_data[18]==0x00):
            DVI_valid = "Not valid"
         else:
            if (rx_data[18]==0x01):
                     DVI_valid = "Valid"
            else:
                     DVI_valid = "Unkown"
      else:
         DVI_valid = "N/A"
   else:
         logger.warning("No data available at the input buffer")
         DVI_valid = "N/A"
   status[port]["DVISignal"] = DVI_valid
   logger.info("DVI signal: "+ DVI_valid)
   return (DVI_valid)
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
if __name__ == "__main__":
    try:
        asyncio.run(communicate_with_server())
    except KeyboardInterrupt:
        logger.info("Client shut down manually.")
        sys.exit(UNKNOWN)
    except Exception as e:
        logger.exception(f"Client encountered an error: {e}")
        sys.exit(UNKNOWN)
