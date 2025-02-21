
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

import serial, sys, os, time, logging, datetime, json, methods, subprocess
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
LOG_FILE = "debug.log"
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
   subprocess.run(["Powershell","stop-process","-Name","NovaMonitorManager, MarsServerProvider"])
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

   #Validate device found on player
   if (device_found == 0):
      message = "NO DEVICE FOUND:\n make sure the correct baudrate is defined in config.json, \nfor windows control pc ensure the NOVA LCT is not running on the host system \nThis can also mean that you don't run the tool as administrator"
      EXIT_CODE = CRITICAL
      my_logger.info ("EXIT CODE: {}, {}".format(EXIT_CODE, message))
      icinga_output(message, 2)
   
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
         message = f"Opened device on port: {ser.name}"
         EXIT_CODE = GOOD
      except SerialException as e:
         message = f"Error opening serial port: {ser.name} - {str(e)}"
         EXIT_CODE = CRITICAL
         my_logger.error(message)
      ser.close()                      
      my_logger.info("Writing to JSON file")
      my_logger.info("{} closed".format(ser.is_open())) # remove at production?
      subprocess.run(["powershell","start",r"$env:USERPROFILE\Desktop\NovaMonitorManager.exe.lnk"])
      icinga_output(message, EXIT_CODE)
    
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
               timeout = time.time() + 5
               while time.time() < timeout:
                  inWaiting = ser.inWaiting()
                  if inWaiting>0: # there should be something at the serial input
                     response = ser.read(size=inWaiting) # read all the data available
                     rx_data = list(response)
                     rx_data_connected = rx_data [19]!=0 or rx_data[18]!=0
                     logger.debug("Received data:"+' '.join('{:02X}'.format(a) for a in rx_data))
                     if check_response(rx_data):                        
                        if (rx_data_connected): # if ACKNOWLEDGE data is not equal to zero then a device is connected
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
         elif (received_data[2]==2):
            logger.error('Command failed due to check error on request data package')
         elif (received_data[2]==3):
            logger.error('Command failed due to check error on acknowledge data package')
         elif (received_data[2]==4):
            logger.error('Command failed due to invalid command')
         else:
            logger.error('Command failed due to UNKNOWN error')
         return False
   except Exception as e:
      logger.error('Command failed due to error: {}'.format(e))
      return False


def icinga_output(message, exit_status):
   print(message)
   sys.exit(exit_status)



# ------------------------------------------------------------------------------------------------------------
# PROGRAM ENTRY POINT - this won't be run only when imported from external module
# ------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
   start_time = time.time()
   main()
   print(time.time() - start_time)