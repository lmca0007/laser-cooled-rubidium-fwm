from labscript import *
from labscript_utils.unitconversions import *
from labscript import start, stop, add_time_marker, Trigger, RemoteBLACS

from analysislib.krb2 import constants
from labscript_devices.PulseBlaster import PulseBlaster
from labscript_devices.NI_DAQmx.labscript_devices import NI_PCIe_6363
from labscript_devices.NI_DAQmx.labscript_devices import NI_PCI_6733
from labscript_devices.NovaTechDDS9M import NovaTechDDS9M
from labscript_devices.IMAQdxCamera.labscript_devices import IMAQdxCamera
from labscript_devices.AndorSolis.labscript_devices import AndorSolis
from labscript.functions import print_time

'''
Rubidium Vapour 4-Wave Mixing Experiment

The below script will be used to get the four-wave-mixing experiment up and running.
'''


####### START CONNECTION TABLE  ########

PulseBlaster(name='pulseblaster_0', board_number=1) #[AST] board_number used to be 0. When the other pulseblaster (tagged PulseBlaster DDS 1) is connected and if this is kept at 0 --> the pulse blasts switch in BLACS
ClockLine(name='pulseblaster_0_ni_clock', pseudoclock=pulseblaster_0.pseudoclock, connection='flag 0')
ClockLine(name='pulseblaster_0_novatech_clock_0', pseudoclock=pulseblaster_0.pseudoclock, connection='flag 1')
ClockLine(name='pulseblaster_0_novatech_clock_1', pseudoclock=pulseblaster_0.pseudoclock, connection='flag 2')

#[AST] added for fast switching of phase for the Raman beam AOMs
PulseBlaster(name='pulseblaster_1', board_number=0,trigger_device=pulseblaster_0.direct_outputs, trigger_connection='flag 3')

NI_PCIe_6363(name='ni_pcie_6363_0',parent_device=pulseblaster_0_ni_clock, clock_terminal='/ni_pcie_6363_0/PFI0', MAX_name='ni_pcie_6363_0',acquisition_rate=5e4)
NI_PCI_6733 (name='ni_pci_6733_0', parent_device=pulseblaster_0_ni_clock, clock_terminal='/ni_pcie_6363_0/PFI0', MAX_name='ni_pci_6733_0')

NovaTechDDS9M(name='novatechdds9m_0', parent_device=pulseblaster_0_novatech_clock_0, com_port='com6')
NovaTechDDS9M(name='novatechdds9m_1', parent_device=pulseblaster_0_novatech_clock_1, com_port='com7')
NovaTechDDS9M(name='novatechdds9m_2', parent_device=pulseblaster_0_novatech_clock_1, com_port='com10')

#Novatech-0 RF outputs
DDS(           name='science_trap_aom',           parent_device=novatechdds9m_0,   connection='channel 0', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line8'})
DDS(           name='rf_evap',         parent_device=novatechdds9m_0,   connection='channel 1', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line9'})
StaticDDS(     name='source_trap_aom',          parent_device=novatechdds9m_0,   connection='channel 2', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line10'})
StaticDDS(     name='master_lock_aom',            parent_device=novatechdds9m_0,   connection='channel 3', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line11'})
#Novatech-1 RF outputs
DDS(           name='science_repump_aom',           parent_device=novatechdds9m_1,   connection='channel 0', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line0'})
DDS(           name='imaging_push_aom',         parent_device=novatechdds9m_1,   connection='channel 1', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line1'})
StaticDDS(     name='source_repump_aom',          parent_device=novatechdds9m_1,   connection='channel 2', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line2'})
# StaticDDS(     name='Faraday_beam',            parent_device=novatechdds9m_1,   connection='channel 3', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line3'})
StaticDDS(     name='repump_lock_aom',            parent_device=novatechdds9m_1,   connection='channel 3', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line3'})
#Novatech-2 RF outputs
#DDS(           name='Dynamic_LG_Mode_AOM',           parent_device=novatechdds9m_2,   connection='channel 0', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line27'}) [Orignial] Used as the RF supply for the sheet dipole AOM now
DDS(           name='dipole_sheet_aom',           parent_device=novatechdds9m_2,   connection='channel 0', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line27'}) #[AST] using what was used at Dynamic_LG_Mode_AOM as the sheet dipole RF drive 
#DDS(           name='HG_Mode_AOM',         parent_device=novatechdds9m_2,   connection='channel 1', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line28'}) #[Orignial] Used as the RF supply for the south dipole AOM now
DDS(           name='south_dipole_aom',         parent_device=novatechdds9m_2,   connection='channel 1', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line28'}) #[AST] using what was used at HG_Mode_AOM as the south dipole RF drive 
StaticDDS(     name='Static_LG_Mode_AOM',          parent_device=novatechdds9m_2,   connection='channel 2', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line29'}) #[Original] Cannot be changed to DDS --> BEC User manual iii. Hardware
StaticDDS(     name='Unused_2',            parent_device=novatechdds9m_2,   connection='channel 3', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line30'})

#Pulseblaster-0 RF outputs
#DDS(           name='dipole_sheet_aom',                     parent_device=pulseblaster_0.direct_outputs,    connection='dds 0') [Original]
DDS(           name='Kick_aom',                     parent_device=pulseblaster_0.direct_outputs,    connection='dds 0') #[AST] using it as the AOM for the kicking laser
#DDS(           name='south_dipole_aom',                        parent_device=pulseblaster_0.direct_outputs, connection='dds 1') #[Original]
DDS(           name='raman_circular',                        parent_device=pulseblaster_0.direct_outputs, connection='dds 1') #[AST] using it as the AOM for the Raman sigma + laser

#[AST] Pulseblaster-4 RF outputs
DDS(           name='raman_horizontal',                     parent_device=pulseblaster_1.direct_outputs,    connection='dds 0')
DDS(           name='raman_vertical',                        parent_device=pulseblaster_1.direct_outputs, connection='dds 1')

#Digital triggger connections for odd devices
DigitalOut(    name='nt_table_enable',      parent_device=ni_pcie_6363_0,    connection='port0/line4')
DigitalOut(    name='mot_mirror_servo',      parent_device=ni_pcie_6363_0,    connection='port0/line5')
DigitalOut(    name='dummy_for_even_number',      parent_device=ni_pcie_6363_0,    connection='port0/line7')
DigitalOut(    name='source_mot_led',      parent_device=ni_pcie_6363_0,    connection='port0/line15')
DigitalOut(    name='sorensen_high',      parent_device=ni_pcie_6363_0,    connection='port0/line26')
DigitalOut(    name='sorensen_intermediate',      parent_device=ni_pcie_6363_0,    connection='port0/line25')
DigitalOut(    name='bottom_imaging_mirror',      parent_device=ni_pcie_6363_0,    connection='port0/line6')


#Analog outputs
AnalogOut(     name='source_coil_north',          parent_device=ni_pci_6733_0,    connection='ao0',
               unit_conversion_class=UnidirectionalCoilDriver,
               unit_conversion_parameters={
                        "slope": source_coil_north_slope,
                        "shift": source_coil_north_shift,
                        "saturation": source_coil_north_saturation
               })
               
AnalogOut(     name='source_coil_south',          parent_device=ni_pci_6733_0,    connection='ao1',
               unit_conversion_class=UnidirectionalCoilDriver,
               unit_conversion_parameters={
                        "slope": source_coil_south_slope,
                        "shift": source_coil_south_shift,
                        "saturation": source_coil_south_saturation
               })
AnalogOut(     name='source_coil_top',          parent_device=ni_pci_6733_0,    connection='ao2',
               unit_conversion_class=UnidirectionalCoilDriver,
               unit_conversion_parameters={
                        "slope": source_coil_top_slope,
                        "shift": source_coil_top_shift,
                        "saturation": source_coil_top_saturation
               })
               
AnalogOut(     name='source_coil_bottom',          parent_device=ni_pci_6733_0,    connection='ao3',
               unit_conversion_class=UnidirectionalCoilDriver, 
               unit_conversion_parameters={
                        "slope": source_coil_bottom_slope,
                        "shift": source_coil_bottom_shift,
                        "saturation": source_coil_bottom_saturation
               })
AnalogOut(     name='bias_x_coils',          parent_device=ni_pci_6733_0,    connection='ao4',
               unit_conversion_class=BidirectionalCoilDriver,
               unit_conversion_parameters={
                        "slope": bias_x_slope,
                        "shift": bias_x_shift,
                        "saturation": bias_x_saturation
               })
               
AnalogOut(     name='bias_y_coils',          parent_device=ni_pci_6733_0,    connection='ao5',
               unit_conversion_class=BidirectionalCoilDriver,
               unit_conversion_parameters={
                        "slope": bias_y_slope,
                        "shift": bias_y_shift,
                        "saturation": bias_y_saturation
               })
AnalogOut(     name='bias_z_coils',          parent_device=ni_pci_6733_0,    connection='ao6',
               unit_conversion_class=BidirectionalCoilDriver,
               unit_conversion_parameters={
                        "slope": bias_z_slope,
                        "shift": bias_z_shift,
                        "saturation": bias_z_saturation
               })
               
AnalogOut(     name='quad_coils',          parent_device=ni_pci_6733_0,    connection='ao7',
               unit_conversion_class=UnidirectionalCoilDriver,
               unit_conversion_parameters={
                        "slope": quad_slope,
                        "shift": quad_shift,
                        "saturation": quad_saturation
               })
               
AnalogOut(     name='rubidium_getter',          parent_device=ni_pcie_6363_0,    connection='ao1',
               unit_conversion_class=UnidirectionalCoilDriver,
               unit_conversion_parameters={
                        "slope": rubidium_getter_slope,
                        "shift": rubidium_getter_shift,
                        "saturation": rubidium_getter_saturation
               })
AnalogOut(     name='dummy',          parent_device=ni_pcie_6363_0,    connection='ao0')

#NI_PCIe_6363 Analog In channels
AnalogIn(      'quad_coils_monitor',                     ni_pcie_6363_0,         'ai9')
AnalogIn(      'bias_z_monitor',                     ni_pcie_6363_0,         'ai10')
AnalogIn(      'mot_fluorescence',                     ni_pcie_6363_0,         'ai11')
AnalogIn(      'igc_pressure',                     ni_pcie_6363_0,         'ai16')


#Digital triggers for Shutters
# Shutter(       name='Imaging_Shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line17',  delay=(3.18e-3,2.45e-3)) #open, close 
Shutter(       name='master_laser_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line18',  delay=(0,0)) #open, close 
Shutter(       name='repump_laser_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line19',  delay=(3.59e-3,3.32e-3)) #open, close   
Shutter(       name='bottom_imaging_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line20',  delay=(3.24e-3,2.45e-3)) #open, close 
Shutter(       name='side_imaging_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line21',  delay=(3.2e-3,2.64e-3)) #open, close 
#Shutter(       name='Top_MOT_Beam_Shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line22',  delay=(3.47e-3,2.72e-3)) #open, close 
Shutter(       name='science_mot_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line23',  delay=(2.82e-3,3.36e-3)) #open, close    
Shutter(       name='push_beam_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line24',  delay=(0,0)) #open, close 

RemoteBLACS(name='imaging_pc', host='bec-krb2-analysis.physics.monash.edu')

# Camera trigger lines
Trigger(    name='side_camera_trigger', parent_device=pulseblaster_1.direct_outputs, connection='flag 0')#[AST]
Trigger(    name='bottom_camera_trigger', parent_device=ni_pcie_6363_0, connection='port0/line14')

IMAQdxCamera(   name='side_camera', parent_device=side_camera_trigger, connection='trigger', orientation='side', serial_number=0xF31031F54, worker=imaging_pc,
    camera_attributes = {'CameraAttributes::Acquisition::AcquisitionMode': 'Continuous','CameraAttributes::Acquisition::Trigger::TriggerMode': 'On','CameraAttributes::Controls::Exposure::ExposureMode': 'TriggerWidth'},
    manual_mode_camera_attributes = {'CameraAttributes::Acquisition::Trigger::TriggerMode': 'Off'})

AndorSolis(
    name='bottom_camera',
    parent_device=bottom_camera_trigger,
    connection='trigger',
    orientation='bottom',
    serial_number=11418,
    worker=imaging_pc,
    trigger_duration = 1e-3,
    mock=False,
    camera_attributes = {'CameraAttributes::Acquisition::Trigger::TriggerMode':'On'},
    manual_mode_camera_attributes = {'CameraAttributes::Acquisition::Trigger::TriggerMode':'Off'})
 
#Control voltage at which the sorensen voltage should be switched
sorensen_critical_current = 2.6
   
####### END CONNECTION TABLE  ########

# Define t = 0 (start of experiment)
start()
t = 0

# set static AOMs
source_repump_aom.enable(source_repump_aom.t0)
source_repump_aom.setfreq(rb_source_MOT_repump_frequency*MHz)
source_repump_aom.setamp(rb_source_MOT_repump_amplitude)

source_trap_aom.enable(source_trap_aom.t0)
source_trap_aom.setfreq(rb_source_MOT_trap_frequency*MHz)
source_trap_aom.setamp(rb_source_MOT_trap_amplitude)

Static_LG_Mode_AOM.disable(Static_LG_Mode_AOM.t0)
Static_LG_Mode_AOM.setfreq(Static_LG_AOM_freq*MHz) #[Original]
Static_LG_Mode_AOM.setamp(Static_LG_AOM_amp) #[Original]

# laser lock! Be careful!
# should be manually turned on always with the hardware switch, 
#but let's do this just to be safe
master_lock_aom.enable(master_lock_aom.t0)
# freq/amp paremeters
master_lock_aom.setfreq(47*MHz)
# master_lock_aom.setamp(0.4501)
master_lock_aom.setamp(0.650)

#Set the Sorensen to its low voltage so we don't fry our IGBT's upon MOT loading, and ensure the bottom imaging mirror is in the correct place
sorensen_high.go_low(t)
sorensen_intermediate.go_low(t)
bottom_imaging_mirror.go_low(t)
dummy_for_even_number.go_low(t) #[AST] Added the shutter to block the second arm during kicking

#Engage the novatechs
nt_table_enable.go_high(nt_table_enable.t0)

#Make sure the MOT mirror is in place
mot_mirror_servo.go_low(mot_mirror_servo.t0)

#Ensure the imaging shutters are closed
bottom_imaging_shutter.close(t)
side_imaging_shutter.close(t)

#Set the coils etc. to their desired values for the MOT load
source_coil_bottom.constant(t, source_coil_bottom_current)
source_coil_top.constant(t, source_coil_top_current)
source_coil_north.constant(t, source_coil_north_current)
source_coil_south.constant(t, source_coil_south_current)
bias_x_coils.constant(t, x_bias_MOT_load_current, "A")
bias_y_coils.constant(t, y_bias_MOT_load_current, "A")
bias_z_coils.constant(t, z_bias_MOT_load_current, "A")
quad_coils.constant(t, quad_coil_MOT_load_current, "A")
rubidium_getter.constant(t, getter_standby_current, "A")


#Set dynamic AOM's
science_trap_aom.enable(science_trap_aom.t0)
science_trap_aom.setfreq(science_trap_aom.t0, rb_science_MOT_trap_frequency*MHz)
science_trap_aom.setamp(science_trap_aom.t0, rb_science_MOT_trap_amplitude)

imaging_push_aom.enable(imaging_push_aom.t0)
imaging_push_aom.setfreq(imaging_push_aom.t0, rb_push_frequency*MHz)
imaging_push_aom.setamp(imaging_push_aom.t0, rb_push_amplitude)

science_repump_aom.enable(science_repump_aom.t0)
science_repump_aom.setfreq(science_repump_aom.t0, rb_science_MOT_repump_frequency*MHz)
science_repump_aom.setamp(science_repump_aom.t0, rb_science_MOT_repump_amplitude)

dipole_sheet_aom.disable(dipole_sheet_aom.t0)
dipole_sheet_aom.setfreq(t, Flat_Sheet_AOM_Frequency*MHz)
dipole_sheet_aom.setamp(t, Flat_Sheet_AOM_Amplitude)

south_dipole_aom.disable(south_dipole_aom.t0)
south_dipole_aom.setfreq(t, south_dipole_trap_frequency*MHz)
south_dipole_aom.setamp(t, south_dipole_trap_amplitude)

raman_horizontal.disable(raman_horizontal.t0)
raman_horizontal.setfreq(t+1e-6, H_Freq*MHz)
raman_horizontal.setamp(t+1e-6, H_Amp)

raman_vertical.disable(raman_vertical.t0)
raman_vertical.setfreq(t+1e-6, V_Freq*MHz)
#raman_vertical.setphase(t+1e-6, 90)
raman_vertical.setamp(t+1e-6, V_Amp)

#raman_circular.disable(raman_vertical.t0)
#raman_circular.setfreq(t+1e-6, V_Freq*MHz)
#raman_circular.setamp(t+1e-6, V_Amp)

Kick_aom.disable(Kick_aom.t0)
Kick_aom.setfreq(t, Kick_Freq*MHz)
Kick_aom.setamp(t, Kick_Amp)

#Dynamic_LG_Mode_AOM.disable(Dynamic_LG_Mode_AOM.t0) [Original]
#Dynamic_LG_Mode_AOM.setfreq(t, Dynamic_LG_freq_initial*MHz) [Original]
#Dynamic_LG_Mode_AOM.setamp(t, Dynamic_LG_Amp_initial) [Original]

#HG_Mode_AOM.disable(HG_Mode_AOM.t0) [Original]
#HG_Mode_AOM.setfreq(t, HG_Mode_AOM_Frequency*MHz) [Original]
#HG_Mode_AOM.setamp(t, HG_Mode_initial_amp) [Original]

rf_evap.disable(rf_evap.t0)
rf_evap.setfreq(t, rf_frequency_1*MHz)
rf_evap.setamp(t, rf_amp_1)

#Below is added to trigger the push beam as it is getting stuck [AST]
for i in range(5):
    t+=10e-3
    push_beam_shutter.open(t)
    t+=10e-3
    push_beam_shutter.close(t)

#Ensure the source and central mot shutters are open to start loading the MOT
#enable AOMs also
science_mot_shutter.open(t)
master_laser_shutter.open(t)
push_beam_shutter.open(t)
# Top_MOT_Beam_Shutter.open(t)
repump_laser_shutter.open(t)

#Start the experiment after 10ms
t+=10e-3

# Turn on the getter
rubidium_getter.constant(t, getter_load_current, "A")

#If doing optimisation measurements, clear the MOT of its load during the experiment programming
if s01_Start_Fresh:
    science_trap_aom.disable(t)
    source_trap_aom.disable(t)   
    t+=start_fresh_time
    science_trap_aom.enable(t)
    source_trap_aom.enable(t)

#Switch on the source_mot_led to increase the pressure in the source chamber
if source_mot_led_enable:
    source_mot_led.go_high(t)

# ensure we don't turn on the getter for longer than the MOT load time
if rb_science_MOT_load_time < getter_blast_time:
    getter_blast_time = rb_science_MOT_load_time
# turn  down the getter to a standy current for the rest of the MOT load
rubidium_getter.constant(t+getter_blast_time, getter_standby_current, "A")

t += rb_science_MOT_load_time
imaging_push_aom.disable(t)
push_beam_shutter.close(t)
# turn off the getter at the end of the MOT load
rubidium_getter.constant(t, 0, "A")

#Switch off the source_mot_led to allow the pressure to drop for experiments
if source_mot_led_enable:
    source_mot_led.go_low(t)

add_time_marker(t, "MOT has been fully loaded",verbose = verbose)
#Next, if we want to compress our MOT before PGC
if s02_CMOT:
    #Here we perform our CMOT stage, all changes occur over the same time span (rb_magnetic_compress_time), with the coils ramped with sine ramps to smooth out the movement.
    #Here we ramp our bias coils to move the CMOT into the catch position
    bias_x_coils.sine_ramp(t,rb_magnetic_compress_time,x_bias_MOT_load_current, rb_compress_bias_x, 1e3, "A")
    bias_y_coils.sine_ramp(t, rb_magnetic_compress_time, y_bias_MOT_load_current, rb_compress_bias_y, 1e3, "A") 
    bias_z_coils.sine_ramp(t, rb_magnetic_compress_time, z_bias_MOT_load_current, rb_compress_bias_z, 1e3, "A")
    #We ramp the detuning of the light to increase the CMOT density
    science_trap_aom.frequency.ramp(t, rb_magnetic_compress_time, rb_science_MOT_trap_frequency*MHz, trap_compress_frequency*MHz, 5e3)
    science_trap_aom.amplitude.ramp(t, rb_magnetic_compress_time, rb_science_MOT_trap_amplitude, trap_compress_amplitude, 5e3)
    science_repump_aom.frequency.ramp(t, rb_magnetic_compress_time, rb_science_MOT_repump_frequency*MHz, repump_compress_frequency*MHz, 5e3) 
    science_repump_aom.amplitude.ramp(t, rb_magnetic_compress_time, rb_science_MOT_repump_amplitude, repump_compress_amplitude, 5e3) 
    #And increase the field gradient to compress the CMOT
    t+=quad_coils.sine_ramp(t,rb_magnetic_compress_time,quad_coil_MOT_load_current, rb_compress_quad, 5e3, "A")

    add_time_marker(t, "MOT has been compressed",verbose = verbose)
    
#Switch off the 2D MOT and push beam
source_trap_aom.disable(t)
source_repump_aom.disable(t)
source_coil_bottom.constant(t, 0)
source_coil_top.constant(t, 0)
source_coil_north.constant(t, 0)
source_coil_south.constant(t, 0)

t+=100e-3

add_time_marker(t, "End MOT hold time",verbose = verbose)

#Next is PGC
if s03_PGC:
    # #if we need to find the dipole beams we can uncomment this section so we can look during PGC (try 15ms drop)
    if Find_Dipole_Trap:
        #Note frequency and amp set at beginning
        south_dipole_aom.enable(t)  
        dipole_sheet_aom.enable(t) 
    
    #ramp the quad coils and bias coils to their specified values and wait for the fields to switch, note light is on during this stage
    bias_x_coils.sine_ramp(t, pgc_magnetic_field_ramp,rb_compress_bias_x, pgc_bias_x, 5e4, units="A") 
    bias_y_coils.sine_ramp(t, pgc_magnetic_field_ramp,rb_compress_bias_y, pgc_bias_y, 5e4, units="A") 
    bias_z_coils.sine_ramp(t, pgc_magnetic_field_ramp,rb_compress_bias_z, pgc_bias_z_initial, 5e4, units="A")
    t+=quad_coils.sine_ramp(t, pgc_magnetic_field_ramp,rb_compress_quad, pgc_quad_initial, 5e4, units="A")

    #Do the final turn off
    quad_coils.constant(t, pgc_quad_final, "A")
    bias_z_coils.constant(t, pgc_bias_z, "A")
    
    #Here we start detuning the cooling and repump light
    if pgc_time:
        #We have the choice of ramping the light, or just switching it to its final value, I found a quick ramp works best
        if pgc_ramp_light:
            # Start to ramp the detuning of the cooling light to cool and compress the cloud
            science_repump_aom.frequency.ramp(t, pgc_light_ramp, repump_compress_frequency*MHz, pgc_repump_freq*MHz, 9e3)
            science_trap_aom.amplitude.ramp(t, pgc_light_ramp, trap_compress_amplitude, pgc_cooling_amp_final, 9e3)
            t+=science_trap_aom.frequency.ramp(t, pgc_light_ramp, trap_compress_frequency*MHz, pgc_cooling_freq_final*MHz, 9e3)
            
        else:
            #Otherwise set to their final values
            science_trap_aom.setfreq(t, pgc_cooling_freq_final*MHz)
            science_repump_aom.setamp(t, pgc_repump_amp_final)
        
    # Molasses cooling at fixed values for optimal temp, and reducing repump to optically pump into the Rb87 F=1 manifold
    t += science_repump_aom.amplitude.ramp(t,pgc_time, pgc_repump_amp_initial, pgc_repump_amp_final, 9e3)       
    
    #Turn off the repump to get the atoms into (1,1) for magnetic trapping
    if repump_wait:
        science_repump_aom.disable(t-repump_wait)
        repump_laser_shutter.close(t-repump_wait)
        print_time(t-repump_wait-repump_laser_shutter.close_delay,'Science Repump shutter triggered to close after PGC')
        
    add_time_marker(t, "End PGC",verbose = verbose)        
    #And switch off the trapping light also
    science_trap_aom.disable(t)
    #And close the shutter if we aren't doing fluorescence imaging
    if (not s04_MT and not Fluorescence_Imaging) or s04_MT:
        master_laser_shutter.close(t)
        science_mot_shutter.close(t)
    print_time(t-science_mot_shutter.close_delay,'Science trap shutter triggered to close')
    #And if we are bottom imaging, close the top mot beam shutter
    #if Bottom_Imaging:
        #if Fluorescence_Imaging:
            #Top_MOT_Beam_Shutter.close(t)
  
#And we next load into a magnetic trap
if s04_MT: 
    #if imaging with the bottom camera, get the mot mirror aand imaging mirror into position
    if Bottom_Imaging:
        mot_mirror_servo.go_high(t)
        if Absorption_Imaging:
            bottom_imaging_mirror.go_high(t+5e-3)
        elif Faraday_Imaging:
            bottom_imaging_mirror.go_high(t+5e-3)
    if s08_Load_Uniform_Trap:
        mot_mirror_servo.go_high(t)
    if Find_Green_Trap:
        mot_mirror_servo.go_high(t)
    #If trying to find the bottom imaging beam, get the imaging mirror into place
    if Find_imaging_beam:
        #mot_mirror_servo.go_high(t)
        bottom_imaging_mirror.go_high(t+5e-3)
    #[AST] Changed Raman beams to come from vertical. so need to move the mirror in and remove the vertical bottom MOT mirror
    if s12_Raman: 
        #bottom_imaging_mirror.go_high(t)
        print('Hi')
        #mot_mirror_servo.go_high(t)

    #Set the sorensen to its high voltage for the fast switch time for the catch
    sorensen_high.go_high(t-5e-3)
    sorensen_intermediate.go_high(t-5e-3)
    print_time(t-5e-3,'Sorensen voltage switched')
     
    #Switch on the magnetic trap and wait for the atoms to stabilise
    bias_x_coils.constant(t, mt_bias_x, "A")
    bias_y_coils.constant(t, mt_bias_y, "A")      
    bias_z_coils.sine_ramp(t, catch_time_Z_bias,0, mt_bias_z, 1e4, units="A")   
    #Here I have hardcoded the initial quad value to make the ramp smooth
    t+=quad_coils.sine_ramp(t, catch_time_quad,1, mt_quad, 1e4, units="A") 
    t+=catch_wait   

    #Quickly compress the atoms a bit
    if Initial_Compress:    
       bias_z_coils.sine_ramp(t, initial_compression_time,mt_bias_z, initial_compress_z, 1e4, units="A") 
       t+=quad_coils.sine_ramp(t, initial_compression_time,mt_quad, initial_compress_quad, 1e4, units="A")
       t+=initial_compress_wait
    
    # Then move the trap to its final position
    if Move_Trap:
      bias_y_coils.sine_ramp(t,z_bias_compress_time, mt_bias_y, mt_bias_y_compress, 1e4, units="A")
      bias_x_coils.sine_ramp(t,z_bias_compress_time, mt_bias_x, mt_bias_x_compress, 1e4, units="A")
      t+=bias_z_coils.sine_ramp(t,z_bias_compress_time, initial_compress_z, mt_bias_z_compress, 1e4, units="A")
      t+=final_position_settle_time

    add_time_marker(t, "Atoms caught, settled and transported in magnetic trap",verbose = verbose)
    
    #Finally we do the last bit of compression
    if Compress:
        #If we need to find the dipole traps
        if Find_Dipole_Trap:
            #Note frequency and amp set at beginning
            dipole_sheet_aom.enable(t)
            south_dipole_aom.enable(t)
            if Find_Raman_Beams:
                raman_horizontal.enable(t)
                raman_vertical.enable(t)
        #Compress the magnetic trap to its final value 
        t +=quad_coils.sine_ramp(t, compress_time, initial_compress_quad, mt_compress_quad, 1e4, units="A") 
    else:
        #If not compressing, set the Sorensen to low so we don't burn out an IGBT
        sorensen_high.go_low(t+30e-3)
        #sorensen_intermediate.go_low(t)
        print_time(t,'Sorensen voltage switched to low for hold')
        
    if Find_Dipole_Trap:
        #Note frequency and amp set at beginning
        south_dipole_aom.enable(t)  
        dipole_sheet_aom.enable(t)

        
    if Dipole_Trap:
        #Note frequency and amp set at beginning
        if Single_beam_trap:
            south_dipole_aom.enable(t)  
        if Sheet_trap:
            south_dipole_aom.enable(t) #[AST] added so single beam evaporation and sheet evaporation can be separated as coded in Hybrid evaporation
            dipole_sheet_aom.enable(t)
    
    add_time_marker(t, "Magnetic Trap has been compressed",verbose = verbose)
    t+=Magnetic_Trap_Hold  
    
    if ModulateMagneticTrapX:
        for i in range(int(ModulateTime*ModulateFrequency)):
            t+=bias_x_coils.sine_ramp(t,1/(2*float(ModulateFrequency)), mt_bias_x_compress, Modulate_x, 1e4, units="A")
            t+=bias_x_coils.sine_ramp(t,1/(2*float(ModulateFrequency)), Modulate_x, mt_bias_x_compress, 1e4, units="A")
    if ModulateMagneticTrapZ:
        # for i in range(int(ModulateTime*ModulateFrequency)):
            # t+=bias_z_coils.sine_ramp(t,1/(2*float(ModulateFrequency)), mt_bias_z_compress, Modulate_z, 1e4, units="A")
            # t+=bias_z_coils.sine_ramp(t,1/(2*float(ModulateFrequency)), Modulate_z, mt_bias_z_compress, 1e4, units="A")
        t+= bias_z_coils.sine(t,ModulateTime,Modulate_Z_Bias*mt_bias_z_compress, 2 * pi * ModulateFrequency, 3*pi/2 , (1+Modulate_Z_Bias)*mt_bias_z_compress, 1e4,units="A")
    if ModulateMagneticQuad:
        t+= quad_coils.sine(t,ModulateTime,Modulate_Quad*mt_compress_quad, 2 * pi * ModulateFrequency, 0 , mt_compress_quad, 1e4,units="A")

    
if s05_RF_Evaporation:    
    #Here we perform RF evaporation in a compressed magnetic trap, we can pick how many stages we want for different final temperatures
    #First we enable the RF
    rf_evap.setamp(t, rf_amp_1)
    rf_evap.enable(t)
    # Then ramp our RF
    if RF_Ramp_1:
        t += rf_evap.frequency.exp_ramp_t(t,rf_evap_time_1, rf_frequency_1* MHz,rf_frequency_2*MHz, time_constant_1, 
        (1.0*rf_evap_points)/rf_evap_time_1,truncation=truncation_compress_evaporation, truncation_type='exponential')
    
    if RF_Ramp_2:
        t += rf_evap.frequency.exp_ramp_t(t,rf_evap_time_2, rf_frequency_2* MHz,rf_frequency_3*MHz, time_constant_2, 
        (1.0*rf_evap_points)/rf_evap_time_2,truncation=truncation_compress_evaporation, truncation_type='exponential')
    
    if RF_Ramp_3:
        t += rf_evap.frequency.exp_ramp_t(t,rf_evap_time_3, rf_frequency_3* MHz,rf_frequency_4*MHz, time_constant_3, 
        (1.0*rf_evap_points)/rf_evap_time_3,truncation=truncation_compress_evaporation, truncation_type='exponential')
    
    if RF_Spectroscopy:
        t += rf_evap.frequency.exp_ramp_t(t,rf_spec_time, rf_frequency_spec_1* MHz,rf_frequency_spec_2*MHz, time_constant_3, 
        (1.0*rf_evap_points)/rf_spec_time,truncation=truncation_compress_evaporation, truncation_type='exponential')
    
    t+=RF_hold
    #Useful for finding the imaging beam with a big target
    # if Find_imaging_beam:
        # master_laser_shutter.open(t-300e-3)
        # bottom_imaging_shutter.open(t-300e-3)
        # imaging_push_aom.setfreq(t, bottom_imaging_frequency * MHz)
        # imaging_push_aom.setamp(t, 0.45)
        # imaging_push_aom.enable(t)
        # imaging_push_aom.disable(t+find_pulse_duration)
        # bottom_imaging_shutter.close(t+find_pulse_duration)   
        # t+=find_pulse_duration
    
    if not s06_Decompress:
        rf_evap.disable(t)
    add_time_marker(t, "End RF evaporation in the compressed trap",verbose = verbose)
    
if s06_Decompress:  
    #Next we decompress our compressed magnetic trap so as to load the atoms into the hybrid trap,
    #Ramp the quad current, noting what value we start at so we don't have a discontinuity
    sorensen_high.go_low(t+decompress_time)
    sorensen_intermediate.go_low(t+decompress_time)
    if Compress:
        quad_coils.sine_ramp(t, decompress_time, mt_compress_quad, decompress_quad, 1e3, units="A")
        bias_x_coils.sine_ramp(t, decompress_time, mt_bias_x_compress, decompress_x_bias, 1e3, units="A") #[AST] Added to get smoother transition to dipole trap, there was only Bz before
        bias_y_coils.sine_ramp(t, decompress_time, mt_bias_y_compress, decompress_y_bias, 1e3, units="A") #[AST] Added to get smoother transition to dipole trap, there was only Bz before
        bias_z_coils.sine_ramp(t, decompress_time, mt_bias_z_compress, decompress_z_bias, 1e3, units="A")
    else:
        quad_coils.sine_ramp(t, decompress_time, mt_quad, decompress_quad, 1e3, units="A")
        bias_x_coils.sine_ramp(t, decompress_time, mt_bias_x, decompress_x_bias, 1e3, units="A") #[AST] Added to get smoother transition to dipole trap, there was only Bz before
        bias_y_coils.sine_ramp(t, decompress_time, mt_bias_y, decompress_y_bias, 1e3, units="A") #[AST] Added to get smoother transition to dipole trap, there was only Bz before
        bias_z_coils.sine_ramp(t, decompress_time, mt_bias_z, decompress_z_bias, 1e3, units="A")
    #Set the RF power
    rf_evap.setamp(t, decompress_amp)
    #Then sweep the RF
    t+=rf_evap.frequency.exp_ramp_t(t,decompress_time-constant_rf, decompress_rf_frequency_1* MHz,decompress_rf_frequency_2*MHz, decompress_time_constant, (1.0*rf_decompress_evap_points)/decompress_time,truncation=truncation_compress_evaporation, truncation_type='exponential')
    #Wait until the quad coil has finished decompressing
    t+=constant_rf

    rf_evap.disable(t)
    #This next line is useful to see what does not remain in the dipole trap
    #quad_coils.constant(t, 0.55, "A")
    t+=decompress_hold
    
    if Find_imaging_beam:
        master_laser_shutter.open(t-100e-3)
        bottom_imaging_shutter.open(t-100e-3)
        imaging_push_aom.setfreq(t, bottom_imaging_frequency * MHz)
        imaging_push_aom.setamp(t, 0.45)
        imaging_push_aom.enable(t)
        imaging_push_aom.disable(t+find_pulse_duration)
        bottom_imaging_shutter.close(t+find_pulse_duration)   
        t+=find_pulse_duration
    
    # if Find_Sheet_Peak:
        # quad_coils.constant(t, 0)
        # bias_z_coils.constant(t, 0, "A")
        # bias_x_coils.constant(t, 0, "A")
        # bias_y_coils.constant(t, 0, "A") 
        # t+=Move_wait
    
    add_time_marker(t, "Magnetic trap decompressed, loading the dipole trap",verbose = verbose)
    
if s07_Hybrid_Evaporation:
    print('in Hybrid Evap')
    #bias_x_coils.sine_ramp(t,hybrid_evap_time_1,mt_bias_x_compress, hybrid_bias_x, 1e3, "A") #[Original] [AST] changed as I added a decompress x to the decompression stage
    bias_x_coils.sine_ramp(t,hybrid_evap_time_1,decompress_x_bias, hybrid_bias_x, 1e3, "A") # [AST] as I added a decompress x to the decompression stage
    #bias_y_coils.sine_ramp(t, hybrid_evap_time_1, mt_bias_y_compress, hybrid_bias_y, 1e3, "A") #[Original] [AST] changed as I added a decompress x to the decompression stage
    bias_y_coils.sine_ramp(t, hybrid_evap_time_1, decompress_y_bias, hybrid_bias_y, 1e3, "A") # [AST] as I added a decompress x to the decompression stage
    #bias_z_coils.sine_ramp(t, rb_magnetic_compress_time, z_bias_MOT_load_current, rb_compress_bias_z, 1e3, "A")
    
    if s11_QDKR:
        dummy_for_even_number.go_high(t) #[AST] added to block second arm of kick laser        
    
    if Single_beam_trap: #[AST] Enabled in Initial Dipole Parameters
        #Here we calculate our ramp parameters
        South_dipole_reduce_amp_1 = linspace(south_dipole_trap_amplitude,south_amp_1,51)
        Hybrid_dipole_down_dt_1 = hybrid_evap_time_1/50.0
        #And perform the dipole beam reduction
        for i in range(50):
            south_dipole_aom.setamp(t,South_dipole_reduce_amp_1[i])
            t+= Hybrid_dipole_down_dt_1
        
        if hybrid_ramp_2:
            South_dipole_reduce_amp_2 = linspace(south_amp_1,south_amp_2,51)
            Hybrid_dipole_down_dt_2 = hybrid_evap_time_2/50.0
            for i in range(50):
                south_dipole_aom.setamp(t,South_dipole_reduce_amp_2[i])
                t+= Hybrid_dipole_down_dt_2
        
        if hybrid_ramp_3:
            South_dipole_reduce_amp_3 = linspace(south_amp_2,south_amp_3,51)
            Hybrid_dipole_down_dt_3 = hybrid_evap_time_3/50.0
            for i in range(50):
                south_dipole_aom.setamp(t,South_dipole_reduce_amp_3[i])
                t+= Hybrid_dipole_down_dt_3      
        
        if hybrid_ramp_4:
            South_dipole_reduce_amp_4 = linspace(south_amp_3,south_amp_4,51)
            Hybrid_dipole_down_dt_4 = hybrid_evap_time_4/50.0
            for i in range(50):
                south_dipole_aom.setamp(t,South_dipole_reduce_amp_4[i])
                t+= Hybrid_dipole_down_dt_4 

    #[AST] Think about the sheet trap --> is it just at the end of DPT evaporation??
    if Sheet_trap: #[AST] Pick either single_beam_trap or to be two dipoles
    #if Sheet_evaporation: #[NOTE] Enable Sheet_trap in Initial Dipole Parameters. 
                           #[AST] Was a true false variable in Hybrid evaporation in Runmanager. But removed by  
        #Here we calculate our ramp parameters
        South_dipole_reduce_amp_1 = linspace(south_dipole_trap_amplitude,south_amp_1,51)
        Flat_Sheet_reduce_amp_1 = linspace(Flat_Sheet_AOM_Amplitude,flat_amp_1,51)
        Hybrid_dipole_down_dt_1_sheet = hybrid_evap_time_1_sheet/50.0
        #And perform the dipole beam reduction
        
        for i in range(50):
            south_dipole_aom.setamp(t,South_dipole_reduce_amp_1[i])
            dipole_sheet_aom.setamp(t,Flat_Sheet_reduce_amp_1[i])
            t+= Hybrid_dipole_down_dt_1_sheet
        
        if hybrid_ramp_2:
            South_dipole_reduce_amp_2 = linspace(south_amp_1,south_amp_2,51)
            Flat_Sheet_reduce_amp_2 = linspace(flat_amp_1,flat_amp_2,51)
            Hybrid_dipole_down_dt_2_sheet = hybrid_evap_time_2_sheet/50.0
            for i in range(50):
                south_dipole_aom.setamp(t,South_dipole_reduce_amp_2[i])
                dipole_sheet_aom.setamp(t,Flat_Sheet_reduce_amp_2[i])
                t+= Hybrid_dipole_down_dt_2_sheet
        
        if hybrid_ramp_3:
            South_dipole_reduce_amp_3 = linspace(south_amp_2,south_amp_3,51)
            Flat_Sheet_reduce_amp_3 = linspace(flat_amp_2,flat_amp_3,51)
            Hybrid_dipole_down_dt_3_sheet = hybrid_evap_time_3_sheet/50.0
            for i in range(50):
                south_dipole_aom.setamp(t,South_dipole_reduce_amp_3[i])
                dipole_sheet_aom.setamp(t,Flat_Sheet_reduce_amp_3[i])
                t+= Hybrid_dipole_down_dt_3_sheet      
        
        if hybrid_ramp_4:
            South_dipole_reduce_amp_4 = linspace(south_amp_3,south_amp_4,51)
            Flat_Sheet_reduce_amp_4 = linspace(flat_amp_3,flat_amp_4,51)
            Hybrid_dipole_down_dt_4_sheet = hybrid_evap_time_4_sheet/50.0
            for i in range(50):
                south_dipole_aom.setamp(t,South_dipole_reduce_amp_4[i])
                dipole_sheet_aom.setamp(t,Flat_Sheet_reduce_amp_4[i])
                t+= Hybrid_dipole_down_dt_4_sheet 
    
    t+=hybrid_hold 
     
    if ModulateDipoleTrapZ:
        # South_dipole_increase_amp_3 = linspace(south_amp_3,south_amp_2,51)
        # for i in range(50):
            # south_dipole_aom.setamp(t,South_dipole_increase_amp_3[i])
            # t+= Hybrid_dipole_down_dt_3  
        # t+20e-3
        # quad_coils.constant(t, Slosh_quad, "A") 
        # t+=Slosh_wait
        # quad_coils.constant(t, decompress_quad, "A") 
        # t+=Slosh_hold
        t+=bias_z_coils.sine_ramp(t, Slosh_wait,mt_bias_z_compress, Slosh_quad, 1e4, units="A") 
        t+=Slosh_wait
        bias_z_coils.constant(t, mt_bias_z_compress, "A") 
        t+=Slosh_hold
        #t+= bias_z_coils.sine(t,ModulateTime,mt_bias_z_compress, 2 * pi * ModulateFrequency, 3*pi/2 , (1+Modulate_Z_Bias)*mt_bias_z_compress, 1e4,units="A")
        
    if ParametricHeatingDipole:
        South_dipole_Increase = linspace(0,2*pi,21)
        Modulate_dt=1/(20*float(ModulateFrequency))

        for i in range(int(ModulateTime*ModulateFrequency)):
                for j in range(20):
                    south_dipole_aom.setamp(t,south_amp_4+0.02*south_amp_4*math.sin(South_dipole_Increase[j]))
                    t+= Modulate_dt
        
        t+=ParametricHold
    
    # repump_laser_shutter.open(t-2500e-3) 
    # repump_laser_shutter.close(t-2000e-3) 
    # repump_laser_shutter.open(t-1500e-3) 
    # repump_laser_shutter.close(t-1000e-3) 
    if Find_Green_Trap:     
        Dynamic_LG_Mode_AOM.enable(t)
        Dynamic_LG_Mode_AOM.setamp(t, 0.36)
        Static_LG_Mode_AOM.enable(t)
    
    #[AST] To check the purity of the sate
    if Purity_of_State:
        quad_coils.constant(t, 0.2)
        t+=3e-3
    
    add_time_marker(t, "Hybrid evaporation finished",verbose = verbose)
    
if s07p5_Trap_for_Exp:
    
    add_time_marker(t, "Loading Exp Trap",verbose = verbose)   
    
    #Gradually turn get rid of the Quad field and increase the Optical DPT depth
 
    if Single_beam_trap:
        South_dipole_increase_amp = linspace(south_amp_start,south_amp_end,51)
        Exp_Trap_dt = Exp_trap_load_t/50.0
        for i in range(50):
            south_dipole_aom.setamp(t,South_dipole_increase_amp[i])
            t+= Exp_Trap_dt             
    
    if Sheet_trap:
        South_dipole_increase_amp = linspace(south_amp_start,south_amp_end,51)
        Sheet_dipole_increase_amp = linspace(sheet_amp_start,sheet_amp_end,51)
        Exp_Trap_dt = Exp_trap_load_t/50.0
        for i in range(50):
            south_dipole_aom.setamp(t,South_dipole_increase_amp[i])
            dipole_sheet_aom.setamp(t,Sheet_dipole_increase_amp[i])
            t+= Exp_Trap_dt            
    
    
    bias_x_coils.sine_ramp(t,Exp_mag_t, mt_bias_x_compress, Exp_Bx_end, 1e4, units="A")
    bias_y_coils.sine_ramp(t,Exp_mag_t, mt_bias_y_compress, Exp_By_end, 1e4, units="A")
    t+=bias_z_coils.sine_ramp(t,Exp_mag_t, mt_bias_z_compress, Exp_Bz_end, 1e4, units="A")
    t+= Exp_trap_hold
    t+=quad_coils.sine_ramp(t,Exp_mag_t, decompress_quad, 0, 1e4, units="A")
    quad_coils.constant(t, -10)
    t+= Exp_trap_hold
    
    add_time_marker(t, "Finished loading Exp Trap",verbose = verbose)

if s08_Load_Uniform_Trap:
    #Here we turn on the ring trap, ramp on the HG mode and turn off the light sheet
    #Enable the ring and static LG mode
    Static_LG_Mode_AOM.enable(t)
    Dynamic_LG_Mode_AOM.enable(t)
    #HG_Mode_AOM.enable(t)
    # south_dipole_aom.disable(t)
    #Calculate our sheet ramp parameters
    dipole_sheet_aom.enable(t)
    South_dipole_reduce_amp_5 = linspace(south_amp_4,0,101)
    Flat_Sheet_increase_amp = linspace(Flat_Sheet_AOM_Amplitude,flat_amp_final,101)
    Uniform_trap_load_dt = Uniform_trap_load_time/100.0
    #Here we ramp our z bias up to load the atoms into the ring
    bias_z_coils.sine_ramp(t,Uniform_trap_load_time, mt_bias_z_compress, Uniform_trap_Z_bias, 1e3, units="A")
    bias_x_coils.sine_ramp(t,Uniform_trap_load_time, mt_bias_x_compress, Uniform_trap_X_bias, 1e3, units="A")
    bias_y_coils.sine_ramp(t,Uniform_trap_load_time, mt_bias_y_compress, Uniform_trap_Y_bias, 1e3, units="A")
    quad_coils.sine_ramp(t,Uniform_trap_load_time, decompress_quad, Uniform_trap_quad, 1e3, units="A")
    #HG_Mode_AOM.amplitude.ramp(t,Rotating_trap_turn_on_time/3, HG_Mode_initial_amp, HG_Mode_final_amp, 1e3)
    for i in range(100):
        dipole_sheet_aom.setamp(t,Flat_Sheet_increase_amp[i])
        south_dipole_aom.setamp(t,South_dipole_reduce_amp_5[i])
        t+= Uniform_trap_load_dt
    
    south_dipole_aom.disable(t)
    
    dipole_sheet_aom.disable(t)
    t+=Uniform_trap_wait
        
if s09_Spin_Rotating_Trap:
    #Time to try spinning our atoms, first we turn on the rotating mode
    Dynamic_LG_Mode_AOM.enable(t)
    t+=Dynamic_LG_Mode_AOM.amplitude.ramp(t,Rotating_trap_turn_on_time, Dynamic_LG_Amp_initial, Dynamic_LG_Amp_final, 1e3)
    
    # Dynamic_LG_Mode_AOM.setfreq(t, Dynamic_LG_freq_final*MHz)
    # t+=initial_spin

    # #Dynamic_LG_Mode_AOM.frequency.ramp(t, Rotating_trap_spin_time, Dynamic_LG_freq_initial_spin*MHz, Dynamic_LG_freq_final*MHz, 1e3)
        
    t += spin_wait
    Static_LG_Mode_AOM.disable(t)
    Dynamic_LG_Mode_AOM.disable(t)
    t+=vortex_expansion

if s10_RFPulse: 
    add_time_marker(t, "Testing RF",verbose = verbose)

    rf_evap.setamp(t, RFPulse_Amp)
    rf_evap.setfreq(t, RF_start*MHz)
    t+=RF_set_wait
    
    if RFPulse_Sweep:
        rf_evap.enable(t)
        t += rf_evap.frequency.exp_ramp_t(t,RFPulse_Time, RF_start* MHz, RF_end*MHz, 1, 
        (1.0*int(9000*RFPulse_Time))/RFPulse_Time,truncation=truncation_compress_evaporation, truncation_type='exponential')
    else:
        rf_evap.enable(t)
        t+=RFPulse_Time
    
    rf_evap.disable(t)
    add_time_marker(t, "End Testing RF",verbose = verbose)

#[AST] Experiment for quantum delta kicked rotor
# tau = Delta kick pulse duration, this is set by the pulse controller HP 8012B Pulse generator provided by Nino. Targeting tau = 500ns for both kicks
# kick_double = a kick of kick_amp_1 and gap of T_1 + kick of kick_amp_2 and gap of T_2
if s11_QDKR: 
    add_time_marker(t, "Quantum Delta Kicked Rotor Experiemnt started",verbose = verbose)
    ## Testing with 3D MOT beams
    #master_laser_shutter.open(t)
    #science_mot_shutter.open(t)
    #science_trap_aom.setamp(t,kick_amp)
    
    #    # Actual Kick laser AOM pre 24 06 2024
    #    Dynamic_LG_Mode_AOM.setamp(t,kick_amp_1)
    #    t+=kick_drop #Wait for 10ms

    #if Single_kick:
    #    for i in range(int(kicks)):
    #       Dynamic_LG_Mode_AOM.enable(t)
    #       t+= tau #Delta kick pulse duration
    #        Dynamic_LG_Mode_AOM.disable(t)
    #        t+= T_1-tau #500e-9 #500ns set by the HP 8012B Pulse generator
    
    #if Double_kick:
    #    for i in range(int(kicks)):
    #       Dynamic_LG_Mode_AOM.enable(t)
    #        t+= tau #Delta kick pulse duration but actually 500ns set by the HP 8012B Pulse generator
    #        Dynamic_LG_Mode_AOM.disable(t)
    #        Dynamic_LG_Mode_AOM.setamp(t,kick_amp_2)
    #        t+= T_1-500e-9 #500ns set by the HP 8012B Pulse generator
    #        Dynamic_LG_Mode_AOM.enable(t)
    #        t+= tau #Delta kick pulse duration but actually 500ns set by the HP 8012B Pulse generator
    #        Dynamic_LG_Mode_AOM.disable(t)
    #        Dynamic_LG_Mode_AOM.setamp(t,kick_amp_1)
    #        t+= T_2-500e-9 #500ns set by the HP 8012B Pulse generator

    # Actual Kick laser AOM pre 24 06 2024
    Kick_aom.setamp(t,kick_amp_1)
    t+=kick_drop #Wait time

    if Single_kick:
        for i in range(int(kick_single)):
            Kick_aom.enable(t)
            t+= tau #Delta kick pulse duration
            Kick_aom.disable(t)
            t+= T_1-tau
    
    if Double_kick:
        for i in range(int(kick_double)): #Each kick has 2 kicks --> a kick of kick_amp_1 and gap of T_1 + kick of kick_amp_2 and gap of T_2
            Kick_aom.enable(t)
            t+= tau
            Kick_aom.disable(t)
            Kick_aom.setamp(t,kick_amp_2)
            t+= T_1-tau
            Kick_aom.enable(t)
            t+= tau
            Kick_aom.disable(t)
            Kick_aom.setamp(t,kick_amp_1)
            t+= T_2-tau
    
    dummy_for_even_number.go_low(t) # To block second arm of kicking laser
    add_time_marker(t, "End QDK",verbose = verbose)
    
    
if s12_Raman: 
    add_time_marker(t, "Testing Raman",verbose = verbose)

    #Set Raman laser Amp and Freq      
    raman_horizontal.setfreq(t, H_Freq*MHz)
    raman_horizontal.setamp(t,H_Amp)
    raman_vertical.setfreq(t, V_Freq*MHz)
    raman_vertical.setamp(t,V_Amp)
    
    #f_evap.setamp(t, 1)
    #rf_evap.setfreq(t, RFFreq*MHz)
    #rf_evap.enable(t)
    #t+=120e-6
    
    if Single_Freq:    
        #Apply Raman pulse to Atoms
        raman_horizontal.enable(t)
        raman_vertical.enable(t)
        t+= Raman_t
        raman_horizontal.disable(t)
        raman_vertical.disable(t)
        
    if Raman_Scan:
        #Here we calculate our ramp parameters, Spend 5us in a single frequency component of 10kHz. Spend 500us in total i.e. 100 steps
        Raman_Freq_Scan = linspace(H_Freq,Scan_Freq_End,101)
        Raman_Amp_Scan = linspace(H_Amp,Scan_Amp_End,101)
        raman_horizontal.enable(t)
        raman_vertical.enable(t)
        #And perform the Raman horizontal frequency scan
        for i in range(101):
            raman_vertical.setfreq(t,Raman_Freq_Scan[i]*MHz)
            raman_vertical.setamp(t,Raman_Amp_Scan[i])
            t+= Raman_Scan_t
        raman_horizontal.disable(t)
        raman_vertical.disable(t)

    rf_evap.disable(t)
    
    add_time_marker(t, "End Testing Raman",verbose = verbose)

#Adding variable hold time for checking trap lifetimes
t+=hold_time #This variable is in MOT stage (s01_Start_Fresh) in RunManager

#Next we image our result!
if Fluorescence_Imaging: 
    
    #Set the Sorensen back to its low voltage so we don't fry our IGBT's upon MOT loading and switch the coils to their imagin values
    sorensen_high.go_low(t)
    sorensen_intermediate.go_low(t)
    
    add_time_marker(t, "Start of Fluorescence imaging",verbose = verbose)
    #Switch off magnetic and optical traps
    if s05_RF_Evaporation:
        if not s06_Decompress:
            rf_evap.disable(t)
    if Dipole_Trap:
        south_dipole_aom.disable(t)
        dipole_sheet_aom.disable(t)
    if s08_Load_Uniform_Trap:
        Static_LG_Mode_AOM.disable(t)
        Dynamic_LG_Mode_AOM.disable(t)
        HG_Mode_AOM.disable(t)
    
    
    quad_coils.constant(t, -10) 
    
    # Set up imaging bias fields
    if Side_Imaging:
        bias_x_coils.constant(t, side_imaging_bias_x, "A")
        bias_y_coils.constant(t, side_imaging_bias_y, "A")
        bias_z_coils.constant(t, side_imaging_bias_z, "A")
    elif Bottom_Imaging:
        bias_x_coils.constant(t, bottom_imaging_bias_x, "A")
        bias_y_coils.constant(t, bottom_imaging_bias_y, "A")
        bias_z_coils.constant(t, bottom_imaging_bias_z, "A")
    
    #Ensure the repump shutter is open and set AOMs and shutters to desired values for imaging
    master_laser_shutter.open(t-200e-3)
    science_trap_aom.disable(t)
    science_repump_aom.disable(t)
    science_mot_shutter.open(t-10e-3)
    if Side_Imaging:
        science_trap_aom.setfreq(t, side_imaging_frequency*MHz)
        science_trap_aom.setamp(t, 0.45)
    elif Bottom_Imaging:
        science_trap_aom.setfreq(t, bottom_imaging_frequency*MHz)
        science_trap_aom.setamp(t, 0.45)
    if rb_imaging_repump:
        repump_laser_shutter.open(t-10e-3) 
        science_repump_aom.setfreq(t, rb_imaging_repump_frequency*MHz)
        science_repump_aom.setamp(t, rb_imaging_repump_amplitude)
    
    #Wait the drop time and centre the exposure on it
    if Side_Imaging:
        t += drop_time-0.5*side_camera_exposure_time
        side_camera.expose(t,'fluorescence_rb87','atoms',side_camera_exposure_time)
    elif Bottom_Imaging:
        bottom_camera.expose(t+ drop_time-0.5*bottom_camera_exposure_time,'fluorescence_rb87', 'atoms')
    
    
    #Enable the light for flourescence imaging wait the exposure of the camera and turn off the light
    if Side_Imaging:
        science_trap_aom.enable(t)
        if rb_imaging_repump:
            science_repump_aom.enable(t-imaging_repump_time)
            science_repump_aom.disable(t)
        t += side_camera_exposure_time
        science_trap_aom.disable(t)
    elif Bottom_Imaging:
        t+= drop_time-0.5*bottom_imaging_flourescence_time
        science_trap_aom.enable(t)
        if rb_imaging_repump:
            science_repump_aom.enable(t-imaging_repump_time)
        t += bottom_imaging_flourescence_time
        if Find_Green_Trap:
            LG_Mode_AOM.disable(t)
            Rotating_trap.disable(t)  
        if rb_imaging_repump:
            science_repump_aom.disable(t-bottom_imaging_flourescence_time)
        science_trap_aom.disable(t)
        t+=0.5*(bottom_camera_exposure_time-bottom_imaging_flourescence_time)

        #If trying to find the dipole beams the following is helpful
    if Find_Dipole_Trap:
        south_dipole_aom.disable(t)
        dipole_sheet_aom.disable(t)
        if Find_Raman_Beams:
            raman_horizontal.disable(t)
            raman_vertical.disable(t)
        # Unused_0.disable(t)
        
    #Wait the interframe time of the camera
    if Side_Imaging:
        t+=side_interframe_time
    elif Bottom_Imaging:
        t+=bottom_interframe_time
    
    #Start exposing the dark frame, enabling the light for the same conditions
    if Side_Imaging:
        t += drop_time-0.5*side_camera_exposure_time
        side_camera.expose(t,'fluorescence_rb87','dark',side_camera_exposure_time)
        science_trap_aom.enable(t)
        if rb_imaging_repump:
            science_repump_aom.enable(t-1e-3)
        t += side_camera_exposure_time
        science_trap_aom.disable(t)
        if rb_imaging_repump:
            science_repump_aom.disable(t)
    elif Bottom_Imaging:
        bottom_camera.expose(t,'fluorescence_rb87', 'dark')
        t+=0.5*bottom_camera_exposure_time-0.5*bottom_imaging_flourescence_time
        science_trap_aom.enable(t)
        if rb_imaging_repump:
            science_repump_aom.enable(t-1e-3)
        t+=bottom_imaging_flourescence_time
        science_trap_aom.disable(t)
        if rb_imaging_repump:
            science_repump_aom.disable(t)        
        t+=0.5*(bottom_camera_exposure_time-bottom_imaging_flourescence_time)
        t+=bottom_interframe_time        
    
if Absorption_Imaging:
    print_time(t,'In Abs Img') #Del
    #Switch off dipole traps
    if s08_Load_Uniform_Trap:
        Static_LG_Mode_AOM.disable(t)
        Dynamic_LG_Mode_AOM.disable(t)
        HG_Mode_AOM.disable(t)
    if Dipole_Trap:
        south_dipole_aom.disable(t)
        dipole_sheet_aom.disable(t)
        print_time(t,'DPT Off') #Del

    
    #Make sure no RF is on
    if s05_RF_Evaporation:
        rf_evap.disable(t)
        print_time(t,'RF Off') #Del
    
    #Switch the coils to their levitation values if levitating, else switch them to imaging values, make sure we dont fry the igbt first though
    sorensen_high.go_low(t)
    sorensen_intermediate.go_low(t)
    if Levitate:
        quad_coils.constant(t, Levitate_quad)
        bias_z_coils.constant(t, Levitate_Z_bias, "A")
        bias_x_coils.constant(t, Levitate_X_bias, "A")
        bias_y_coils.constant(t, Levitate_Y_bias, "A")
        print_time(t,'Set Mag to Lev') #Del
    else:
        quad_coils.constant(t, -10)  
        # Set up imaging bias fields
        if Side_Imaging:
            bias_x_coils.constant(t, side_imaging_bias_x, "A")
            bias_y_coils.constant(t, side_imaging_bias_y, "A")
            bias_z_coils.constant(t, side_imaging_bias_z, "A")
        elif Bottom_Imaging:
            bias_x_coils.constant(t, bottom_imaging_bias_x, "A")
            bias_y_coils.constant(t, bottom_imaging_bias_y, "A")
            bias_z_coils.constant(t, bottom_imaging_bias_z, "A")            
 
    #Set imaging and repump AOM values
    science_repump_aom.setfreq(t, rb_imaging_repump_frequency*MHz)
    science_repump_aom.setamp(t, rb_imaging_repump_amplitude)
    print_time(t,'Set RP Amp Freq') #Del
    master_laser_shutter.open(t-200e-3)
    print_time(t,'MOT Shutter open') #Del
    science_trap_aom.disable(t)
    science_repump_aom.disable(t)
    science_trap_aom.setamp(t, 0)
    print_time(t,'MOT and RP AOM OFF') #Del
    
    if Side_Imaging:
        imaging_push_aom.setfreq(t, side_imaging_frequency * MHz)
        imaging_push_aom.setamp(t, side_imaging_amplitude)
        print_time(t,'Set IMG Amp Freq') #Del
    elif Bottom_Imaging:
        imaging_push_aom.setfreq(t, bottom_imaging_frequency * MHz)
        imaging_push_aom.setamp(t, bottom_imaging_amplitude)      
    
    #Set up and perform imaging repump if we need
    if rb_imaging_repump:
        if Side_Imaging:
            #Open up the repump shutter well before repumping
            repump_laser_shutter.open(t+drop_time-0.5*side_camera_exposure_time-10e-3)
            print_time(t+drop_time-0.5*side_camera_exposure_time-10e-3+repump_laser_shutter.open_delay,'Repump shutter opened for imaging repump')
            print_time(t,'RP Sutter open') #Del
            #Enable the repump and set its properties such that it finishes repumping 100e-6 before imaging
            science_repump_aom.enable(t+drop_time-0.5*side_imaging_pulse_time-imaging_repump_time-100e-6)
            print_time(t+drop_time-0.5*side_imaging_pulse_time-imaging_repump_time-100e-6,'Imaging repump AOM enabled')
            print_time(t,'RP AOM ON') #Del
            #Disable repump 100e-6 before imaging
            science_repump_aom.disable(t+drop_time-0.5*side_imaging_pulse_time-100e-6)
            add_time_marker(t+drop_time-0.5*side_camera_exposure_time-100e-6, "Atoms have been repumped",verbose = verbose)
            print_time(t,'RP AOM OFF') #Del
            if verbose: print ("Repump light turned on for imaging at t=%.9f"%(t+drop_time-0.5*side_camera_exposure_time-imaging_repump_time-100e-6))
        elif Bottom_Imaging:
            #Open up the repump shutter well before repumping
            repump_laser_shutter.open(t+drop_time-0.5*bottom_camera_exposure_time-10e-3)
            print_time(t+drop_time-0.5*bottom_camera_exposure_time-10e-3+repump_laser_shutter.open_delay,'Repump shutter opened for imaging repump')
            #Enable the repump and set its properties such that it finishes repumping 100e-6 before imaging
            science_repump_aom.enable(t+drop_time-0.5*bottom_imaging_pulse_time-imaging_repump_time-100e-6)
            #Disable repump 100e-6 before imaging
            science_repump_aom.disable(t+drop_time-0.5*bottom_imaging_pulse_time-100e-6)
            add_time_marker(t+drop_time-0.5*bottom_imaging_pulse_time-100e-6, "Atoms have been repumped",verbose = verbose)
            if verbose: print ("Repump light turned on for imaging at t=%.9f"%(t+drop_time-0.5*bottom_imaging_pulse_time-100e-6) )           
    else:
        #Ensure repump is turned off otherwise
        science_repump_aom.disable(t)
    
    # Open the imaging shutters early
    master_laser_shutter.open(t-200e-3)
    if Side_Imaging:
        side_imaging_shutter.open(t-1e-3)
        print_time(t-1e-3-side_imaging_shutter.open_delay,'Side imaging shutter triggered to open for absorption imaging')
    elif Bottom_Imaging:
        bottom_imaging_shutter.open(t-10e-3)
        print_time(t-10e-3-bottom_imaging_shutter.open_delay,'Bottom imaging shutter triggered to open for absorption imaging')
    
    # Atoms exposure
    # Start exposing camera during tof, centre the exposure on the drop time
    if Side_Imaging:
        t += drop_time-0.5*side_camera_exposure_time
        print_time(t,'Side camera starting to expose')
        side_camera.expose(t,'absorption_rb87', 'atoms',side_camera_exposure_time)
        t += 0.5*(side_camera_exposure_time-side_imaging_pulse_time)
    if Bottom_Imaging:
        t += drop_time-0.5*bottom_camera_exposure_time
        print_time(t,'Bottom camera starting to expose')
        bottom_camera.expose(t,'absorption_rb87', 'atoms',bottom_camera_exposure_time)
        t += 0.5*(bottom_camera_exposure_time-bottom_imaging_pulse_time)

    #Switch off the levitation field if on, just before the imaging pulse
    if Levitate:
        if Side_Imaging:
            quad_coils.constant(t+0.5*side_imaging_pulse_time-Levitate_switch_off, -10)
            bias_x_coils.constant(t+0.5*side_imaging_pulse_time-Levitate_switch_off, side_imaging_bias_x, "A")
            bias_y_coils.constant(t+0.5*side_imaging_pulse_time-Levitate_switch_off, side_imaging_bias_y, "A")
            bias_z_coils.constant(t+0.5*side_imaging_pulse_time-Levitate_switch_off, side_imaging_bias_z, "A")
            print_time(t,'Mag Lev to Side IMG') #Del
        if Bottom_Imaging:
            quad_coils.constant(t+0.5*bottom_imaging_pulse_time-Levitate_switch_off, -10)
            bias_x_coils.constant(t+0.5*bottom_imaging_pulse_time-Levitate_switch_off, bottom_imaging_bias_x, "A")
            bias_y_coils.constant(t+0.5*bottom_imaging_pulse_time-Levitate_switch_off, bottom_imaging_bias_y, "A")
            bias_z_coils.constant(t+0.5*bottom_imaging_pulse_time-Levitate_switch_off, bottom_imaging_bias_z, "A")
        
    #If trying to find the dipole beams the following is helpful
    if Find_Dipole_Trap:
        south_dipole_aom.disable(t)
        dipole_sheet_aom.disable(t)
        if Find_Raman_Beams:
            raman_horizontal.disable(t)
            raman_vertical.disable(t)
    if Find_Green_Trap: 
        Static_LG_Mode_AOM.disable(t)
        Dynamic_LG_Mode_AOM.disable(t)
    
    #Set the imaging amplitude and frequency at the same time as enabling, as otherwise the novatech misses a clock tick apparently, and enable the light
    if Side_Imaging:
        imaging_push_aom.enable(t)
        print_time(t,'Side imaging light turned on')
        if verbose: print ("Image taken at t = %.9f"%t)
        #Disable the light after imaging
        t += side_imaging_pulse_time
        imaging_push_aom.disable(t)  
        print_time(t,'IMG AOM OFF') #Del
    if Bottom_Imaging:
        imaging_push_aom.enable(t)
        print_time(t,'Bottom imaging light turned on')
        if verbose: print ("Image taken at t = %.9f"%t)
        #Disable the light after imaging
        t += bottom_imaging_pulse_time
        imaging_push_aom.disable(t) 
    
    # Now wait until camera has finished exposing then begin the flat field exposure after waiting the interframe time, making the imaging sequence identical
    if Side_Imaging:
        t += 0.5*(side_camera_exposure_time-side_imaging_pulse_time)
        t+= side_interframe_time
        side_camera.expose(t,'absorption_rb87', 'flat',side_camera_exposure_time)
        #t += 0.5*(side_camera_exposure_time-side_imaging_pulse_time) #[Original]
        t += 0.5*(side_camera_exposure_time-side_imaging_flat_time) #[AST] Added so can vary the flat frame to match abs imaging pixel values
    if Bottom_Imaging:
        t += 0.5*(bottom_camera_exposure_time-bottom_imaging_pulse_time)
        t+= bottom_interframe_time
        bottom_camera.expose(t,'absorption_rb87', 'flat',bottom_camera_exposure_time)
        t += 0.5*(bottom_camera_exposure_time-bottom_imaging_pulse_time)

    #Enable the AOM for imaging
    if Side_Imaging:
        science_repump_aom.enable(t-imaging_repump_time-100e-6)
        science_repump_aom.disable(t-100e-6)
        imaging_push_aom.enable(t)
        if verbose: print ("Image taken at t = %.9f"%t)
        #t += side_imaging_pulse_time #[Original]
        t += side_imaging_flat_time #[AST] Added so can vary the flat frame to match abs imaging pixel values 
        imaging_push_aom.disable(t)   
    if Bottom_Imaging:
        science_repump_aom.enable(t-imaging_repump_time-100e-6)
        science_repump_aom.disable(t-100e-6)
        imaging_push_aom.enable(t)
        if verbose: print ("Image taken at t = %.9f"%t)
        t += bottom_imaging_pulse_time
        imaging_push_aom.disable(t) 
    
    
    # Now wait until camera has finished exposing then begin the dark field exposure after waiting the interframe time and closing the shutters
    if Side_Imaging:
        #t += 0.5*(side_camera_exposure_time-side_imaging_pulse_time) #[Original]
        t += 0.5*(side_camera_exposure_time-side_imaging_flat_time) #[AST] Added so can vary the flat frame to match abs imaging pixel values 
        side_imaging_shutter.close(t)
        repump_laser_shutter.close(t)
        master_laser_shutter.close(t)
        t+= side_interframe_time
        side_camera.expose(t,'absorption_rb87', 'dark',side_camera_exposure_time)
        t +=side_camera_exposure_time
    if Bottom_Imaging:
        t += 0.5*(bottom_camera_exposure_time-bottom_imaging_pulse_time)
        repump_laser_shutter.close(t+20e-3)
        bottom_imaging_shutter.close(t+20e-3)
        master_laser_shutter.close(t+20e-3)
        t+= bottom_interframe_time
        bottom_camera.expose(t,'absorption_rb87', 'dark',bottom_camera_exposure_time)
        t +=bottom_camera_exposure_time
 

# if Faraday_Imaging:
   
    # #Set the Sorensen back to its low voltage so we don't fry our IGBT's upon MOT loading and switch the coils to their imagin values
    # sorensen_high.go_low(t)
    # sorensen_intermediate.go_low(t)
    
    # add_time_marker(t, "Start of Fluorescence imaging",verbose = verbose)
    # #Switch off magnetic and optical traps
    # if s05_RF_Evaporation:
        # if not s06_Decompress:
            # rf_evap.disable(t)
    # if Dipole_Trap:
        # south_dipole_aom.disable(t)
        # dipole_sheet_aom.disable(t)
    # if s08_Load_Uniform_Trap:
        # Static_LG_Mode_AOM.disable(t)
        # Dynamic_LG_Mode_AOM.disable(t)
        # HG_Mode_AOM.disable(t)
    
    
    # quad_coils.constant(t, -10) 
    
    # # Set up imaging bias fields
    # bias_x_coils.constant(t, Faraday_imaging_bias_x, "A")
    # bias_y_coils.constant(t, Faraday_imaging_bias_y, "A")
    # bias_z_coils.constant(t, Faraday_imaging_bias_z, "A")
    
    # #Ensure the repump shutter is open and set AOMs and shutters to desired values for imaging
    # master_laser_shutter.open(t-200e-3)
    # science_trap_aom.disable(t)
    # science_repump_aom.disable(t)
    # science_trap_aom.setamp(t, 0)
    # science_repump_aom.setamp(t, 0)
    # if rb_imaging_repump:
        # repump_laser_shutter.open(t-10e-3) 
        # science_repump_aom.setfreq(t, rb_imaging_repump_frequency*MHz)
        # science_repump_aom.setamp(t, rb_imaging_repump_amplitude)
    
    # #Wait the drop time and centre the exposure on it
    # bottom_camera.expose('Faraday_rb87', t+ drop_time-0.5*bottom_camera_exposure_time, 'atoms')
    
    # #Enable the repump light if repumping, then enable the faraday beam
    # if rb_imaging_repump:
        # science_repump_aom.enable(t-imaging_repump_time)
        # science_repump_aom.disable(t)
    # #Ensure the faraday beam pulse is centred on the exposure
    # t+= drop_time-0.5*Faraday_Imaging_time
    # Faraday_beam.enable(t)
    # t+=Faraday_Imaging_time
    # Faraday_beam.disable(t)
    # #Wait until the end of the exposure
    # t += 0.5*(bottom_camera_exposure_time-Faraday_Imaging_time)
        
    # #Wait the interframe time of the camera
    # t+=bottom_interframe_time
    
    # #Start exposing the dark frame, enabling the light for the same conditions
    # bottom_camera.expose('Faraday_rb87', t, 'dark')
    # t+=0.5*bottom_camera_exposure_time-0.5*Faraday_Imaging_time
    # Faraday_beam.enable(t)
    # t+= Faraday_Imaging_time
    # Faraday_beam.disable(t)
    # t += 0.5*(bottom_camera_exposure_time-Faraday_Imaging_time)
       
    # t+=bottom_interframe_time      
    
####################### END OF EXPERIMENT, NOW SET SOME SENSIBLE DEFAULTS ################################
t += 600e-3
    
bottom_imaging_mirror.go_low(t)
dummy_for_even_number.go_low(t) #[AST] Shutter to block second arm of kicking
mot_mirror_servo.go_low(t)
# NT_engage goes low at end
nt_table_enable.go_low(t)

#Set the shutters to their defaults
#push_beam_shutter.open(t)
push_beam_shutter.close(t)
bottom_imaging_shutter.close(t)
science_mot_shutter.open(t)
# Top_MOT_Beam_Shutter.open(t)
repump_laser_shutter.open(t) 
master_laser_shutter.open(t)

#Ensure the dipole traps are off
south_dipole_aom.setamp(t,0.05)  
dipole_sheet_aom.setamp(t,0.05)
Kick_aom.setamp(t,0.05)
south_dipole_aom.disable(t)  
dipole_sheet_aom.disable(t)
Static_LG_Mode_AOM.disable(t)
#Dynamic_LG_Mode_AOM.disable(t) [Original] this is used as the sheet dipole AOM
Kick_aom.disable(t)
#HG_Mode_AOM.disable(t) [Original] this is used as the south dipole AOM

#Set the coils etc. to their desired values for the MOT load, note the Z bias is set to zero as the IGBT gets hot for its set value
source_coil_bottom.constant(t, source_coil_bottom_current)
source_coil_top.constant(t, source_coil_top_current)
source_coil_north.constant(t, source_coil_north_current)
source_coil_south.constant(t, source_coil_south_current)
bias_x_coils.constant(t, x_bias_MOT_load_current, "A")
bias_y_coils.constant(t, y_bias_MOT_load_current, "A")
bias_z_coils.constant(t, z_bias_MOT_load_current, "A")
quad_coils.constant(t, quad_coil_MOT_load_current, "A")
rubidium_getter.constant(t, getter_standby_current)#, "A")
source_trap_aom.enable(t)
source_repump_aom.enable(t)

# Set cooling AOMs back to defaults
science_trap_aom.enable(t)
science_trap_aom.setfreq(t, rb_science_MOT_trap_frequency*MHz)
science_trap_aom.setamp(t, rb_science_MOT_trap_amplitude)

science_repump_aom.enable(t)
science_repump_aom.setfreq(t, rb_science_MOT_repump_frequency*MHz)
science_repump_aom.setamp(t, rb_science_MOT_repump_amplitude)

imaging_push_aom.enable(t)
imaging_push_aom.setfreq(t, rb_push_frequency*MHz)
imaging_push_aom.setamp(t, rb_push_amplitude)

#Set the Sorensen back to its low voltage so we don't fry our IGBT's upon MOT loading
sorensen_high.go_low(t)
sorensen_intermediate.go_low(t)

#Acquire our analog lines
bias_z_monitor.acquire('Z_Bias_voltage',10e-3,t)
quad_coils_monitor.acquire('Quad_voltage',10e-3,t)
mot_fluorescence.acquire('mot_fluorescence',10e-3,t)
igc_pressure.acquire('IGC_voltage',10e-3,t)


t+=50e-3

stop(t)