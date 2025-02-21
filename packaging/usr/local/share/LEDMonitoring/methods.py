import serial
import serial.tools.list_ports
import json
import time
import logging
from logging.handlers import TimedRotatingFileHandler
import os, sys
from sys import platform
status = {} # Initialise variable to store status data
global last_updated
if platform == "linux":
   dir = "/data/opt/LEDMonitoring"
else:
   dir = r"C:\LEDMonitoring"
os.chdir(dir)
#os.chdir("/data/opt/LEDMonitoring")
#os.chdir(r'C:\LEDMonitoring')
CONFIG = "config.json"

def loadConfig(logger_name):
   logger = logging.getLogger(logger_name)
   logger.info(f'Loading {CONFIG}')
   try:
        f = open(f"{CONFIG}", "r")
   except IOError:
        data = {}
        data["version"] = "Unkown"
        data["baudrate"] = 115200
        data["sleepTime"] = 0.3
        logger.error(f"Error: {CONFIG} not found, using default parameters.")
        return data
   else:
            data = json.load(f)
            return data
   
def loadConfig_old(text,target_port):
   with open(f'{CONFIG}', 'r') as f:
    data = json.load(f)
    print ("*********************************************************")
    print ("\t\t",text)
    print("\t\tPORT:",target_port)
    print ("\t\t   version: ",data["version"])
    print ("")
    print ("*********************************************************")
    return data

def read_data(filename,logger_name):
   logger = logging.getLogger(logger_name)
   try:
      with open(filename, "r") as read_file:
         temp_data=json.loads(read_file.read())
         logger.info('Reading from {}'.format(filename))
   except IOError: # TODO: or read from backup file
      logger.error('Error: {} not found.'.format(filename))
      temp_data = {}
   return temp_data

def write_data(filename,json_data,logger_name):#, content): #TODO: needs error handling
   logger = logging.getLogger(logger_name)
   try:
       with open(filename, "w") as outfile:
         data=json.dumps(json_data, indent=4)
         outfile.write(data)
       logger.info('Written to {}'.format(filename))
   except IOError: # TODO: or read from backup file
      logger.error('Error: {} not found.'.format(filename))
   return

def checkConnections():
    port = "/dev/ttyUSB0"
    return (port)

def checksum (arg1):# Function definition for checksum calculation
    chksum = 0
    for i in range (2, len(arg1)-2):
        chksum = chksum + arg1 [i]
    chksum = chksum + 0x5555
    chksum_high = chksum & 0xFF
    chksum_low = (chksum & 0xFF00)>>8
    arg1 [len(arg1)-2]=chksum_high
    arg1 [len(arg1)-1]=chksum_low
    return arg1

def setupSerialPort(baud, logger_name):
    logger = logging.getLogger(logger_name)
    logger.info("Setting up serial port")
    port = serial.Serial()
    port.baudrate = baud #Baudrate 115200f or MCTRL300 only; other devices use different baudrate
    port.bytesize =  serial.EIGHTBITS
    port.parity = serial.PARITY_NONE
    port.stopbits = serial.STOPBITS_ONE 
    port.timeout = 0
    return port

def checkConnectedDevice(port, device, sleep_time):
    port.port = device
    # TRY OPENING UP THIS PORT
    try: 
        port.open()
    except Exception as e:
        print (str(e))
    if port.isOpen():
        try:
            port.flushInput() #flush input buffer, discarding all its contents
            port.flushOutput() #flush output buffer, aborting current output and discard all that is in buffer  
            # SEND COMMAND

            # CHECK IF ANYTHING IS AT THE INPUT
            time.sleep (sleep_time)  

            #IF SO, INTERPRET IT

            #OTHERWISE MOVE ON
        except Exception as e1:
            print ("Error communicating with device...",str(e1))
        port.close()
    else:
        exit()

def get_file_handler(file, formatter, schedule, intervals, backups):
   file_handler = TimedRotatingFileHandler(file, when=schedule, encoding='utf-8', interval=intervals, backupCount=backups) # rotates log every day and stores up to 7 backups (1 week)
   file_handler.setFormatter(formatter)
   return file_handler
   
   
      
def get_console_handler(formatter):
   console_handler = logging.StreamHandler()
   console_handler.setFormatter(formatter)
   return console_handler

def get_logger(logger_name,log_file, log_formatter, log_schedule, log_interval, log_backups):
   logger = logging.getLogger(logger_name)
   logger.setLevel(logging.DEBUG) # better to have too much log than not enough
   logger.addHandler(get_file_handler(log_file, log_formatter, log_schedule, log_interval, log_backups))
   #logger.addHandler(get_console_handler(log_formatter))  #writes to the console
   logger.propagate = False # with this pattern, it's rarely necessary to propagate the error up to parent
   return logger

def search_devices(logger_name,ser,sleep_time,connection): # Searches for all sender cards connected to each USB port (/dev/ttyUSBX) on the system
    logger = logging.getLogger(logger_name)
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
                     if check_response(logger_name,rx_data):                        
                        if (rx_data[18]!=0 or rx_data [19]!=0): # if ACKNOWLEDGE data is not equal to zero then a device is connected                           
                              device_found =  device_found + 1
                              connected_port = port
                              valid_ports.append(port)
                              logger.info("Device found on port: {} | {} | {}".format(port, desc, hwid))                       
                        else:
                              logger.info("Device not connected")
               except Exception as e1:
                  logger.error("Error communicating with device: " + str(e1))
               ser.close()
               logger.info("{} closed".format(port)) # remove at production
    logger.info("Found {} device(s)".format(device_found))
    return device_found, valid_ports

def check_response(logger_name,received_data):
   logger = logging.getLogger(logger_name)
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



