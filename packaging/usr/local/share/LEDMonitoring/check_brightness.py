from base_monitoring import *
check_value = {
   WARNING: ((10,30),(85, 90)),
   CRITICAL: ((0,10), (90, 100)),
}

async def main(reader, writer):
   global sleep_time
   global flash_wait_time
   global status 
   global ser
   global last_updated
   global data
   global logger
   global config
   module_status_info = {}
   exit_code = UNKNOWN
   exit_codes = []
   output = []   

   initialize_program()
   ser = methods.setupSerialPort(config["baudrate"],LOGGER_NAME) # Initialise serial port
   device_found, valid_ports = search_devices(ser, sleep_time, status)
   start_time = time.time()
   #Validate device found on player
   if (device_found == 0 ):
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
         
      #retrieve and unpack brightness from receiver card
      message, exit_code = get_display_brightness(port=ser.port) 
      output.append(message)
      exit_codes.append(exit_code)
      ser.close() #closing 
      logger.info("Writing to JSON file")
      logger.info("{} closed".format(ser.is_open)) # remove at production?
      # -------------------------------------------------------------
      # TO DO
      # Include checks for brightness >0. This should be a WARNING.
      # -------------------------------------------------------------
      logger.info ("EXIT CODE: {}, {}".format(exit_code, message))
   await icinga_output(output, exit_codes, reader, writer)
    
def get_display_brightness(port):
# ---------------------------------------------------------------------------------------
# SCREEN BRIGHTNESS SETTINGS
# This needs to be on a per receiver card basis or global?
# ---------------------------------------------------------------------------------------
   logger = logging.getLogger(LOGGER_NAME)
   logger.info("Getting current screen brightness...")
   display_brightness_send = methods.checksum(display_brightness)
   logger.debug("Sending command: "+' '.join('{:02X}'.format(a) for a in display_brightness_send))
   ser.write (display_brightness_send)
   time.sleep (sleep_time)
   if ser.inWaiting()>0:
      response = ser.read(size=ser.inWaiting())
      rx_data = list(response)
      logger.debug("Received data: "+' '.join('{:02X}'.format(a) for a in rx_data))
      if check_response(rx_data):
         brightness = rx_data[18]
         brightness_pc = round(100*brightness/255)
         logger.info("Brightness Level: "+ str(brightness))
         logger.info("Global Brightness: {}% ".format(brightness_pc))
         status[port]["brightnessLevelPC"] = brightness_pc
         status[port]["brightnessLevel"] = brightness
      else:
         status[port]["brightnessLevelPC"] = "N/A"
         status[port]["brightnessLevel"] = "N/A"
   else:
         logger.warning("No data available at the input buffer")
         status[port]["brightnessLevelPC"] = "N/A"
         status[port]["brightnessLevel"] = "N/A"
   return status[port]["brightnessLevelPC"]

if __name__ == "__main__":   
   asyncio.run(communicate_with_server(main, "CHECK_BRIGHTNESS"))
