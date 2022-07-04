# -*- coding: utf-8 -*-
"""
Created on Thu May 12 11:01:25 2022

@author: Administrator
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Mar  3 14:45:23 2022

@author: benja
"""

from PfeifferVacuumCommunication import MaxiGauge, MaxiGaugeError
from LeCroy_Scope import LeCroy_Scope, EXPANDED_TRACE_NAMES, WAVEDESC_SIZE
from BronkhorstCommunication import ELFLOW
import time
from datetime import datetime
import numpy as np
import os.path
import h5py as h5py
import tkinter 
from tkinter import filedialog

scope_ip_addr = '192.168.1.4'
hdf5_filename = 'data\output_'+datetime.now().strftime("%m%d")+'.hdf5'

def acquire_displayed_traces(scope, datasets, hdr_data, x):
    """ worker for below :
        acquire enough sweeps for the averaging, then read displayed scope trace data into HDF5 datasets
    """

    traces = scope.displayed_traces()

    for tr in traces:
        x,NTimes = datasets[tr].shape
        datasets[tr][x-1,0:NTimes] = scope.acquire(tr)[0:NTimes]    # sometimes for 10000 the scope hardware returns 10001 samples, so we have to specify [0:NTimes]
        datasets[tr].resize((x+1,NTimes))
        datasets[tr].flush()
        # hdr_data[tr][x-1] = np.void(scope.header_bytes())    # valid after scope.acquire()
        # hdr_data[tr].flush()
        # are there consequences in timing or compression size if we do the flush(es) recommended for the SWMR function?

    scope.set_trigger_mode('AUTO')   # resume triggering

def create_sourcefile_dataset(grp, fn):
    """ worker for below:
        create an HDF5 dataset containing the contents of the specified file
        add attributes file name and modified time
    """
    fds_name = os.path.basename(fn)
    fds = grp.create_dataset(fds_name, data=open(fn, 'r').read())
    fds.attrs['filename'] = fn
    fds.attrs['modified'] = time.ctime(os.path.getmtime(fn))
    
def Acquire_Scope_Data_2D(scope, fl, get_hdf5_filename, get_channel_description):
    """
    The main data acquisition routine
    
        Arguments are user-provided callback functions that return the following:
            get_hdf5_filename()          the output HDF5 filename,
            get_positions()              the positions array,
            get_channel_description(c)   the individual channel descriptions (c = 'C1', 'C2', 'C3', 'C4'),
            get_ip_addresses()           a dict of the form {'scope':'10.0.1.122', 'x':'10.0.0.123', 'y':'10.0.0.124', 'z':''}
                                              if a key is not specified, no motion will be attempted on that axis
    
        Creates the HDF5 file, creates the various groups and datasets, adds metadata (see "HDF5 OUTPUT FILE SETUP")
    
        Iterates through the positions array (see "MAIN ACQUISITION LOOP"):
            calls motor_control.set_position(pos)
            Waits for the scope to average the data, as per scope settings
            Writes the acquired scope data to the HDF5 output file
    
        Closes the HDF5 file when done
    """
    
    global scope_ip_addr
    # list of files to include in the HDF5 data file
    src_files = [__file__,           # ASSUME this file is in the same directory as the next two:
                os.path.dirname(__file__)+os.sep+'LeCroy_Scope.py',
               ]
    #for testing, list these:s
    print('Files to record in the hdf5 archive:')
    # print('    invoking file      =', src_files[0])
    print('    this file          =', src_files[0])
    print('    LeCroy_Scope file  =', src_files[1])

    #============================
    ######### HDF5 OUTPUT FILE SETUP #########

    # Open hdf5 file for writing (user callback for filename):

    ofn = get_hdf5_filename()      # callback arg to the current function

    f = h5py.File(ofn,  'a')  # 'w' - overwrite (we should have determined whether we want to overwrite in get_hdf5_filename())
    # f = h5py.File(ofn,  'x')  # 'x' - no overwrite
    print("DONE")
    #============================
    # create HDF5 groups similar to those in the legacy format:
    NTimes = scope.max_samples()
    traces = scope.displayed_traces()
    datasets = {}
    hdr_data = {}
    if not "/Acquisition" in f:
        acq_grp    = f.create_group('/Acquisition')              # /Acquisition
        acq_grp.attrs['run_time'] = time.ctime()                                       # not legacy
        scope_grp  = acq_grp.create_group('LeCroy_scope')        # /Acquisition/LeCroy_scope
        presflow_grp = acq_grp.create_group('PresFlow')
        header_grp = scope_grp.create_group('Headers')                                 # not legacy
    
        meta_grp   = f.create_group('/Meta')                     # /Meta                not legacy
        script_grp = meta_grp.create_group('Python')             # /Meta/Python
        scriptfiles_grp = script_grp.create_group('Files')       # /Meta/Python/Files
    
        # in the /Meta/Python/Files group:
        for src_file in src_files:
            create_sourcefile_dataset(scriptfiles_grp, src_file)                       # not legacy
    
        # I don't know how to get this information from the scope:
        scope_grp.create_dataset('LeCroy_scope_Setup_Arrray', data=np.array('Sorry, this is not included', dtype='S'))
    
        # create the scope access object, and iterate over positions
        scope_grp.attrs['ScopeType'] = scope.idn_string

        # create datasets, one for each displayed trace , empty. These will all be populated for compatibility with legacy format hdf5 files.
        # todo: should we maybe just ignore these?  or have a user option to include them?
        
        for tr in traces:
            name = scope.expanded_name(tr)
            ds = scope_grp.create_dataset(name, shape=(1,NTimes), maxshape=(None,NTimes), chunks=(1,NTimes), fletcher32=True, compression='gzip', compression_opts=9)
            datasets[tr] = ds
            hdr_data[tr] = header_grp.create_dataset(name, shape = (NTimes,), dtype="V%i"%(WAVEDESC_SIZE), fletcher32=True, compression='gzip', compression_opts=9)  # V346 = void type, 346 bytes long
        
        pres_ds = presflow_grp.create_dataset('Pressure', shape=(1,1), maxshape=(None,1), chunks=(1,1), fletcher32=True, compression='gzip', compression_opts=9)
        flow_ds = presflow_grp.create_dataset('Flow', shape=(1,1), maxshape=(None,1), chunks=(1,1), fletcher32=True, compression='gzip', compression_opts=9)
        prestime_ds = presflow_grp.create_dataset('Time', shape=(1,1), dtype='float64', maxshape=(None,1), chunks=(1,1), fletcher32=True, compression='gzip', compression_opts=9)
        
        
        # create "time" dataset
        time_ds = scope_grp.create_dataset('time', shape=(1,NTimes), maxshape=(None,NTimes), chunks=(1,NTimes), fletcher32=True, compression='gzip', compression_opts=9)
        t_ds = scope_grp.create_dataset('time.time', shape=(1,1), dtype='float64', maxshape=(None,1), chunks=(1,1), fletcher32=True, compression='gzip', compression_opts=9)
        
        
    else:
        pres_ds = f["/Acquisition/MaxiGauge/Pressure"]
        prestime_ds = f["/Acquisition/MaxiGauge/Time"]
        flow_ds = f["/Acquisition/Bronkhorst/Flow"]
        time_ds = f["/Acquisition/LeCroy_scope/time"]
        t_ds = f["/Acquisition/LeCroy_scope/time.time"]
        
        for tr in traces:
            datasets[tr] = f["/Acquisition/LeCroy_scope/"+scope.expanded_name(tr)]
            hdr_data[tr] = f["/Acquisition/LeCroy_scope/Headers/"+scope.expanded_name(tr)]
            
    
    # at this point all datasets should be created, so we can switch to SWMR mode
    # f.swmr_mode = True    # SWMR MODE: DO NOT CREATE ANY MORE DATASETS AFTER THIS
    
    startTime_scope = 0
    while True:
        try:            
            startTime_pres = time.time()
            ### Read out the pressure gauges
            try:
                ps = mg.pressures() 
            except MaxiGaugeError as mge:
                print(mge)
                continue
            
            pres = "%.3E" % (ps[2].pressure)        
            y = pres_ds.shape[0]
            
            bronk_data = fl.measure()
            flow = "%.3f" % (bronk_data[2])
            print("Pressure: ", pres, "Flow: ", flow,bronk_data[4])
    
            # if startTime_scope % (10*m) == 0:
            #     print('starting acquisition loop at', time.ctime())
            #     acquisition_loop_start_time = time.time()
                    
            #     x = time_ds.shape[0]
                    
            #     # scope.autoscale('C3')  # for now can only _increase_ the V/div
        
            #     # do averaging, and copy scope data for each trace on the screen to the output HDF5 file
            #     acquire_displayed_traces(scope, datasets, hdr_data, x)   # argh the pos[0] index is 1-based
        
            #     # at least get one time array recorded for swmr functions
            #     time_ds[x-1,0:NTimes] = scope.time_array()[0:NTimes]
            #     time_ds.resize((x+1,NTimes))
            #     time_ds.flush()
            #     t_ds[x-1,0] = np.float64(acquisition_loop_start_time)
            #     t_ds.resize((x+1,1))
            #     t_ds.flush()
    
            pres_ds[y-1,0] = float(pres)
            pres_ds.resize((y+1,1))
            pres_ds.flush()
            flow_ds[y-1,0] = float(flow)
            flow_ds.resize((y+1,1))
            flow_ds.flush()
            prestime_ds[y-1,0] = np.float64("%.10g" % startTime_pres)
            prestime_ds.resize((y+1,1))
            prestime_ds.flush()
            
            # do this every 0.1n seconds
            endTime = time.time()-startTime_pres 
            for i in range(n):
                time.sleep(max([0.0, (1.0-endTime)/10]))
            startTime_scope += 0.1*n
    
        # close the connection when the user interrupts it
        except KeyboardInterrupt:
            mg.disconnect()
            scope.__del__()
            raise
        
        except Exception:
            mg.disconnect()
            scope.__del__()
            raise

    # Set any unused datasets to 0 (e.g. any C1-4 that was not acquired); when compressed they require negligible space
    # Also add the text descriptions.    Do these together to be able to be able to make a note in the description
    for tr in traces:
        if datasets[tr].len() == 0:
            datasets[tr] = np.zeros(shape=(NTimes,))
            datasets[tr].attrs['description'] = 'NOT RECORDED: ' + get_channel_description(tr)           # callback arg to the current function
            datasets[tr].attrs['recorded']    = False
        else:
            datasets[tr].attrs['description'] = get_channel_description(tr)                              # callback arg to the current function
            datasets[tr].attrs['recorded']    = True

    f.close()  # close the HDF5 file
    #done

###############################################################################

def get_channel_description(tr) -> str:
    """ callback function to return a string containing a description of the data in each recorded channel """

    #user: assign channel description text here to override the default:
    if tr == 'C1':
        return ''
    if tr == 'C2':
        return 'Output voltage on Faraday cup'
    if tr == 'C3':
        return ''
    if tr == 'C4':
        return ''

    # otherwise, program-generated default description strings follow
    if tr in EXPANDED_TRACE_NAMES.keys():
        return 'no entered description for ' + EXPANDED_TRACE_NAMES[tr]

    return '**** get_channel_description(): unknown trace indicator "'+tr+'". How did we get here?'

def get_hdf5_filename() -> str:
    """ actual callback function to return the output file name """
    global hdf5_filename

    avoid_overwrite = False     # <-- setting this to False will allow overwriting an existing file without a prompt

    #user: modify this if desired

    fn = hdf5_filename       # variable assigned at the top of this file

    if fn == None  or len(fn) == 0  or  (avoid_overwrite  and  os.path.isfile(fn)):
        # if we are not allowing possible overwrites as default, and the file already exists, use file open dialog
        tk = tkinter.Tk()
        tk.withdraw()
        fn = filedialog.asksaveasfilename(title='Enter name of HDF5 file to write')
        if len(fn) == 0:
            raise SystemExit(0)     # user pressed 'cancel'
        tk.destroy()

    hdf5_filename = fn    # save it for later
    return fn

###############################################################################


### Initialize an instance of the MaxiGauge controller
mg = MaxiGauge()
### Initialise the scope
with LeCroy_Scope(scope_ip_addr,verbose=False) as scope:
    with ELFLOW() as fl:
        n = 10 # amount of time (0.1s) between pressure reaadouts
        m = int(scope.timebase("C2")[:-2]) # timebase (s/div), should be > 1
        
        ### Set the time on the scope to match the computer
        # scope.settime()
        Acquire_Scope_Data_2D(scope, fl, get_hdf5_filename, get_channel_description)


    
        