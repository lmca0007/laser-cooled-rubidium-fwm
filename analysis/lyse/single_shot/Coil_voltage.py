from analysislib.common import *
from lyse import *
from pylab import *
from labscript_utils.unitconversions.linear_coil_driver import UnidirectionalCoilDriver
import time

start_time = time.time()

# Import data 
dataset = data(path)    
run = Run(path)
globals = run.get_globals()

t, monitor_data_Quad_Actual = run.get_trace('Quad_voltage')
#t, monitor_data_Pickup_Voltage = run.get_trace('MOT_Fluorescence')
t, monitor_data_Z_Bias_Actual = run.get_trace('Z_Bias_voltage')   
y_units = 'V'
    
   
#Plot the IGC Pressure and photodiode voltage data    
figure(5)
plot(1e3*t, monitor_data_Quad_Actual,'g',label='Quad Coil')
plot(1e3*t, monitor_data_Z_Bias_Actual,'r',label ='Z Bias Coil',)
title('Quad coil')
xlabel('time (ms)')
ylabel(y_units)
# axis(ymin=-2)
grid(True)
legend(loc='best')
