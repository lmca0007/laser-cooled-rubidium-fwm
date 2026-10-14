from labscript import *
from labscript_utils.unitconversions import *
from labscript import start, stop, add_time_marker, Trigger, RemoteBLACS

from labscript_devices.PulseBlaster import PulseBlaster
from labscript_devices.NI_DAQmx.labscript_devices import NI_PCIe_6363
from labscript_devices.NI_DAQmx.labscript_devices import NI_PCI_6733
from labscript_devices.NovaTechDDS9M import NovaTechDDS9M
from labscript_devices.Camera import Camera
from labscript_devices.IMAQdxCamera.labscript_devices import IMAQdxCamera
from labscript_devices.AndorSolis.labscript_devices import AndorSolis

PulseBlaster(name='pulseblaster_0', board_number=1) #[AST] board_number used to be 0. When the other pulseblaster (tagged PulseBlaster DDS 1) is connected and if this is kept at 0 --> the pulse blasts switch in BLACS
ClockLine(name='pulseblaster_0_ni_clock', pseudoclock=pulseblaster_0.pseudoclock, connection='flag 0')
ClockLine(name='pulseblaster_0_novatech_clock_0', pseudoclock=pulseblaster_0.pseudoclock, connection='flag 1')
ClockLine(name='pulseblaster_0_novatech_clock_1', pseudoclock=pulseblaster_0.pseudoclock, connection='flag 2')

#[AST] added for fast switching of phase for the Raman beam AOMs
PulseBlaster(name='pulseblaster_1', board_number=0,trigger_device=pulseblaster_0.direct_outputs, trigger_connection='flag 3')

NI_PCIe_6363(name='ni_pcie_6363_0',parent_device=pulseblaster_0_ni_clock, clock_terminal='/ni_pcie_6363_0/PFI0', MAX_name='ni_pcie_6363_0', acquisition_rate = 1e5)

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
StaticDDS(     name='repump_lock_aom',            parent_device=novatechdds9m_1,   connection='channel 3', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line3'})

#Novatech-2 RF outputs
#DDS(           name='Dynamic_LG_Mode_AOM',           parent_device=novatechdds9m_2,   connection='channel 0', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line27'}) [Orignial] Used as the RF supply for the sheet dipole AOM now
DDS(           name='dipole_sheet_aom',           parent_device=novatechdds9m_2,   connection='channel 0', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line27'}) #[AST] using what was used at Dynamic_LG_Mode_AOM as the sheet dipole RF drive 
#DDS(           name='HG_Mode_AOM',         parent_device=novatechdds9m_2,   connection='channel 1', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line28'}) #[Orignial] Used as the RF supply for the south dipole AOM now
DDS(           name='south_dipole_aom',         parent_device=novatechdds9m_2,   connection='channel 1', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line28'}) #[AST] using what was used at HG_Mode_AOM as the sheet dipole RF drive 
StaticDDS(     name='Static_LG_Mode_AOM',          parent_device=novatechdds9m_2,   connection='channel 2', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line29'}) #[Orignial] Cannot be changed to DDS --> BEC User manual iii. Hardware
StaticDDS(     name='Unused_2',            parent_device=novatechdds9m_2,   connection='channel 3', digital_gate={'device':ni_pcie_6363_0,'connection':'port0/line30'})

#Pulseblaster-0 RF outputs
#DDS(           name='dipole_sheet_aom',                     parent_device=pulseblaster_0.direct_outputs,    connection='dds 0') [Original]
DDS(           name='Kick_aom',                     parent_device=pulseblaster_0.direct_outputs,    connection='dds 0') #[AST] using it as the AOM for the kicking laser
#DDS(           name='south_dipole_aom',                        parent_device=pulseblaster_0.direct_outputs, connection='dds 1') #[Original]
DDS(           name='raman_circular',                        parent_device=pulseblaster_0.direct_outputs, connection='dds 1') #[AST] using it as the AOM for the Raman sigma + laser

#[AST] Pulseblaster-1 RF outputs
DDS(           name='raman_horizontal',                     parent_device=pulseblaster_1.direct_outputs,    connection='dds 0')
DDS(           name='raman_vertical',                        parent_device=pulseblaster_1.direct_outputs, connection='dds 1')


#Digital trigger connections for odd devices
## 0-3 on NovaTechDDS9M
DigitalOut(    name='nt_table_enable',      parent_device=ni_pcie_6363_0,    connection='port0/line4')
DigitalOut(    name='mot_mirror_servo',      parent_device=ni_pcie_6363_0,    connection='port0/line5')
DigitalOut(    name='bottom_imaging_mirror',      parent_device=ni_pcie_6363_0,    connection='port0/line6')
DigitalOut(    name='dummy_for_even_number',      parent_device=ni_pcie_6363_0,    connection='port0/line7')
## 8-11 on NovaTechDDS9M

DigitalOut(    name='source_mot_led',      parent_device=ni_pcie_6363_0,    connection='port0/line15')

#Digital triggers for Shutters
# Shutter(       name='imaging_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line17',  delay=(0,0)) #open, close 
Shutter(       name='master_laser_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line18',  delay=(0,0)) #open, close  
Shutter(       name='repump_laser_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line19',  delay=(0,0)) #open, close   
Shutter(       name='bottom_imaging_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line20',  delay=(0,0)) #open, close   
Shutter(       name='side_imaging_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line21',  delay=(0,0)) #open, close   
# Shutter(       name='top_mot_beam_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line22',  delay=(0,0)) #open, close   
Shutter(       name='science_mot_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line23',  delay=(0,0)) #open, close    
Shutter(       name='push_beam_shutter',                    parent_device=ni_pcie_6363_0,    connection='port0/line24',  delay=(0,0)) #open, close 


DigitalOut(    name='sorensen_intermediate',      parent_device=ni_pcie_6363_0,    connection='port0/line25')
DigitalOut(    name='sorensen_high',      parent_device=ni_pcie_6363_0,    connection='port0/line26')
## 27-30 on NovaTechDDS9M (not currently in use)


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
               
#Analog acquisition lines
AnalogIn(      'quad_coils_monitor',                     ni_pcie_6363_0,         'ai9')
AnalogIn(      'bias_z_monitor',                     ni_pcie_6363_0,         'ai10')
AnalogIn(      'mot_fluorescence',                     ni_pcie_6363_0,         'ai11')
AnalogIn(      'igc_pressure',                     ni_pcie_6363_0,         'ai16')

# IMAGING SYSTEM
#Camera( 'side_camera', pulseblaster_0.direct_outputs,    connection='flag 3', BIAS_port=42518, serial_number=0xF31031F54, SDK='IMAQdx', effective_pixel_size=4.2e-6, exposure_time=1e-3,  orientation='side')
#Camera(name='bottom_camera',parent_device=ni_pcie_6363_0,connection='port0/line14', BIAS_port=42521, serial_number=11418, SDK="Andor2", effective_pixel_size=4.5e-6, exposure_time=1e-3, orientation='bottom')

RemoteBLACS(name='imaging_pc', host='bec-krb2-analysis.physics.monash.edu')

# Camera trigger lines
#Trigger(    name='side_camera_trigger', parent_device=pulseblaster_0.direct_outputs, connection='flag 3')#[original]
Trigger(    name='side_camera_trigger', parent_device=pulseblaster_1.direct_outputs, connection='flag 0')#[AST]
Trigger(    name='bottom_camera_trigger', parent_device=ni_pcie_6363_0, connection='port0/line14')

IMAQdxCamera(   name='side_camera', parent_device=side_camera_trigger, connection='trigger', orientation='side', serial_number=0xF31031F54, worker=imaging_pc,
    camera_attributes = {'CameraAttributes::Acquisition::AcquisitionMode': 'Continuous',
    'CameraAttributes::Acquisition::Trigger::TriggerActivation': 'RisingEdge',
    'CameraAttributes::Acquisition::Trigger::TriggerDelayAbs': 0.0,
    'CameraAttributes::Acquisition::Trigger::TriggerMode': 'On',
    'CameraAttributes::Acquisition::Trigger::TriggerSelector': 'FrameStart',
    'CameraAttributes::Acquisition::Trigger::TriggerSource': 'Line1',
    'CameraAttributes::Controls::Exposure::ExposureMode': 'TriggerWidth'},
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

start() 
stop(1)
