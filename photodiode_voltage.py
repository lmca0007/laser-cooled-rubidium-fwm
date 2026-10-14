# from analysislib.common import *
from lyse import *
from pylab import *
import time

start_time = time.time()

# Import data 
dataset = data(path)    
run = Run(path)
globals = run.get_globals()

t, monitor_data_Photodiode = run.get_trace('mot_fluorescence')
#t, monitor_data_Imaging = run.get_trace('Imaging_Beam')   
y_units = 'V'
    
   
#Plot the IGC Pressure and photodiode voltage data    
figure(1)
plot(1e3*t, monitor_data_Photodiode,label='MOT_Fluorescence_Photodiode_voltage')
title('MOT_Fluorescence')
xlabel('time (ms)')
ylabel(y_units)
axis(ymin=0)
grid(True)
legend(loc='best')

#if wanting to plot something else
# figure(2)
# plot(1e3*t, monitor_data_Imaging,label='Imaging_beam_Photodiode_voltage')
# title('MOT_Fluorescence')
# xlabel('time (ms)')
# ylabel(y_units)
# axis(ymin=0)
# grid(True)
# legend(loc='best')