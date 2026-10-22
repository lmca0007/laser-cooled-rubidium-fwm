from pylab import *
import lyse, h5py
from analysislib.krb2 import constants

Isat_default = 100000

run = lyse.Run(lyse.path)
dataset = lyse.data(lyse.path)


def get_roi(shape, orientation):
    """ROI (x1, y1, x2, y2) in pixels. The roi_* globals are side camera pixels, so other cameras use the full frame."""
    ny, nx = shape
    if dataset.get('roi_full', True) or orientation != 'side':
        return 0, 0, nx, ny
    return [int(dataset.get(k)) for k in ('roi_x1', 'roi_y1', 'roi_x2', 'roi_y2')]


results = {}
result_arrays = {}
with h5py.File(lyse.path, 'r') as h5file:
    # Shots with Absorption_Imaging and Fluorescence_Imaging both off have no camera exposures, so no images group
    if "images" not in h5file:
        print("No images in this shot (imaging disabled?), skipping OD calculation")
    for orientation, images in h5file.get("images", {}).items():
        # The camera pixel size comes from the Cameras globals, in case the connection table has not been recompiled
        pixel_size = dataset.get(orientation + '_pixel_size')
        print("pixel size (%s):" % orientation, pixel_size)

        for image_type, frameset in images.items():
            if not hasattr(frameset, 'keys'):
                continue
            element = image_type.split("_")[-1]
            if element != 'rb87':
                continue
            element_constants = getattr(constants, element)
            key = "%s_%s" % (orientation, element)

            # The Andor camera saves frames as (1, ny, nx), the IMAQdx camera as (ny, nx)
            if image_type.startswith("absorption"):
                Isat = dataset.get("_".join([orientation, element, "saturation_intensity"]), Isat_default)
                atoms = squeeze(float32(frameset["atoms"]))
                flat = squeeze(float32(frameset["flat"]))
                dark = squeeze(float32(frameset["dark"]))

                atoms -= dark
                flat -= dark

                # Pixels with no signal in either frame carry no information, so set their OD to 0
                valid = (atoms > 0) & (flat > 0)
                OD = zeros(atoms.shape, dtype=float32)
                OD[valid] = -log(atoms[valid] / flat[valid]) + (flat[valid] - atoms[valid]) / Isat

                figure()
                imshow(OD, vmin=0, cmap="gray", interpolation="none")
                colorbar()
                title("Optical density (%s, %s)" % (orientation, element))
                figure()
                imshow(flat, vmin=0, cmap="gray")
                title("Flat field")
                figure()
                imshow(atoms, vmin=0, cmap="gray")
                title("Atoms frame")
                figure()
                imshow(dark, vmin=0, cmap="gray")
                title("Dark frame")

                results[key + "__N"] = pixel_size**2 * OD.sum() / element_constants.sigma0
                results[key + "__MaxOD"] = OD.max()
                results[key + "__FlatLevel"] = flat.sum()
                results[key + "__Isat"] = Isat
                results["N_ab"] = results[key + "__N"]
                result_arrays[key + "__OD"] = OD

                fit_rois = dataset.get('fit_rois', ["roi0"])
                if isinstance(fit_rois, str):
                    fit_rois = [fit_rois]
                x1, y1, x2, y2 = get_roi(OD.shape, orientation)
                if x2 - x1 != 0 and y2 - y1 != 0:
                    roi_OD = OD[y1:y2, x1:x2]
                    for roi_name in fit_rois:
                        prefix = key + "_" + roi_name
                        results[prefix + "__N"] = pixel_size**2 * roi_OD.sum() / element_constants.sigma0
                        result_arrays[prefix + "__ODROI"] = roi_OD

            elif image_type.startswith("fluoro"):
                atoms = squeeze(float64(frameset["atoms"]))
                dark = squeeze(float64(frameset["dark"]))
                OD = atoms - dark
                results[key + "__N"] = OD.sum()
                results[key + "__MaxOD"] = OD.max()
                result_arrays[key + "__OD"] = OD

run.save_results_dict(results)
for k, v in result_arrays.items():
    run.save_result_array(k, v)
