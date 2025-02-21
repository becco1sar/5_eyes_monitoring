# ------------------------------------------------------------------------------------------------------------
# IMPORTS
import sys
#sys.path.append('/data/LEDManager')
import serial
import time
import serial.tools.list_ports
import logging
from logging.handlers import TimedRotatingFileHandler
import datetime
import json
import methods
from methods import read_data, write_data, loadConfig

FORMATTER = logging.Formatter('%(asctime)s %(name)s %(levelname)-8s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
LOG_FILE_DEBUG = "debug.log"#"/data/LEDManager/debug.log"
LOG_FILE_ACTIVITY = 'activity.log'#"/data/LEDManager/activity.log"
LOGGER_NAME_ACTIVITY = 'display_control'
LOGGER_NAME_DEBUG = 'display_control_debug'
LOGGER_SCHEDULE_DEBUG = 'midnight'
LOGGER_SCHEDULE_ACTIVITY = 'D'
LOGGER_BACKUPS = 7
LOGGER_INTERVAL = 1
# ------------------------------------------------------------------------------------------------------------
# COMMANDS
connection = list(b"\x55\xAA\x00\xAA\xFE\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x02\x00\x01\x57") # Reconnect Sending Card/Receiving Card
set_display_off = list(b"\x55\xAA\x00\x80\xFE\x00\x01\x00\xFF\xFF\x01\x00\x00\x01\x00\x02\x01\x00\xFF\xD7\x58")
#set_display_off = list(b"\x55\xAA\x00\x80\xFE\x00\x01\x00\xFF\xFF\x01\x00\x00\x01\x00\x02\x01\x00\xFF\xD6\x59")
#display_on = list(b"\x55\xAA\x00\x80\xFE\x00\x01\x00\xFF\xFF\x01\x00\x00\x01\x00\x02\x01\x00\x00\xD7\x58")
# ------------------------------------------------------------------------------------------------------------

def main(argv):
    #print('Hello control')
    serial_port = argv
    my_logger_debug.info("Using port: {}".format(serial_port))
    ser.port = serial_port
    try: 
        ser.open()
    except Exception as e:
        my_logger_debug.error("Error opening serial port: " + ser.name +" - "+ str(e))
        #exit()
    if ser.isOpen():
        try:
            ser.flushInput() #flush input buffer, discarding all its contents
            ser.flushOutput() #flush output buffer, aborting current output and discard all that is in buffer
            my_logger_debug.info("Opened device on port: "+ser.name) # remove at production
            set_display_off_send = methods.checksum(set_display_off)
            my_logger_debug.debug("Sending command: " + ' '.join('{:02X}'.format(a) for a in set_display_off_send))
            ser.write (set_display_off_send)
            time.sleep (sleep_time)
            if ser.inWaiting()>0:
	            #print ("Data available at the input buffer: ",ser.inWaiting()," bytes")
                response = ser.read(size=ser.inWaiting())
                rx_data = list(response)
                my_logger_debug.debug("Received data: "+' '.join('{:02X}'.format(a) for a in rx_data))
                if check_response(rx_data):
                    my_logger_activity.info('Display turned OFF')
                else:
                    my_logger_debug.error ("Error turning on the display")
            else:
                my_logger_debug.debug ("No data available at the input buffer")
        except Exception as e1:
            my_logger_debug.error("Error opening serial port: " + str(e))
            #exit()
        ser.close()
        my_logger_debug.info("Closed device on port: "+ser.name) # remove at production
    else:
        my_logger_debug.error("Error communicating with device: "+ser.name)
        #exit()
    
    

def search_devices():
    logger = logging.getLogger(LOGGER_NAME_DEBUG)
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
                            device_found =  device_found + 1
                            connected_port = port
                            valid_ports.append(port)
                            logger.info("Device found on port: {} | {} | {}".format(port, desc, hwid))                       
                        else:
                            logger.info("Device not connected")
                     else:
                        logger.info("Device not connected") 
               except Exception as e1:
                  logger.error("Error communicating with device: " + str(e1))
               ser.close()
               logger.info("{} closed".format(port)) # remove at production
    logger.info("Found {} device(s)".format(device_found))
    return device_found, valid_ports

def check_response(received_data):
   logger = logging.getLogger(LOGGER_SCHEDULE_DEBUG)
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

# this won't be run when imported
if __name__ == "__main__":
    #main()
    my_logger_debug = methods.get_logger(LOGGER_NAME_DEBUG,LOG_FILE_DEBUG,FORMATTER,LOGGER_SCHEDULE_DEBUG,LOGGER_INTERVAL,LOGGER_BACKUPS) # Set up the logging
    my_logger_activity = methods.get_logger(LOGGER_NAME_ACTIVITY,LOG_FILE_ACTIVITY,FORMATTER,LOGGER_SCHEDULE_ACTIVITY,LOGGER_INTERVAL,LOGGER_BACKUPS) # Set up the logging
    my_logger_debug.info("--------------------------------------------------------------")
    my_logger_debug.info("LEDManager - Switch OFF the display")
    config = loadConfig(LOGGER_NAME_DEBUG) # Load the configuration information
    my_logger_debug.info("Version: {}, Baudrate: {}, Sleep Time: {}".format(config["version"],config["baudrate"],config["sleepTime"]))
    last_updated = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    sleep_time = float(config["sleepTime"])
    ser = methods.setupSerialPort(config["baudrate"],LOGGER_NAME_DEBUG) # Initialise serial port
    try:
        main(sys.argv[1])
    except:
        my_logger_debug.info ("USB port incorrect or not specified. Searching for connected devices")
        device_found, valid_ports = search_devices()
        if (device_found!=0):
            i=0
            for port in sorted(valid_ports):
                    print("Available port: {}, (".format(port),i,")")
                    i=i+1
            selection = False
            connected_port_index = None
            while selection==False:
                #print ("Choose port:")
                connected_port_index = input('PLEASE SELECT TARGET PORT (INDEX): ')
                try:
                    index=int(connected_port_index)
                    if not 0 <= index < len(valid_ports):
                        print ("Input not valid, please select one of the available ports")
                        #exit()
                        #sys.stderr.write('--- Invalid index!\n')
                        continue
                except ValueError:
                    pass
                    #exit()
                else:
                        connected_port = valid_ports[index]
                        selection = True
                        main(connected_port)
                #return selected_port
            #connected_port =  ports[selected_port]#[selected_port]
            #my_logger_debug.info("Using port: {}".format(connected_port))
        else:
            my_logger_debug.info("No devices found. Exiting.")
            exit()
        #main(connected_port)
