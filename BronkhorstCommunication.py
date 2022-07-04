# -*- coding: utf-8 -*-
"""
Created on Wed Apr 27 10:19:14 2022

@author: Administrator
"""

import serial
import serial.tools.list_ports
import numpy as np
import time
import struct

class ELFLOW:
    def __init__(self, comm_port=None, timeout=2, verbose=False):

        self.sp = None
        self.verbose = verbose
        
        if comm_port is not None:
            self.comm_port = comm_port
        else:
            lpis = list(serial.tools.list_ports.comports())     # lpi = ListPortInfo object
            # for lpi in lpis:
                # self.comm_port = lpi[0]          # here we end up using the last one found
                # print('found', lpi[0], '   description:',lpi[1])
                
            self.comm_port = lpis[0][0]    
            self.sp = serial.Serial(self.comm_port, baudrate=38400, bytesize=serial.EIGHTBITS, 
                                        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                                        timeout=timeout)        # open serial port

        if self.verbose:
            print('connected as "',self.sp.name,'"',sep='')             # determine and mention which port was really used

        if self.verbose:
            print('attempting to establish communications with')
            
        # device_name = self.send_cmd(':0703047163716300\r')
        
        # if self.verbose:
            # print(device_name)
        


    def __repr__(self): 
        """ return a printable version: not a useful function """
        return self.id.decode()

    def __str__(self):
        """ return a string representation: as useless as __repr__() """
        return self.__repr__()

    def __bool__(self):
        """ boolean test if valid - assumes valid if the serial port reports is_open """
        if type(self.sp) != type(None):
            return self.sp.is_open()
        return False

    def __enter__(self):
        """ no special processing after __init__() """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """ same as __del__() """
        self.__del__()

    def __del__(self):
        """ close up """
        if type(self.sp) != type(None):
            self.sp = None

    def send_cmd(self, s):
        """ Send ASCII command via serial port.
            Add carriage return to every command send.
            read_until() returns bytes when available and reads until ‘\r’ is found
            The return string contains '\r' at the end which is removed from the function return.
        """
        c = s + "\n"

        cmd = c.encode()
        nw = self.sp.write(cmd)
        if nw != len(cmd):
            self.sp.flush()  # nominally, waits until all data is written
        if self.verbose:
            print('send_cmd("',s,'")')
            
        c_r = self.sp.read_until().decode()
        if self.verbose:
            print(' -->', c_r)
        return c_r

    def flush(self):
        self.sp.flush()

    def close(self):
        self.sp.flush()
        self.sp.close()


#=====================================================================

    # def configure(self, function='CURR'):
    #     '''
    #     This command configures the instrument for "one shot" measurement
    #     each subsequent read command will then trigger a single measurement and acquire the reading.
    #     Available functions: CURRent
    #     '''
    #     self.send_cmd("CONF:" + function)

    # def read(self):
    #     '''
    #     This command is used to trigger and acquire readings.
    #     The number of readings depends on how the trigger model is configured.
    #     When this command is sent, the following commands are executed in order: INIT, FETC
    #     '''
    #     r = self.send_cmd("READ?")
    #     pos = r.find("A")
    #     if pos != -1:
    #         return float(r[:pos])
    #     else:
    #         return 999
        
        
    def measure(self):
        '''
        This command combines all other signal oriented measurement commands to perform
        a "one shot" measurement and acquire the reading.
        When this command is sent, the following commands are executed in order: 
        serial,usertag,measure,capacity,capacityunit,fluidtype
        '''
        r = self.send_cmd(":1A0304F1EC7163006D71660001AE0120CF014DF0017F077101710A\r")
        serial_no = bytearray.fromhex(r[13:33]).decode()
        usertag = bytearray.fromhex(r[39:55]).decode()
        measure = int(r[59:63],16)*0.7/32000
        cap = struct.unpack('!f',bytes.fromhex(r[65:73]))[0]
        cap_unit = bytearray.fromhex(r[77:91]).decode()
        fluid = bytearray.fromhex(r[95:115]).decode()
        return serial_no,usertag,measure,cap,cap_unit,fluid
    
    def setpoint(self,setpoint):
        '''
        Sends a user defined setpoint for the MFC between 0 and 100%.
        '''
        if setpoint <= 100:
            setpoint_hex = hex(int(32000*setpoint/100))[2:]
            sp = self.send_cmd(":0603010121"+setpoint_hex+"\r")
            return sp
        else:
            return
        
        
        
        
# def run(ifn, p, nt, nshot, interval):
    
#     tarr = np.zeros(nt)
#     result = np.zeros((nt, nshot))
    
#     print('Data run starting at ', time.ctime())
#     for i in range(nt):
        
#         tarr[i] = time.time()
        
#         try:
#             for j in range(nshot):
#                 result[i,j] = p.read()
#                 print(j, end=' ')
            
#             print('%i---I=%.2e'%(i, np.average(result[i])), end=' ')
#             np.save(ifn+'.npy', result)
#             np.save(ifn+'-tarr.npy',tarr)
            
#             print('waiting...')
#             for n in range(60*interval):
#                 time.sleep(1)
            
#         except KeyboardInterrupt:
#             print('Haulted due to ctrl-c')
#             break
#         except:
#             print('Some error occured...')
#             continue

#     p.close()
#     print('done at ', time.ctime())

#=====================================================================


# if __name__ == '__main__':
#     """ standalone """


#     with ELFLOW(verbose=False) as p:
#         print(p.measure())
        

    
    