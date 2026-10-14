from pylab import *
import socket
import lyse, h5py
from analysislib.krb2 import aliases
from analysislib.krb2 import constants

import time


#Isat_default = 141.81 # bottom
Isat_default = 100000 #2858.0 #+/- 222 - center

hostname = socket.gethostname()

run = lyse.Run(lyse.path)
dataset = lyse.data(lyse.path)

results = {}
result_arrays = {}
with h5py.File(lyse.path) as h5file:
    for orientation, images in h5file["images"].items():
        # Override BIAS pixel size with one from global in case the connection table has not been recompiled since the last update to the value
        # or the BIAS has not been restarted since the last connection table recompilation
        if dataset.get('side_imaging', True):
            pixel_size = dataset.get('side_pixel_size')
        elif dataset.get('bottom_imaging', True):
            pixel_size = dataset.get('bottom_pixel_size')
        print("pixel size:", pixel_size)
        
        for image_type, frameset in images.items():
            #element = "rb87"
            # Comment: Commented out the following lines to get MOT_shot working. It would appear that we were only checking to see what element it is if it is NOT 
            #           an absorption image anyway, and that this script is set up to work for fluorescent images too except we might call them something different to what we used to? 
            #           Needs cleaning up!
            #           - Shaun
            #
            # Comment: I've taking the element choosing code and added it inside the absorption code block so that K absorption images work...not sure if Ok or not 
            #          I think the below check was for backwards compatibility with shots where the Rb absorption image was just called "absorption" rather
            #           than absorption_rb87
            #          - Phil
            #
            # if image_type == "absorption":
            element = image_type.split("_")[1]
            if element not in ['rb85','rb87','k41']:
                # print "found an unusual element"
                continue
            print ("Element: %s"%element)
            element_constants = getattr(constants, element)
            
            if image_type.startswith("absorption"):
                element = image_type.split("_")[1]
                Isat = Isat_default
                isat_name = "_".join([orientation, element, "saturation_intensity"])
                if "Cameras" in h5file["globals"]:
                    
                    #if isat_name in h5file["globals"]["Cameras"].attrs:
                    #    Isat = float(h5file["globals"]["Cameras"].attrs[isat_name])
                    if dataset.get(isat_name, False):
                        Isat = dataset.get(isat_name,Isat)
                
                    
                
                # print Isat
                #Isat = 3800#450#7.2#2000
                # Isat=400
                #Isat = 626
                # Isat = 2500
                atoms = float32(frameset["atoms"])
                flat = float32(frameset["flat"])
                dark = float32(frameset["dark"])

                atoms -= dark
                flat -= dark
                #delta = atoms-1.2*flat
                #flat = 0.8*flat #[AST] Changed the flat frame coefficient to make the background low
                
                key = "%s_%s" % (orientation, element)
                
                
                OD = (-log(atoms/flat) + (flat-atoms)/Isat)
                OD[isnan(OD)] = 0.0
                OD[isinf(OD)] = 0.0
                
                
                
                figure()
                imshow(OD,vmin=0,cmap="gray", interpolation="none")
                
                colorbar()
                title("Optical density (%s, %s)" % (orientation, element))
                # img_path = lyse.path.replace('.h5', '.png')
                # # raman_pulse_period = dataset.get('raman_inter_pulse_time')
                # raman_gate_amp = dataset.get('raman_gate_amplitude')
                # import os
                # img_path = os.path.join(os.path.dirname(img_path), '%.3f.png'%raman_gate_amp)

                # savefig(img_path)
                
                figure()
                imshow(flat,vmin = 0,cmap="gray")
                title("Flat field")
                figure()
                imshow(atoms,vmin = 0,cmap="gray")
                title("Atoms frame")
                figure()
                imshow(dark,vmin = 0,cmap="gray")
                title("Dark frame")
                #figure()
                #imshow(delta,vmin = 0,cmap="gray")
                #title("Delta frame")
                
                
                N = pixel_size**2 * OD.sum()/element_constants.sigma0
                MaxOD = OD.max()
                FlatLevel = flat.sum()
                key = "%s_%s" % (orientation, element)
                results[key + "__N"] = N
                results[key + "__MaxOD"] = MaxOD
                results[key + "__FlatLevel"] = FlatLevel
                results[key + "__Isat"] = Isat
                results["N_ab"] = results[key + "__N"]
                result_arrays[key + "__OD"] = OD
                
                all_fit_rois = fit_rois = ["roi0", "roi1", "roi2","roi3"]
                fit_rois = dataset.get('fit_rois',fit_rois)
                
                for roi_name in fit_rois:
                # for roi_name in dataset.get('fit_rois',["roi0", "roi1", "roi2","roi3"]):
                    try:
                        
                        # get the roi
                        #x1,y1,x2,y2 = dataset[orientation, roi_name] ### Hard-coded!
                        if dataset.get('roi_full',True):
                            x1,y1,x2,y2 = 0,0,2752,2200
                        else:
                            x1,y1,x2,y2 = [dataset.get('roi_x1'),dataset.get('roi_y1'),dataset.get('roi_x2'),dataset.get('roi_y2')]
                        # We may only be saving part of the chip, so readjust the coordinates to take this into account
                        x1, y1 = x1-dataset[orientation, 'roi_left'], y1-dataset[orientation, 'roi_top']
                        x2, y2 = x2-dataset[orientation, 'roi_left'], y2-dataset[orientation, 'roi_top']
                    except:
                        continue
                    if (x2-x1!=0):
                        roi_OD = OD[y1:y2,x1:x2]
                        prefix = key[:-4] + "_" + roi_name
                        
                        roi_N = pixel_size**2 * roi_OD.sum()/element_constants.sigma0
                        results[prefix + "__N"] = roi_N
                        result_arrays[prefix + "__ODROI"] = roi_OD
                # Hack                
                not_fit_rois = [r for r in all_fit_rois if r not in fit_rois]
                
                for roi_name in not_fit_rois:
                    try:
                        
                        # get the roi
                        #x1,y1,x2,y2 = dataset[orientation, roi_name] ### Hard-coded!
                        if dataset.get('roi_full',True):
                            x1,y1,x2,y2 = 0,0,2752,2200
                        else:
                            x1,y1,x2,y2 = [dataset.get('roi_x1'),dataset.get('roi_y1'),dataset.get('roi_x2'),dataset.get('roi_y2')]
                        # We may only be saving part of the chip, so readjust the coordinates to take this into account
                        x1, y1 = x1-dataset[orientation, 'roi_left'], y1-dataset[orientation, 'roi_top']
                        x2, y2 = x2-dataset[orientation, 'roi_left'], y2-dataset[orientation, 'roi_top']
                    except:
                        continue
                    if (x2-x1!=0):
                        roi_OD = OD[y1:y2,x1:x2]
                        prefix = key[:-4] + "_" + roi_name
                        
                        roi_N = pixel_size**2 * roi_OD.sum()/element_constants.sigma0
                        results[prefix + "__N"] = roi_N
                        
                        
            elif image_type.startswith("fluoro"):
                atoms = float64(frameset["atoms"])
                dark = float64(frameset["dark"])
                OD = atoms - dark
                N = OD.sum()
                MaxOD = OD.max()
                
                key = "%s_%s" % (orientation, element)
                results[key + "__N"] = N
                results[key + "__MaxOD"] = MaxOD
                result_arrays[key + "__OD"] = OD
                
run.save_results_dict(results)
for k, v in result_arrays.items():
    run.save_result_array(k, v)
