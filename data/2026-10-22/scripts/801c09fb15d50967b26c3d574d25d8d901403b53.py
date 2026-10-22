from labscript import *
from labscript_utils.unitconversions import *
from labscript import start, stop, add_time_marker, Trigger
try:
    from labscript import RemoteBLACS
except ImportError:  # labscript >= 3.2 (e.g. an offline install) moved it
    from labscript.remote import RemoteBLACS

from labscript_devices.PulseBlaster import PulseBlaster
from labscript_devices.NI_DAQmx.labscript_devices import NI_PCIe_6363
from labscript_devices.NI_DAQmx.labscript_devices import NI_PCI_6733
from labscript_devices.NovaTechDDS9M import NovaTechDDS9M
from labscript_devices.IMAQdxCamera.labscript_devices import IMAQdxCamera
from labscript_devices.AndorSolis.labscript_devices import AndorSolis
from labscript.functions import print_time

'''
Rubidium Vapour 4-Wave Mixing Experiment

Sequence: MOT load -> CMOT -> PGC -> hold/drop -> fluorescence or absorption
imaging (side or bottom camera), then the between-shot MOT-loading defaults.

Globals: globals/fwm_globals.h5 (experiment parameters + Cameras/Magneatos calibrations).
'''


####### START CONNECTION TABLE  ########
#
# !! This must match connection_table.py in BLACS on the lab PC !!
# BLACS rejects any shot whose connection table is not a subset of its own, so
# do not rename, remove or rewire devices here. Hardware the FWM sequence does
# not use stays defined and is parked (gated off) in the sequence below.
# The coil unit conversions read the Magneatos globals, keep those values identical.

# --- Clocking ---
PulseBlaster(name='pulseblaster_0', board_number=1) #[AST] board_number used to be 0. When the other pulseblaster (tagged PulseBlaster DDS 1) is connected and if this is kept at 0 --> the pulse blasts switch in BLACS
ClockLine(name='pulseblaster_0_ni_clock', pseudoclock=pulseblaster_0.pseudoclock, connection='flag 0')
ClockLine(name='pulseblaster_0_novatech_clock_0', pseudoclock=pulseblaster_0.pseudoclock, connection='flag 1')
ClockLine(name='pulseblaster_0_novatech_clock_1', pseudoclock=pulseblaster_0.pseudoclock, connection='flag 2')

# Second PulseBlaster (triggered by pb0 flag 3), added for fast Raman phase switching
PulseBlaster(name='pulseblaster_1', board_number=0,trigger_device=pulseblaster_0.direct_outputs, trigger_connection='flag 3')

NI_PCIe_6363(name='ni_pcie_6363_0',parent_device=pulseblaster_0_ni_clock, clock_terminal='/ni_pcie_6363_0/PFI0', MAX_name='ni_pcie_6363_0',acquisition_rate=5e4)
NI_PCI_6733 (name='ni_pci_6733_0', parent_device=pulseblaster_0_ni_clock, clock_terminal='/ni_pcie_6363_0/PFI0', MAX_name='ni_pci_6733_0')

NovaTechDDS9M(name='novatechdds9m_0', parent_device=pulseblaster_0_novatech_clock_0, com_port='com6')
NovaTechDDS9M(name='novatechdds9m_1', parent_device=pulseblaster_0_novatech_clock_1, com_port='com7')
NovaTechDDS9M(name='novatechdds9m_2', parent_device=pulseblaster_0_novatech_clock_1, com_port='com10')

# --- NovaTech RF outputs (digital gates on ni_pcie_6363_0 port0) ---
# Novatech-0
DDS(           name='science_trap_aom',           parent_device=novatechdds9m_0,   connection='channel 0', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line8'})
DDS(           name='rf_evap',         parent_device=novatechdds9m_0,   connection='channel 1', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line9'})
StaticDDS(     name='source_trap_aom',          parent_device=novatechdds9m_0,   connection='channel 2', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line10'})
StaticDDS(     name='master_lock_aom',            parent_device=novatechdds9m_0,   connection='channel 3', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line11'})
# Novatech-1 (ch3 was previously the Faraday beam)
DDS(           name='science_repump_aom',           parent_device=novatechdds9m_1,   connection='channel 0', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line0'})
DDS(           name='imaging_push_aom',         parent_device=novatechdds9m_1,   connection='channel 1', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line1'})
StaticDDS(     name='source_repump_aom',          parent_device=novatechdds9m_1,   connection='channel 2', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line2'})
StaticDDS(     name='repump_lock_aom',            parent_device=novatechdds9m_1,   connection='channel 3', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line3'})
# Novatech-2 (ch0 was Dynamic_LG_Mode_AOM, ch1 was HG_Mode_AOM; ch2 must stay a StaticDDS, see BEC user manual iii. Hardware)
DDS(           name='dipole_sheet_aom',           parent_device=novatechdds9m_2,   connection='channel 0', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line27'})
DDS(           name='south_dipole_aom',         parent_device=novatechdds9m_2,   connection='channel 1', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line28'})
StaticDDS(     name='Static_LG_Mode_AOM',          parent_device=novatechdds9m_2,   connection='channel 2', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line29'})
StaticDDS(     name='Unused_2',            parent_device=novatechdds9m_2,   connection='channel 3', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line30'})

# --- PulseBlaster RF outputs ---
# Pulseblaster-0 (dds 0 was the sheet dipole, dds 1 the south dipole)
DDS(           name='Kick_aom',                     parent_device=pulseblaster_0.direct_outputs,    connection='dds 0')
DDS(           name='raman_circular',                        parent_device=pulseblaster_0.direct_outputs, connection='dds 1')
# Pulseblaster-1
DDS(           name='raman_horizontal',                     parent_device=pulseblaster_1.direct_outputs,    connection='dds 0')
DDS(           name='raman_vertical',                        parent_device=pulseblaster_1.direct_outputs, connection='dds 1')

# --- Digital lines ---
DigitalOut(    name='nt_table_enable',      parent_device=ni_pcie_6363_0,    connection='port0/line4')
DigitalOut(    name='mot_mirror_servo',      parent_device=ni_pcie_6363_0,    connection='port0/line5')
DigitalOut(    name='dummy_for_even_number',      parent_device=ni_pcie_6363_0,    connection='port0/line7') # kick-laser second-arm shutter
DigitalOut(    name='source_mot_led',      parent_device=ni_pcie_6363_0,    connection='port0/line15')
DigitalOut(    name='sorensen_high',      parent_device=ni_pcie_6363_0,    connection='port0/line26')
DigitalOut(    name='sorensen_intermediate',      parent_device=ni_pcie_6363_0,    connection='port0/line25')
DigitalOut(    name='bottom_imaging_mirror',      parent_device=ni_pcie_6363_0,    connection='port0/line6')


# --- Coils and getter (analog outputs) ---
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

# --- Analog inputs (NI_PCIe_6363) ---
AnalogIn(      'quad_coils_monitor',                     ni_pcie_6363_0,         'ai9')
AnalogIn(      'bias_z_monitor',                     ni_pcie_6363_0,         'ai10')
AnalogIn(      'mot_fluorescence',                     ni_pcie_6363_0,         'ai11')
AnalogIn(      'igc_pressure',                     ni_pcie_6363_0,         'ai16')


# --- Shutters, delay=(open, close) ---
Shutter(       name='master_laser_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line18',  delay=(0,0)) #open, close
Shutter(       name='repump_laser_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line19',  delay=(3.59e-3,3.32e-3)) #open, close
Shutter(       name='bottom_imaging_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line20',  delay=(3.24e-3,2.45e-3)) #open, close
Shutter(       name='side_imaging_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line21',  delay=(3.2e-3,2.64e-3)) #open, close
Shutter(       name='science_mot_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line23',  delay=(2.82e-3,3.36e-3)) #open, close
Shutter(       name='push_beam_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line24',  delay=(0,0)) #open, close

# --- Cameras (run by the remote BLACS on the imaging PC) ---
RemoteBLACS(name='imaging_pc', host='bec-krb2-analysis.physics.monash.edu')

Trigger(    name='side_camera_trigger', parent_device=pulseblaster_1.direct_outputs, connection='flag 0')
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

####################### INITIAL STATE ################################

# Static 2D MOT AOMs
source_repump_aom.enable(source_repump_aom.t0)
source_repump_aom.setfreq(rb_source_MOT_repump_frequency*MHz)
source_repump_aom.setamp(rb_source_MOT_repump_amplitude)

source_trap_aom.enable(source_trap_aom.t0)
source_trap_aom.setfreq(rb_source_MOT_trap_frequency*MHz)
source_trap_aom.setamp(rb_source_MOT_trap_amplitude)

# laser lock! Be careful!
# should be manually turned on always with the hardware switch,
#but let's do this just to be safe
master_lock_aom.enable(master_lock_aom.t0)
master_lock_aom.setfreq(47*MHz)
master_lock_aom.setamp(0.650)

#Set the Sorensen to its low voltage so we don't fry our IGBT's upon MOT loading, and ensure the bottom imaging mirror is in the correct place
sorensen_high.go_low(t)
sorensen_intermediate.go_low(t)
bottom_imaging_mirror.go_low(t)
dummy_for_even_number.go_low(t) # keep the (unused) kick-laser second-arm shutter closed

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

# Parked hardware: BEC-experiment RF channels unused by FWM. They stay gated off
# for the whole shot. Freq/amp are the values the BEC globals held (Aug 2026), so
# the hardware sees exactly what it did before the cleanup.
dipole_sheet_aom.disable(dipole_sheet_aom.t0)
dipole_sheet_aom.setfreq(t, 110*MHz)
dipole_sheet_aom.setamp(t, 1)

south_dipole_aom.disable(south_dipole_aom.t0)
south_dipole_aom.setfreq(t, 99*MHz)
south_dipole_aom.setamp(t, 1)

raman_horizontal.disable(raman_horizontal.t0)
raman_horizontal.setfreq(t+1e-6, 76*MHz)
raman_horizontal.setamp(t+1e-6, 0.5)

raman_vertical.disable(raman_vertical.t0)
raman_vertical.setfreq(t+1e-6, 88*MHz)
raman_vertical.setamp(t+1e-6, 0.2)

Kick_aom.disable(Kick_aom.t0)
Kick_aom.setfreq(t, 80*MHz)
Kick_aom.setamp(t, 1)

rf_evap.disable(rf_evap.t0)
rf_evap.setfreq(t, 38.5*MHz)
rf_evap.setamp(t, 0.9)

Static_LG_Mode_AOM.disable(Static_LG_Mode_AOM.t0)
Static_LG_Mode_AOM.setfreq(80*MHz)
Static_LG_Mode_AOM.setamp(0.5)

####################### MOT LOAD ################################

# Cycle the push beam shutter, as it tends to get stuck
for i in range(5):
    t+=10e-3
    push_beam_shutter.open(t)
    t+=10e-3
    push_beam_shutter.close(t)

#Ensure the source and central mot shutters are open to start loading the MOT
science_mot_shutter.open(t)
master_laser_shutter.open(t)
push_beam_shutter.open(t)
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

####################### CMOT ################################

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

####################### PGC ################################

if s03_PGC:
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

    #Turn off the repump to get the atoms into F=1
    if repump_wait:
        science_repump_aom.disable(t-repump_wait)
        repump_laser_shutter.close(t-repump_wait)
        print_time(t-repump_wait-repump_laser_shutter.close_delay,'Science Repump shutter triggered to close after PGC')

    add_time_marker(t, "End PGC",verbose = verbose)
    #And switch off the trapping light also
    science_trap_aom.disable(t)
    #And close the shutter if we aren't doing fluorescence imaging
    if not Fluorescence_Imaging:
        master_laser_shutter.close(t)
        science_mot_shutter.close(t)
    print_time(t-science_mot_shutter.close_delay,'Science trap shutter triggered to close')

# Bottom imaging: swing the MOT mirror out and the bottom imaging mirror in.
# (Previously done at the start of the magnetic trap stage.) Without a magnetic
# trap the released cloud falls while the servos move - check timing in the lab.
if Bottom_Imaging:
    mot_mirror_servo.go_high(t)
    if Absorption_Imaging:
        bottom_imaging_mirror.go_high(t+5e-3)

#Adding variable hold time for checking lifetimes
t+=hold_time

####################### FLUORESCENCE IMAGING ################################

if Fluorescence_Imaging:

    #Set the Sorensen back to its low voltage so we don't fry our IGBT's upon MOT loading and switch the coils to their imagin values
    sorensen_high.go_low(t)
    sorensen_intermediate.go_low(t)

    add_time_marker(t, "Start of Fluorescence imaging",verbose = verbose)

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
        if rb_imaging_repump:
            science_repump_aom.disable(t-bottom_imaging_flourescence_time)
        science_trap_aom.disable(t)
        t+=0.5*(bottom_camera_exposure_time-bottom_imaging_flourescence_time)

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

####################### ABSORPTION IMAGING ################################

if Absorption_Imaging:
    #Switch the coils to their imaging values, make sure we dont fry the igbt first though
    sorensen_high.go_low(t)
    sorensen_intermediate.go_low(t)
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
    master_laser_shutter.open(t-200e-3)
    science_trap_aom.disable(t)
    science_repump_aom.disable(t)
    science_trap_aom.setamp(t, 0)

    if Side_Imaging:
        imaging_push_aom.setfreq(t, side_imaging_frequency * MHz)
        imaging_push_aom.setamp(t, side_imaging_amplitude)
    elif Bottom_Imaging:
        imaging_push_aom.setfreq(t, bottom_imaging_frequency * MHz)
        imaging_push_aom.setamp(t, bottom_imaging_amplitude)

    #Set up and perform imaging repump if we need
    if rb_imaging_repump:
        if Side_Imaging:
            #Open up the repump shutter well before repumping
            repump_laser_shutter.open(t+drop_time-0.5*side_camera_exposure_time-10e-3)
            print_time(t+drop_time-0.5*side_camera_exposure_time-10e-3+repump_laser_shutter.open_delay,'Repump shutter opened for imaging repump')
            #Enable the repump and set its properties such that it finishes repumping 100e-6 before imaging
            science_repump_aom.enable(t+drop_time-0.5*side_imaging_pulse_time-imaging_repump_time-100e-6)
            print_time(t+drop_time-0.5*side_imaging_pulse_time-imaging_repump_time-100e-6,'Imaging repump AOM enabled')
            #Disable repump 100e-6 before imaging
            science_repump_aom.disable(t+drop_time-0.5*side_imaging_pulse_time-100e-6)
            add_time_marker(t+drop_time-0.5*side_camera_exposure_time-100e-6, "Atoms have been repumped",verbose = verbose)
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

    #Set the imaging amplitude and frequency at the same time as enabling, as otherwise the novatech misses a clock tick apparently, and enable the light
    if Side_Imaging:
        imaging_push_aom.enable(t)
        print_time(t,'Side imaging light turned on')
        if verbose: print ("Image taken at t = %.9f"%t)
        #Disable the light after imaging
        t += side_imaging_pulse_time
        imaging_push_aom.disable(t)
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
        t += 0.5*(side_camera_exposure_time-side_imaging_flat_time) # flat pulse length can differ to match abs imaging pixel values
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
        t += side_imaging_flat_time
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
        t += 0.5*(side_camera_exposure_time-side_imaging_flat_time)
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

####################### END OF EXPERIMENT, NOW SET SOME SENSIBLE DEFAULTS ################################
# These final values are what BLACS holds between shots (MOT loading state).
t += 600e-3

bottom_imaging_mirror.go_low(t)
dummy_for_even_number.go_low(t) # kick-laser second-arm shutter
mot_mirror_servo.go_low(t)
# NT_engage goes low at end
nt_table_enable.go_low(t)

#Set the shutters to their defaults
push_beam_shutter.close(t)
bottom_imaging_shutter.close(t)
science_mot_shutter.open(t)
repump_laser_shutter.open(t)
master_laser_shutter.open(t)

#Ensure the parked dipole/kick AOMs are off
south_dipole_aom.setamp(t,0.05)
dipole_sheet_aom.setamp(t,0.05)
Kick_aom.setamp(t,0.05)
south_dipole_aom.disable(t)
dipole_sheet_aom.disable(t)
Static_LG_Mode_AOM.disable(t)
Kick_aom.disable(t)

#Set the coils etc. to their desired values for the MOT load
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
