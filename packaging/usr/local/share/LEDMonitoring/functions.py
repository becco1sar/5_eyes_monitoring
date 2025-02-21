def get_ambient_light_level_via_function_card(port):
# ---------------------------------------------------------------------------------------
# AMBIENT LIGHT LEVEL
# Device: Sending Card
# Base Address: 0x0200_0000H
# Data Length: 2H
# ---------------------------------------------------------------------------------------
   logger = logging.getLogger(LOGGER_NAME)
   logger.info("Refreshing function card register")
   refresh_function_send = methods.checksum(function_card_refresh_register)
   logger.debug("Sending command: "+' '.join('{:02X}'.format(a) for a in refresh_function_send))
   ser.write (refresh_function_send)
   time.sleep (sleep_time)
   if ser.inWaiting()>0:
      response = ser.read(size=ser.inWaiting())
      rx_data = list(response)
      logger.debug("Received data: "+' '.join('{:02X}'.format(a) for a in rx_data))
   else:
         logger.warning("No data available at the input buffer")
   logger.info("Getting ambient light level from function card")
   check_ALS_send = methods.checksum(check_ALS_function)
   logger.debug("Sending command: "+' '.join('{:02X}'.format(a) for a in check_ALS_send))
   ser.write (check_ALS_send)
   time.sleep (sleep_time)
   if ser.inWaiting()>0:
      response = ser.read(size=ser.inWaiting())
      rx_data = list(response)
      logger.debug("Received data: "+' '.join('{:02X}'.format(a) for a in rx_data))
      if check_response(rx_data):
         if (rx_data[20]&0x80==0x80):
            ambient_light_lux=rx_data[21]*(0xFFFF/0xFF)
         else:
            ambient_light_lux="Data invalid (0x{:02X})".format(int(rx_data[18]*(0xFFFF/0xFF)))
      else:
         ambient_light_lux="N/A"
   else:
         logger.warning("No data available at the input buffer")
         ambient_light_lux="N/A"
   status[port]["ambientLightLevel"] = ambient_light_lux
   logger.info("Ambient Light Level (lux): {} ".format(ambient_light_lux))    