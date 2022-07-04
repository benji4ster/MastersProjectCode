# -*- coding: utf-8 -*-
"""
Created on Mon Feb 28 11:14:40 2022

@author: benja
"""

import socket

class MaxiGauge:
    
    port = 8000
    host = "192.168.1.2" # server ip address - configurable using ethernet 
                         # configuration tool (note: format "xxx.xxx.x.y" where 
                         # x´s )
    
    # sel = selectors.DefaultSelector()
    
    def __init__(self, host=host, debug=False):
        
        self.debug = debug
        print("Looking for gauge server at", self.host, "\n", flush=True)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.connect((self.host, self.port))
        print("Successfully connected to gauge server!\n")
        # self.s.close()
        # self.s.bind((self.host, self.port)) # bind to port
        # self.s.listen() # wait for client connection
        # print("Listening for connection...")
        # self.s.setblocking(False)
        # self.sel.register(s, selectors.EVENT_READ, data=None) # register socket to monitor events with select
        # print(f"Listening on {(self.host, self.port)}")
        
        # while True:
        # conn, addr = s.accept()
        # print(f"Accepted connection from {addr}")
        # conn.close()
        # print("Goodbye")
        
        
        # try: 
        #     while True:
        #         events = self.sel.select(timeout=None) # blocks until there are sockets ready for I/O
        #         for key, mask in events:
        #             if key.data is None:
        #                 conn, addr = key.fileobj.accept()  # establish connection, should be ready to read
        #                 print(f"Accepted connection from {addr}")
        #                 conn.setblocking(False)
        #                 data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
        #                 events = selectors.EVENT_READ | selectors.EVENT_WRITE
        #                 self.sel.register(conn, events, data=data)
        #             else:
        #                 self.service_connection(key, mask)
        # except KeyboardInterrupt:
        #       print("Caught keyboard interrupt, exiting")
        self.logfilename = 'measurement-data.txt'
        

    def pressures(self):
        return [self.pressure(i+1) for i in range(6)]

    def pressure(self, sensor):
        # self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.s.connect((self.host, self.port))
        if sensor < 1 or sensor > 6: 
            raise MaxiGaugeError("Sensor can only be between 1 and 6. You choose " + str(sensor))
        reading = self.send(b"PR%d" % sensor, 1)  ## reading will have the form x,x.xxxEsx <CR><LF> (see p.88)
        # self.s.close()
        try:
            r = reading[0].split(',')
            status = int(r[0])
            pressure = float(r[-1])
        except:
            raise MaxiGaugeError("Problem interpreting the returned line:\n%s" % reading)
        return PressureReading(sensor, status, pressure)
    
    def send(self, mnemonic, numEnquiries=0):
        self.write(mnemonic+LINE_TERMINATION)
        self.getACKorNAK()
        response = []
        for i in range(numEnquiries):
            self.enquire()
            response.append(self.read())
        return response

    def debugMessage(self, message):
        if self.debug:
            print(repr(message))
    
    def write(self, what):
        self.debugMessage(what)
        self.s.sendall(what)
        
    def enquire(self):
        self.write(C["ENQ"])
        
    def read(self):
        data = ""
        while True:
            x = self.s.recv(1024)
            self.debugMessage(x)
            data += str(x, "utf-8")
            if len(data) > 1 and data[-2:] == str(LINE_TERMINATION,"utf-8"):
                break
        return data[:-len(str(LINE_TERMINATION,"utf-8"))]
        
    def getACKorNAK(self):
        returncode = self.read()
        self.debugMessage(returncode)
        # if acknowledgement ACK is not received
        if len(returncode) < 3:
            self.debugMessage("Only received a line termination from gauge, was expecting ACK or NAK.")
        if len(returncode) > 2 and returncode[-3] == C["NAK"]:
            self.enquire()
            returnedError = self.read()
            error = str(returnedError).split(",", 1)
            print(repr(error))
            errmsg = {"System Error": ERR_CODES[0][int(error[0])], "Gauge Error": ERR_CODES[1][int(error[1])]}
            raise MaxiGaugeNAK(errmsg)
        if len(returncode) > 2 and returncode[-3] != b"ACK":
            self.debugMessage("Expecting ACK or NAK from gauge but neither were sent.")
        # otherwise:
        else: 
            return returncode[:-(len(LINE_TERMINATION)+1)]
    
    def disconnect(self):
        self.s.close()
        print("\n Connection safely terminated.")
    
            
class PressureReading(object):
    def __init__(self, id, status, pressure):
        if int(id) not in range(1,7):
            raise MaxiGaugeError("Pressure Gauge ID must be between 1-6")
        self.id = int(id)
        if int(status) not in PRESSURE_READING_STATUS.keys(): 
            raise MaxiGaugeError("The Pressure Status must be in the range %s" % PRESSURE_READING_STATUS.keys())
        self.status = int(status)
        self.pressure = float(pressure)

    def statusMsg(self):
        return PRESSURE_READING_STATUS[self.status]

    def __repr__(self):
        return "Gauge #%d: Status %d (%s), Pressure: %f mbar\n" % (self.id, self.status, self.statusMsg(), self.pressure)            
            
class MaxiGaugeError(Exception):
    pass

class MaxiGaugeNAK(MaxiGaugeError):
    pass


       
### ------- Control Symbols as defined on p. 81 of the english
###         manual for the Pfeiffer Vacuum TPG256A  -----------
C = { 
  'ETX': b"\x03", # End of Text (Ctrl-C)   Reset the interface
  'CR':  b"\x0D", # Carriage Return        Go to the beginning of line
  'LF':  b"\x0A", # Line Feed              Advance by one line
  'ENQ': b"\x05", # Enquiry                Request for data transmission
  'ACQ': b"\x06", # Acknowledge            Positive report signal
  'NAK': b"\x15", # Negative Acknowledge   Negative report signal
  'ESC': b"\x1b", # Escape
}

# LINE_TERMINATION=C['CR']+C['LF'] # CR, LF and CRLF are all possible (p.82)
LINE_TERMINATION=C["CR"]+C["LF"] # CR, LF and CRLF are all possible (p.82)

### Mnemonics as defined on p. 85
M = [
  'BAU', # Baud rate                           Baud rate                                    95
  'CAx', # Calibration factor Sensor x         Calibration factor sensor x (1 ... 6)        92
  'CID', # Measurement point names             Measurement point names                      88
  'DCB', # Display control Bargraph            Bargraph                                     89
  'DCC', # Display control Contrast            Display control contrast                     90
  'DCD', # Display control Digits              Display digits                               88
  'DCS', # Display control Screensave          Display control screensave                   90
  'DGS', # Degas                               Degas                                        93
  'ERR', # Error Status                        Error status                                 97
  'FIL', # Filter time constant                Filter time constant                         92
  'FSR', # Full scale range of linear sensors  Full scale range of linear sensors           93
  'LOC', # Parameter setup lock                Parameter setup lock                         91
  'NAD', # Node (device) address for RS485     Node (device) address for RS485              96
  'OFC', # Offset correction                   Offset correction                            93
  'OFC', # Offset correction                   Offset correction                            93
  'PNR', # Program number                      Program number                               98
  'PRx', # Status, Pressure sensor x (1 ... 6) Status, Pressure sensor x (1 ... 6)          88
  'PUC', # Underrange Ctrl                     Underrange control                           91
  'RSX', # Interface                           Interface                                    94
  'SAV', # Save default                        Save default                                 94
  'SCx', # Sensor control                      Sensor control                               87
  'SEN', # Sensor on/off                       Sensor on/off                                86
  'SPx', # Set Point Control Source for Relay xThreshold value setting, Allocation          90
  'SPS', # Set Point Status A,B,C,D,E,F        Set point status                             91
  'TAI', # Test program A/D Identify           Test A/D converter identification inputs    100
  'TAS', # Test program A/D Sensor             Test A/D converter measurement value inputs 100
  'TDI', # Display test                        Display test                                 98
  'TEE', # EEPROM test                         EEPROM test                                 100
  'TEP', # EPROM test                          EPROM test                                   99
  'TID', # Sensor identification               Sensor identification                       101
  'TKB', # Keyboard test                       Keyboard test                                99
  'TRA', # RAM test                            RAM test                                     99
  'UNI', # Unit of measurement (Display)       Unit of measurement (pressure)               89
  'WDT', # Watchdog and System Error Control   Watchdog and system error control           101
]
        
### Error codes as defined on p. 97
ERR_CODES = [
  {
        0: 'No error',
        1: 'Watchdog has responded',
        2: 'Task fail error',
        4: 'IDCX idle error',
        8: 'Stack overflow error',
       16: 'EPROM error',
       32: 'RAM error',
       64: 'EEPROM error',
      128: 'Key error',
     4096: 'Syntax error',
     8192: 'Inadmissible parameter',
    16384: 'No hardware',
    32768: 'Fatal error'
  } ,
  {
        0: 'No error',
        1: 'Sensor 1: Measurement error',
        2: 'Sensor 2: Measurement error',
        4: 'Sensor 3: Measurement error',
        8: 'Sensor 4: Measurement error',
       16: 'Sensor 5: Measurement error',
       32: 'Sensor 6: Measurement error',
      512: 'Sensor 1: Identification error',
     1024: 'Sensor 2: Identification error',
     2048: 'Sensor 3: Identification error',
     4096: 'Sensor 4: Identification error',
     8192: 'Sensor 5: Identification error',
    16384: 'Sensor 6: Identification error',
  }
]

### pressure status as defined on p.88
PRESSURE_READING_STATUS = {
  0: 'Measurement data okay',
  1: 'Underrange',
  2: 'Overrange',
  3: 'Sensor error',
  4: 'Sensor off',
  5: 'No sensor',
  6: 'Identification error'
}
            
            
            
            