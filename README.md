# 5_eyes_monitoring
-------------------
LED Display Status
-------------------
Suite of tools which allows to:
- retrieve information (via the Novastar serial protocol 1.9.3 over USB) from Novastar sender cards and receiver cards which are connected to them
- manually control display parameters via Novastar sender cards
- automatically control display parameters via Novastar sender cards with a state machine and systemctl timers and services
- log all activity
- determine a displays operating status or health by smartly analysing information retrieved from the sender card(s)
- integration with other monitoring agents (Icinga) and Network Mangagement Systems

USAGE:
Windows: python display_status.py & echo %errorlevel%
Linux: (sudo) python display_status.py ;echo $?

-------------
REVISIONS
-------------
v1.0.5
- increased timeout from 0.5s to 0.6s (in config.json) to ensure consistent response from sender card
- cleaned and tidied up code, removed commented/unused instructions
- check on presence of multifunction card now accommodates any valid card, not just MFN300(-B)

v1.0.4
- Included Flash module timeout in initial messages (value taken from config.json)
- Amended messaging for easier reading of logs
- Amended output messaging and included EXIT_CODE and message in log

v1.0.3
- Updated module flash checks to reflect ACK/STATUS bytes when a module flash is not detected. Does not necessarily indicate an error if Flash not present on module. Needs further checks and tests. 
- Included checks for when a MFN-300 is connected (use of ambient light sensor for example on MCTRL660 which has no ALS input). If MFN not present, will query ALS via sender directly.
- Included number of expected/found sender and receiver cards in output message

-------------
TO DO
-------------
- (DONE) - Include number of expected/found sender (DONE) and receiver cards (DONE) and modules
- Append text to output message string when multiple anomalies found
- Include overall output (EXIT_CODE and message string) into status.json file
- Include scenario for when modules connected to several sender output ports (e.g. logo boxes)
- display control scripts
    - auto-brightness settings
    - display on/off
    - testing on/off
    - brightness setting (manual)
- EDID: interpret returned data; this may require additional packages.
- Define testing regime, criteria, methodology
- clear up code in methods.py
- include check on global brightness - this should be >0 (except at night time) so should raise a WARNING
- potentially compare global brightness vs ALS reading to ensure display is sufficiently bright
- find suitable name for application (LEDManager, NovaMan, other?) and amend where relevant

-------------
COMPATIBILITY
-------------
- Novastar sender cards:
    - MSD300/MCTRL300  - Baudrate: 115200 Bps (TESTED)
    - MSD600/MSD600/MCTRL600/MCTRL610 - Baudrate: 1048576 Bps (TESTED)
    - MCTRL500 - Baudrate: 115200 Bps (TESTED)

- Novastar receiver cards:
    - A5s Plus (TESTED)
    - A4s (NOT TESTED)
    - A5s (TESTED)
    - A7s (NOT TESTED)
    - A8s (NOT TESTED)
    - A9s (NOT TESTED)
    - A10s (NOT TESTED)
    - MRV 366/ MRV 316 (NOT TESTED)
    - MRV 328 (NOT TESTED)
    - MRV 308 (NOT TESTED)

- Novastar multifunction cards:
    - MFN-300(B) (TESTED)

Please note that for certain parameters and features, i.e. the Module Flash and the Ribbon Cable checks, the LED cabinets must have the adequate hardware and the receiver the adequate firmware.
For legacy equipment, this is not guaranteed and the result may be unkown. The other parameters are generally valid.

----------------------------
MINIMUM REQUIREMENTS (SUITE)
----------------------------
- Python 3.8.10
- PySerial 3.5
- Novastar sender card (connected via USB)
- Access to USB (/dev/ttyUSBX) and COM (COMX) ports 

------------
INSTALLATION
------------
1 - Install required packages:
    a) PySerial 3.5: https://pypi.org/project/pyserial/
        pip install pyserial

        Or:
        - Download the archive from http://pypi.python.org/pypi/pyserial. Unpack the archive, enter the pyserial-x.y directory and run:
        - python3 setup.py install
Workaround - use apt in linux sudo apt install python3-serial
-----
FILES
-----
- README.txt
    This file. Overview of the software, description of the features, functionality and operation.
- activity.log
    Logs activity whereby the state of the display is changed (e.g. display ON/OFF).
- debug.log
    Logs information useful for troubleshooting, debugging and testing. Mainly records serial commands sent and the corresponding data received.
- config.json
    JSON file used to store application configuration data such as:
        - version: current version of the suite
        - baudrate: used for serial communications (different sender cards used different baudrate)
        - sleep time: used to pause between transmission/reception of serial commands 
- display_status.py
    PYTHON script that interrogates all identified compatible Novastar sender and receiver cards. Retrieves a set of parameters useful for determining the status of a display.
- methods.py
    PYTHON script which contains additional functions used in the various scripts.
- status.json
    JSON file summarising the information retrieve from the Novsatar sender and receiver cards.


Additionally, the following files may be used for managing the display:
- set_display_on.py
- set_display_off.py

-----------
PERMISSIONS
-----------


-------
LOGGING
-------
Please note that debug.log and activity.log use 7-day log rotation, therefore up to 7 files can be present in folder.


-------
TESTING
-------


---------------------------------------------------------------------
AVAILABLE DISPLAY PARAMETERS MONITORED AND/OR CONTROLLED (READ/WRITE)
---------------------------------------------------------------------
_________________________________________________________________________________________________________________________________________________________________________________________   
            NAME                |       DEVICE      |               DESCRIPTION                                     |        READ        |         WRITE      |        IMPLEMENTED (Y/N)
_________________________________________________________________________________________________________________________________________________________________________________________
TEMPERATURE VALID (RECEIVER CARD)   RECEIVER CARD   This byte is for the temperature sensor on the receiving card.              X                   O                       Y
                                                    The highest bit is used to indicate valid temperature data. 
                                                    1 for data valid and 0 for data invalid.
                                                    The lowest bit is for negative/positive temperature. 
                                                    0 for positive and 1 for negative.
TEMPERATURE (RECEIVER CARD)         RECEIVER CARD   Temperature output by the sensor on the receiving card. Unit: 0.5C          X                   O                       Y
VOLTAGE (RECEIVER CARD)             RECEIVER CARD   This byte is for power supply voltage of the receiving card.                X                   O                       Y
                                                    The highest bit is for valid data. 1 for valid and 0 for invalid.
                                                    The rest 7 bits are for the voltage value. Value range: 0~127
                                                    Unit: 0.1V
MONITORING CARD PRESENT             RECEIVER CARD   This byte is used to indicate whether the monitor card is existed. 
                                                    0xff for monitor card existing and other values for not existing.           X                   O                       Y
MONITORING CARD MODEL               RECEIVER CARD   Module information of the monitor card.                                     X                   O                       N
MONITORING CARD FIRMWARE VERSION    RECEIVER CARD   Firmware version of the monitor card                                        X                   O                       N
MONITORING CARD TEMPERATURE VALID   RECEIVER CARD   This byte is for the temperature sensor on the monitor card.                X                   O                       N
                                                    The highest bit is used to indicate valid temperature data. 
                                                    1 for data valid and 0 for data invalid.
                                                    The lowest bit is for negative/positive temperature. 
                                                    0 for positive and 1 for negative.
MONITOR CARD SMOKE SENSOR PRESENT   RECEIVER CARD   This byte is for the smoke sensor on the monitor card.                      X                   O                       N
                                                    The lowest bit is used to indicate whether smoke is detected. 
                                                    0 for no smoke detected and 1 for smoke detected.
MONITOR CARD FAN SPEED 0            RECEIVER CARD   The speed of Fan 1 monitored by the monitor card.                           X                   O                       N
                                                    The highest bit is for data validation. 
                                                    The rest 7 bits are for the speed, ranging from 0 to 127 
                                                    with unit 50rpm.
MONITOR CARD FAN SPEED 1            RECEIVER CARD   The speed of Fan 2 monitored by the monitor card.                           X                   O                       N
                                                    The highest bit is for data validation. 
                                                    The rest 7 bits are for the speed, ranging from 0 to 127 
                                                    with unit 50rpm.
MONITOR CARD FAN SPEED 2            RECEIVER CARD   The speed of Fan 3 monitored by the monitor card.                           X                   O                       N
                                                    The highest bit is for data validation. 
                                                    The rest 7 bits are for the speed, ranging from 0 to 127 
                                                    with unit 50rpm.
MONITOR CARD FAN SPEED 3            RECEIVER CARD   The speed of Fan 4 monitored by the monitor card.                           X                   O                       N
                                                    The highest bit is for data validation. 
                                                    The rest 7 bits are for the speed, ranging from 0 to 127 
                                                    with unit 50rpm.
MONITOR CARD VOLTAGE 0              RECEIVER CARD   Power supply voltage of the monitor card. The highest                       X                   O                       N
                                                    bit is for data validation. The rest 7 bits are for the 
                                                    voltage value, ranging from 0 to 127 with unit 0.1V.
MONITOR CARD VOLTAGE 1              RECEIVER CARD   The Voltage 1 monitored by the monitor card. The highest                    X                   O                       N
                                                    bit is for data validation. The rest 7 bits are for the 
                                                    voltage value, ranging from 0 to 127 with unit 0.1V.
MONITOR CARD VOLTAGE 2              RECEIVER CARD   The Voltage 2 monitored by the monitor card. The highest                    X                   O                       N
                                                    bit is for data validation. The rest 7 bits are for the 
                                                    voltage value, ranging from 0 to 127 with unit 0.1V.
MONITOR CARD VOLTAGE 3              RECEIVER CARD   The Voltage 3 monitored by the monitor card. The highest                    X                   O                       N
                                                    bit is for data validation. The rest 7 bits are for the 
                                                    voltage value, ranging from 0 to 127 with unit 0.1V.
MONITOR CARD VOLTAGE 4              RECEIVER CARD   The Voltage 4 monitored by the monitor card. The highest                    X                   O                       N
                                                    bit is for data validation. The rest 7 bits are for the 
                                                    voltage value, ranging from 0 to 127 with unit 0.1V.
MONITOR CARD VOLTAGE 5              RECEIVER CARD   The Voltage 5 monitored by the monitor card. The highest                    X                   O                       N
                                                    bit is for data validation. The rest 7 bits are for the 
                                                    voltage value, ranging from 0 to 127 with unit 0.1V.
MONITOR CARD VOLTAGE 6              RECEIVER CARD   The Voltage 6 monitored by the monitor card. The highest                    X                   O                       N
                                                    bit is for data validation. The rest 7 bits are for the 
                                                    voltage value, ranging from 0 to 127 with unit 0.1V.
MONITOR CARD VOLTAGE 7              RECEIVER CARD   The Voltage 7 monitored by the monitor card. The highest                    X                   O                       N
                                                    bit is for data validation. The rest 7 bits are for the 
                                                    voltage value, ranging from 0 to 127 with unit 0.1V.
MONITOR CARD VOLTAGE 8              RECEIVER CARD   The Voltage 8 monitored by the monitor card. The highest                    X                   O                       N
                                                    bit is for data validation. The rest 7 bits are for the 
                                                    voltage value, ranging from 0 to 127 with unit 0.1V.
MONITOR CARD STATUS (DOOR)          RECEIVER CARD   This byte is for cabinet door opening checking.                             X                   O                       N 
                                                    Bit0 is for the first cabinet and Bit1 is for the second 
                                                    cabinet. 0 for door closed and 1 for door open.
DVI SIGNAL VALID                    SENDER CARD     This byte is for valid DVI signal.                                          X                   O                       Y
                                                    01 : DVI signal is good
                                                    00 : No DVI signal
POWER SUPPLY 1                      FUNCTION CARD   Status of the 1st power supply switch (0=ON; 1=OFF)                         X                   X                       N
POWER SUPPLY 2                      FUNCTION CARD   Status of the 2nd power supply switch (0=ON; 1=OFF)                         X                   X                       N
POWER SUPPLY 3                      FUNCTION CARD   Status of the 3rd power supply switch (0=ON; 1=OFF)                         X                   X                       N
POWER SUPPLY 4                      FUNCTION CARD   Status of the 4th power supply switch (0=ON; 1=OFF)                         X                   X                       N
POWER SUPPLY 5                      FUNCTION CARD   Status of the 5th power supply switch (0=ON; 1=OFF)                         X                   X                       N
POWER SUPPLY 6                      FUNCTION CARD   Status of the 6th power supply switch (0=ON; 1=OFF)                         X                   X                       N
POWER SUPPLY 7                      FUNCTION CARD   Status of the 7th power supply switch (0=ON; 1=OFF)                         X                   X                       N
POWER SUPPLY 8                      FUNCTION CARD   Status of the 8th power supply switch (0=ON; 1=OFF)                         X                   X                       N
BRIGHTNESS ADJUST (GLOBAL)          RECEIVER CARD   The overall brightness                                                      X                   X                       Y
BRIGHTNESS ADJUST (RED)             RECEIVER CARD   Brightness of the red component                                             X                   X                       Y
BRIGHTNESS ADJUST (GREEN)           RECEIVER CARD   Brightness of the green component                                           X                   X                       Y
BRIGHTNESS ADJUST (BLUE)            RECEIVER CARD   Brightness of the blue component                                            X                   X                       Y
BRIGHTNESS ADJUST (V-RED)           RECEIVER CARD   Brightness of the virtualred component                                      X                   X                       Y
FACTORY RESET                       SENDER CARD     Writing any value to this register will activate                            X                   X                       N 
                                                    the operation of reset all sending cards / controllers 
                                                    to factory setting.
GAMMA VALUE                         RECEIVER CARD   Gamma value. The Gamma value is one of the parameters                       X                   X                       Y
                                                    in the gamma transform equation. It is stored in the 
                                                    receiving card.                                                                 
GAMMA TABLE                         RECEIVER CARD   Gamma table is used for data transform. It is based on                      X                   X                       Y
                                                    look-up table method. When the receiving card receives 
                                                    the video data from sending card, it will finish the 
                                                    transformation through look-up table method.
FPGA FIRMWARE VERSION               SENDER CARD     FPGA program version. The version number has four parts.                    X                   X                       Y
                                                    Each part is represent by one byte.
RECEIVER CARD MODEL ID              RECEIVER CARD   Different type of receiving cards have their own Model ID.                  X                   O                       Y
SENDER CARD MODEL ID                SENDER CARD     Sending Cards / Controllers Model ID                                        X                   O                       Y
FUNCTION CARD MODEL ID              FUNCTION CARD   Function card Model ID                                                      X                   O                       N
NS060 ALS READING                   SENDER CARD     Low 8 bits of Environment brightness. The unit of the data is 2 Lux         X                   O                       Y    
                                                    High 8 bits of environment brightness. The highest bit is for 
                                                    data validation. And 1 means the data is valid.
ENABLE/DISABLE ALS                  SENDER CARD     Set this byte as 0x7D to enable stand-alone mode of the light sensor.       X                   X                       Y
                                                    To disable stand-alone mode, set this byte as 0xFF.
AUTO-BRIGHT (ALS QUANTITY)          SENDER CARD     The maximum value could be 8. As one controller, such as MCTRL300,          X                   X                       Y
                                                    can have one light sensor only. So if the light sensor is 
                                                    connected to a controller, set this value as 1. 
                                                    If function card is used, this value could be up to 8.
AUTO-BRIGHT (ALS MAX LUX)           SENDER CARD     Threshold for maximum environment brightness (LOW, HIGH BYTES)              X                   X                       Y
AUTO-BRIGHT (ALS MIN LUX)           SENDER CARD     Threshold for minimum environment brightness (LOW, HIGH BYTES)              X                   X                       Y
AUTO-BRIGHT (ALS MAX BRIGHT)        SENDER CARD     Brightness corresponding to MAX LUX                                         X                   X                       Y
AUTO-BRIGHT (ALS MIN BRIGHT)        SENDER CARD     Brightness corresponding to MIN LUX                                         X                   X                       Y
AUTO-BRIGHT (SEGMENTS)              SENDER CARD     Number of intermediate steps between MIN and MAX BRIGHT                     X                   X                       Y
AUTO-BRIGHT (ALS POSITION S/C)      SENDER CARD     If the light sensor is connected to a sending card/ sending box             X                   X                       Y
                                                    (controller), set this value as 0x01; otherwise, if the light sensor 
                                                    is connected with a function card, set this value as 0x00
AUTO-BRIGHT (ALS PORT ADDRESS S/C)  SENDER CARD     The RJ45 port of a controller/ sending card that is connected with          X                   X                       Y 
                                                    the function card. (If the light sensor is connected to a function card. 
                                                    To locate the light sensor, the system needs to know the function card 
                                                    is connected with which RJ45 port of the controller.)
AUTO-BRIGHT (FUNC. CARD POSITION)   SENDER CARD     Index of the function card. (LOW, HIGH BYTES)                               X                   X                       Y
AUTO-BRIGHT (ALS PORT ADDRESS F/C)  SENDER CARD     If the light sensor is connected with the first port of the function        X                   X                       Y 
                                                    card, the address is 0; if connected with the second port, the address 
                                                    is 1...if the light sensor is connected with the forth port, 
                                                    the address is 3.
RECEIVER CARD MODEL ID              RECEIVER CARD   A valid Model ID is a value other than 00.                                  X                   O                       Y
RECEIVER CARD FIRMWARE VERSION      RECEIVER CARD   A valid Firmware version is a value other than 00 00 00 00                  X                   O                       Y
REDUNDANCY STATUS (S/C)             SENDER CARD     Bit[1:0] is used to represent the redundant status of the sending unit      X                   O                       N 
                                                    output port 1. If Bit[1:0] 2’b is 10 (Bit[1]=1, Bit[0]=0), output port 1 
                                                    of the sending unit is working as redundant. For values other than 10, 
                                                    the port is not working as redundant. Bit[3:2] is used for output port 2;
                                                    Bit[5:4] is for output port 3; Bit[7:6] is for output port 4. Values for 
                                                    Bit[3:2], Bit [5:4] and Bit[7:6] means the same as Bit[1:0].
REDUNDANCY STATUS (R/C)             RECEIVER CARD   Try to read the receiving card Model ID with the address based on the        X                   O                       N 
                                                    redundant output port of the sending unit. If the Model ID can be read 
                                                    back, it means the corresponding receiving card is working in the 
                                                    redundant line.
EDID REGISTER                       SENDER CARD     To set the resolution and refresh rate of sending card, the specified        X                   X                      N 
                                                    content should be written into EDID register. This document describes 
                                                    the basic 128-byte data structure "EDID 1.3".
SELF TEST MODE (RED)                RECEIVER CARD   Display a full, solid RED image                                              X                   X                      N
SELF TEST MODE (GREEN)              RECEIVER CARD   Display a full, solid GREEN image                                            X                   X                      N
SELF TEST MODE (BLUE)               RECEIVER CARD   Display a full, solid BLUE image                                             X                   X                      N
SELF TEST MODE (WHITE)              RECEIVER CARD   Display a full, solid WHITE image                                            X                   X                      N
SELF TEST MODE (HORIZONTAL LINES)   RECEIVER CARD   Display HORIZONTAL lines                                                     X                   X                      N
SELF TEST MODE (VERTICAL LINES)     RECEIVER CARD   Display VERTICAL lines                                                       X                   X                      N
SELF TEST MODE (DIAGONAL LINES)     RECEIVER CARD   Display DIAGONAL lines                                                       X                   X                      N
SELF TEST MODE (GREYSCALE)          RECEIVER CARD   Display GREYSCALE gradient image                                             X                   X                      N
SELF TEST MODE (ALL TESTS)          RECEIVER CARD   Execute all tests in loop                                                    X                   X                      N
KILL MODE                           RECEIVER CARD   0xff: black display 0x00:normal display                                      X                   X                      Y
LOCK MODE                           RECEIVER CARD   0xff: lock display 0x00:normal display                                       X                   X                      Y
CALIBRATION CORRECTION              RECEIVER CARD   Bit[0]: calibration on/off’1’, calibration on; ‘0’, calibration off          X                   X                      N 
                                                    Bit[1]: calibration type ‘1’, brightness calibration; ‘0’, color 
                                                    calibration
                                                    Bit[7:2]: Reserved, “000000”
                                                    Example:
                                                    0x00: calibration off
                                                    0x03: brightness calibration on 
                                                    0x01: color calibration on
RECONNECT SENDER-RECEIVER           S/R CARD        Acknowledge data is not equal to zero means in connected status.            O                    X                      Y 
PARAMETER STORE                     RECEIVER CARD   Write down any value(such as 0x11) into the address to finish               O                    X                      N TODO 
                                                    the parameter store operation
CABINET SIZE (WIDTH)                SENDER CARD     The width of per cabinet. Read width and height after rcfg file is saved.   X                   O                       Y
CABINET SIZE (HEIGHT)               SENDER CARD     The height of per cabinet.Read width and height after rcfg file is saved.   X                   O                       Y
RIBBON CABLE                        SCAN CARD       Ribbon cable detection must work together with MON300 mionitoring card      X                   O                       Y
INPUT SOURCE STATUS                 SENDER CARD     Each Bit expressed the Type of Input Source. “1” means input source 
                                                    signal is valid, “0” expressed input source is invalid. Total 1 Byte.       X                   O                       Y 
                                                    Bit[0]:3G-SDI
                                                    Bit[1]:HDMI
                                                    Bit[2]:DVI1
                                                    Bit[3]:DVI2
                                                    Bit[4]:DVI3
                                                    Bit[5]:DVI4
                                                    Bit[6]:DP
                                                    Bit[6]:Reserved
INPUT SOURCE SELECTION (STATUS)     SENDER CARD     The status of the switching input source is automatically or manually.      X                   O                       Y
                                                    “0x5A” means manually, other means automatically
INPUT SOURCE SELECTION (MANUAL)     SENDER CARD     Select Input Source Manually Write below values can change the type         X                   Y                       Y
                                                    of Input source. 
                                                    DVI:0x58; 
                                                    Dual_DVI:0x61 
                                                    HDMI:0x05
                                                    3G-SDI: 0x01; 
                                                    DP:0x5F 
                                                    HDMI1.4:0x5A
MODULE FLASH CHECK (START)          SCAN CARD
MODULE FLASH CHECK (READ RESULT)    SCAN CARD       After Check, Send the Read Command to the offset address 0x3010,            X                   O                       Y
                                                    can read back the result. The data length depend on the flash 
                                                    topology of actual receiving card setting
**********************************************************************************************************************************************************
END.
