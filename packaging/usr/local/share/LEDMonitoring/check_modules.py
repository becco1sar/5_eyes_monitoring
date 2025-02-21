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
log_file = "debug_modules.log" 
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

async def communicate_with_server():
   global data
   global logger
   logger = methods.get_logger(LOGGER_NAME,log_file,FORMATTER,LOGGER_SCHEDULE,LOGGER_INTERVAL,LOGGER_BACKUPS) # Set up the logging
   """Asynchronous client communication with the server."""
   logger.info("ESTABLISHING CONNECTION WITH LOCAL SERVER QUEUE")
   reader, writer = await asyncio.open_connection("127.0.0.1",8888)
   if not reader and not writer:
      logger.error("COULD NOT ESTABLISH CONNECTION WITH 127.0.0.1 ON PORT 8888")
   writer.write("check modules". encode())
   await writer.drain()
   logger.info("AWAITING PERMISSION TO USE COM PORTS FROM LOCAL SERVER")
   data = await reader.read(1024)
   if not data.decode().strip() == "START":
      logger.error("")
      await icinga_output("Could not make connection with localserver to access com port", UNKNOWN,reader, writer)
   logger.info("PERMISSION TO USE COM PORT GRANTED STARTING CHECK_MODULES SCRIPT")
   await main(reader, writer)
    
async def main(reader, writer):
   global sleep_time
   global flash_wait_time
   global status 
   global ser
   global last_updated
   global number_of_modules
   global device_found
   global logger
   global valid_ports
   global receiver_card_found
   global no_of_receiver_cards
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
   number_of_modules = config["modules"]
   ser = methods.setupSerialPort(config["baudrate"],LOGGER_NAME) # Initialise serial port
   device_found, valid_ports = search_devices(ser)
   start_time = time.time()
   #Validate device found on player
   if not valid_ports:
      message = "NO DEVICE - make sure a valid controller is connected, that the correct baudrate is defined in config.json and ensure the NOVA LCT is not running on the host system \nThis can also mean that you don't run the tool as administrator"
      exit_code = CRITICAL
      logger.info ("EXIT CODE: {}, {}".format(exit_code, message))
      end_time = time.time()
      await icinga_output(message, exit_code, reader, writer)
   
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
         await icinga_output(message, exit_code, reader, writer)         
      # -------------------------------------
      # RETRIEVE PARAMETERS FROM SENDER CARDS
      # -------------------------------------
      receiver_card_found = True
      no_of_receiver_cards = 0
      status[serial_port]["receiverCard"]={}
      display_on = True
      
      while (receiver_card_found):
         try:
            logger.info("=============================================================================================================================================")
            logger.info ("Connecting to receiver number: {}".format(no_of_receiver_cards+1))    
            if (not get_receiver_connected(serial_port)):  
               logger.info("Receiver card not connected.")
               break
            # ---------------------------------------
            # RETRIEVE PARAMETERS FROM RECEIVER CARDS
            # ---------------------------------------
            get_receiver_card_model(serial_port) #not necessary 
            get_receiver_card_firmware(serial_port) #not necessary 
            #################################################################################################
            number_of_modules, modules_ok = get_module_status(serial_port,  modules_ok) #required
            #################################################################################################
            no_of_receiver_cards = no_of_receiver_cards+1
      ##############################################################################################
         except Exception as e:
            message = e
            exit_code = UNKNOWN
            await icinga_output(message, exit_code, reader, writer)
            
      ser.close() #closing 
      i += 1

      #UPDATE INDEPENDANT CHECK DO NOT WIRTE TO STATUS.JSON FILE @
      # write_data(STATUS_FILE, status, LOGGER_NAME) # This could go to the end to 
      
      if (False in [value['module_status'] for value in module_status_info.values()]): #checking if a status does not return True
         msg = ""
         for receiver in module_status_info:
            module_status = module_status_info[receiver]['module_status']
            detected_modules = module_status_info[receiver]['detected_modules']
            if module_status is False:               
               expected_modules = config['modules']
               msg += f"ERROR IN ONE OR MORE MODULES - {expected_modules} EXPECTED, {detected_modules} FOUND, RECEIVER_NR {receiver} \n"         
         message = msg
         exit_code = CRITICAL # Should this be CRITICAL? #MODULE_ERROR
      #TODO ADD BLOCK FAULT AS WARNING
      else:
         message = f"ALL MODULES OK"
         exit_code = GOOD

      logger.info ("EXIT CODE: {}, {}".format(exit_code, message))
      
      await icinga_output(message, exit_code, reader, writer)
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

#################################################################################################
def get_module_status(port,  modules_ok):
#-----------------------------------------------------------------
   global no_of_receiver_cards
   global number_of_modules
   logger = logging.getLogger(LOGGER_NAME)
   logger.info("Getting module status")
   check_module_status [8] = no_of_receiver_cards
   data_groups = 4
   data_length = number_of_modules * (22+2*data_groups)
   print (data_length)
   first_byte = data_length & 0xFF00
   second_byte = data_length & 0x00FF
   print (first_byte, second_byte)
   check_module_status [16] = second_byte
   check_module_status [17] = first_byte
   element_length = 22 + (data_groups*2)
   print (element_length)
   # Here we must adjust length of data to be read (L) for NUMBER OF MODULES (N) and for DATA GROUPS PER MODULE (DG) according to the formula:
   # L = N * (22+2*DG)
   # Assumption for now is that N=4 (this value may be stored in config.json) and DG=1. Therefore:
   # L = 4 * (22+2*1) = 4 * (24) = 96 = 0x60 --> check_module_status [16] = 96
   check_module_status_send = methods.checksum(check_module_status)
   logger.debug("Sending command: "+' '.join('{:02X}'.format(a) for a in check_module_status_send))
   ser.write(check_module_status_send)
   time.sleep(sleep_time)
   modules_ok = True
   # ------------------------------------------------------------------------------------------------
   # Read length of payload data received - payload will contain info for all N modules.
   # First byte (X0)represents LED module status (xFF=NORMAL; 0x00=PROBLEM)
   # (X1) to (X21) represents other data (such as power supply voltage, temperature and runtime of module?)
   # (X22) and (X23) represent cable detection --> These should both be 0 - any other value means an error
   # 
   # ------------------------------------------------------------------------------------------------
   if ser.inWaiting()>0:
         response = ser.read(size=ser.inWaiting())
         rx_data = list (response)
         logger.debug("Received data: "+' '.join('{:02X}'.format(a) for a in rx_data))
         #number_of_modules = int(rx_data[16]/4)
         #logger.info ("Total amount of modules: {}".format(number_of_modules))
         status[port]["receiverCard"][no_of_receiver_cards]["module"]={}
         if check_response(rx_data):
            # Read X0-X23 bytes for each module expected
            # First, read the X0 byte for LED module status
            # Next, check flat cable data in bytes X22 and X23.
            # The Data Groups consist of 2 bytes (16 bits). Each bit is a Data Flag
            for j in range (int(number_of_modules)):
               status[port]["receiverCard"][no_of_receiver_cards]["module"][j]={}
               element = rx_data[18+j*element_length:(18+j*element_length)+element_length]
               #print("MODULE STATUS: {:02X}",hex(element))
               logger.debug("MODULE STATUS: "+' '.join('{:02X}'.format(a) for a in element))
               #TODO assign the values to variables0xFF = OK etc.
               if (element[0]==0xFF):
                  module_sts= "OK"
                  modules_ok = modules_ok and True
               elif (element[0]==0x00):
                  module_sts = "Error or no module available"
                  modules_ok = modules_ok and False
               else:
                  module_sts = "Unkown module state"
                  modules_ok = modules_ok and True
                  
               if ((element[22] & 0xF) != 0) | ((element[24] & 0xF) != 0) | ((element[26] & 0xF) != 0)| ((element[28] & 0xF) != 0):
                  block_fault = "FAULT"
               else:
                  block_fault = "OK"                  
               logger.info ("Module {module_index}: STATUS:{write_result} (0x{write_hex:02X})   BLOCK FAULTS:{block}".format(module_index=j+1,write_result=module_sts,write_hex=element[0],block=block_fault))#.format(j+1).format(module_write).format(element[0]).format(module_read).format(element[1]))
               status[port]["receiverCard"][no_of_receiver_cards]["module"][j]=module_sts
         else:
            modules_ok = modules_ok and False
            status[port]["receiverCard"][no_of_receiver_cards]["module"]='N/A'
   else:
         logger.warning ("No data available at the input buffer")    
         number_of_modules = 0
         modules_ok = modules_ok and False
         module_status="N/A"    
         status[port]["receiverCard"][no_of_receiver_cards]["module"]="N/A"
   return (number_of_modules,modules_ok)
#################################################################################################
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
if __name__ == "__main__":
   try:      
      asyncio.run(communicate_with_server())
   except KeyboardInterrupt:
      logger.info("Client shut down manually.")
      sys.exit(UNKNOWN)
   except Exception as e:
      logger.exception(f"Client encountered an error: {e}")
      sys.exit(UNKNOWN)
      
      