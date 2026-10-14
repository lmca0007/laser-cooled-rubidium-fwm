# Gaussian fit of everything


from pylab import *
from analysislib.common import *
#from lyse import *
import lyse
from scipy import optimize
from scipy.ndimage.interpolation import rotate
import socket
import matplotlib.gridspec as gridspec


from analysislib.krb2.aliases import *

results = {}

run = lyse.Run(lyse.path)
dataset = lyse.data(lyse.path)

fit_od0 = True#dataset.get('fit_od0', False)
fit_clip = dataset.get('fit_clip', 2.5)
fit_clip = 2.0


def gaussian(height, center_x, center_y, width_x, width_y, od0=0):
    """Returns a gaussian function with the given parameters"""
    width_x = float(width_x)
    width_y = float(width_y)
    return lambda y,x: height*exp(
                -(((center_x-x)/width_x)**2+((center_y-y)/width_y)**2)/2) + od0

def gauss_1d(x, x0, sigma_x, peak):
    return peak* exp(-1/2*((x-x0)/sigma_x)**2)

def calc_moments2d(Z):
    Z = Z - Z.min()
    Zs = Z.sum()
    yy, xx = indices(Z.shape)
    x0 = (Z*xx).sum()/Zs
    y0 = (Z*yy).sum()/Zs
    xw = sqrt((Z*(xx-x0)**2).sum()/Zs)/2
    yw = sqrt((Z*(yy-y0)**2).sum()/Zs)/2
    return x0, y0, xw, yw

def plot_results(prefix, image,params):
    ny, nx = image.shape
    x = arange(nx)
    y = arange(ny)
    
    figheight = 8
    sideplotheight = figheight/4
    figwidth = (ny/nx*(figheight - sideplotheight) + sideplotheight)
    # f = figure('atom',figsize=(figwidth,figheight))
    # gs = gridspec.GridSpec(2, 2,width_ratios = [sideplotheight, figwidth - sideplotheight],
                                # height_ratios = [figheight-sideplotheight, sideplotheight])
    gs = gridspec.GridSpec(2, 3,width_ratios = [2,5,0.3],#[sideplotheight, figwidth - sideplotheight],
                                height_ratios = [4,1])#[figheight-sideplotheight, sideplotheight])
    subplot(gs[1])
    title('Optical density')
    if not image.max() < 0 and image.max() > image.min():
        imshow(image,vmin=0,interpolation="nearest")
        coloraxes = subplot(gs[2])
        colorbar(cax=coloraxes)
        ## for changing color of the plot similar to fluorescence image use code below
        #imshow(image,vmin=0,interpolation="nearest", cmap="jet")
        #colorbar()
        
    #title("fit_frame_roi - %s" % (prefix))
    #colorbar()
    subplot(gs[0])
    thermal_peak, x0, y0, sigma_x, sigma_y = params[:5]
    #x0 = 1570
    #y0 = 1700
    if len(params) > 5:
        offset = params[5]
    else:
        offset = 0.0
    if (int(x0)>=0) and (int(x0)<image.shape[1]) and (int(y0)>=0) and (int(y0)<image.shape[0]):
        col = image[:, int(x0)]
        #col=[]
        #for rr in range(size(image[:,int(x0)])):
        #    col += [sum(image[rr,:])]
        row = image[int(y0), :]
        #row =[]
        #for rr in range(size(image[int(y0),:])):
        #    row += [sum(image[:,rr])]
        plot(col,y)
        plot(gauss_1d(y,y0,sigma_y,thermal_peak) + offset,y,'k--',linewidth=1.5)
        axis(ymin=y.max(), ymax=y.min())
        subplot(gs[4])
        plot(x,row,label='data')
        plot(x, gauss_1d(x,x0,sigma_x,thermal_peak) + offset,'k--',linewidth=1.5,label='fit (thermal)')
        axis(xmin=x.min(),xmax=x.max())
    subplots_adjust(bottom=.05, top=.95,left=.05, right=.95, wspace=0, hspace=0)
    for ax in gcf().axes:
        ax.set_xticks([])
        ax.set_yticks([])
    # figure()
    # X,Y = meshgrid(x,y)
    # z_fit = gaussian(thermal_peak, x0, y0, sigma_x, sigma_y, offset)(Y,X)
    # imshow(z_fit-image, cmap="Greys", vmin=0,vmax=0.4)
    # colorbar()

def rebin(f):
    """ Decorator for fit which bins the data (od) and converts the results back to original pixels"""
    def func(prefix, od, binsize=5, **kw):
        if binsize > 1:
            od0 = zeros((int(od.shape[0]/binsize), int(od.shape[1]/binsize)))
            odcrop = od[:od0.shape[0]*binsize,:od0.shape[1]*binsize]
            for i in range(binsize):
                for j in range(binsize):
                    od0 += odcrop[i::binsize,j::binsize]
            od0 /= binsize**2
        else:
            od0 = od
        p, err = f(od0, **kw)
        p[1:5] *= binsize
        if err is not None:
            err[1:5] *= binsize
            plot_results(prefix, od, p)
        else:
            err = [None]*6
        return p, err
    return func

@rebin
def fit(od, fit_od0=True, clip=inf):
    """2D Gaussian fit
        * od is the image to fit
        * fit_od0 tells to leave the "zero" level as a free parameter
        * binsize is the size of the bin (default is 5)
    """
    clip_multiplier = int16(od.ravel() < clip)
    x0, y0, xw, yw = calc_moments2d(od)
    H = od.max()
    y0, x0 = unravel_index(od.argmax(), od.shape) # Works better for small clouds
    p0 = [H, x0, y0, xw, yw]
    #p0 = [7,587.0,426.0,600.0,500.0]
    if fit_od0:
        p0.append(0.0)
    errfunc = lambda p: ravel(gaussian(*p)(*indices(od.shape)) - od) * clip_multiplier
    result = optimize.leastsq(errfunc, p0, full_output=True, epsfcn=1e-6)
    p = result[0]
    
    if result[1] is not None:
        errors = sqrt(result[1].diagonal()) * errfunc(p).std()
    else:
        errors = None
    return p, errors

fit_prefixes = []

images = {}
with lyse.h5py.File(run.h5_path) as h5_file:
    if "/results/eigenfringe_OD" in h5_file:
        for key, val in h5_file["results"]["eigenfringe_OD"].items():
            if key =="OD":
                images['top_rb87__OD'] = val[:]
        if not images:
            for key, val in h5_file["results"]["OD_calc"].items():
                if key.endswith("__OD"):
                    images[key] = val[:]
    else:
        for key, val in h5_file["results"]["OD_calc"].items():
            if key.endswith("__OD"):
                images[key] = val[:]

for key, val in images.items():
    raw_OD = val
    prefix = key[:-4]
    orientation = prefix.split("_")[0]
    
    # default fit rois if any of the code below fails to find the correct key in the dataset
    fit_rois = ["roi0", "roi1", "roi2","roi3"]
    
    
    fit_rois = dataset.get('fit_rois',fit_rois)
    
    # if the rois are not an iterable list/tuple/etc
    # then make it one containing the single string
    # if not hasattr(fit_rois, '__iter__'):
        # fit_rois = [fit_rois]
    if isinstance(fit_rois,str):
        fit_rois = [fit_rois]

    # Iterate over the fit rois
    for roi_name in fit_rois:
        print(roi_name)
        try:
            
            # get the roi
            #x1,y1,x2,y2 = dataset[orientation, roi_name] ### Hard-coded!
            # We may only be saving part of the chip, so readjust the coordinates to take this into account
            #x1, y1 = x1-dataset[orientation, 'roi_left'], y1-dataset[orientation, 'roi_top']
            #x2, y2 = x2-dataset[orientation, 'roi_left'], y2-dataset[orientation, 'roi_top']
            if dataset.get('roi_full',True):
                x1,y1,x2,y2 = 0,0,2752,2200
            else:
                x1,y1,x2,y2 = [dataset.get('roi_x1'),dataset.get('roi_y1'),dataset.get('roi_x2'),dataset.get('roi_y2')]

        except:
            continue
        
        if x2-x1 != 0 and y2-y1 != 0:
            OD = raw_OD[y1:y2,x1:x2]
            prefix = key[:-4] + "_" + roi_name
            # print prefix
            #pixel_size = dataset[orientation,'effective_pixel_size']
            pixel_size = 4.2e-6
            
            # Override BIAS pixel size with one from global in case the connection table has not been recompiled since the last update to the value
            # or the BIAS has not been restarted since the last connection table recompilation
            if dataset.get('side_imaging', True) and dataset.get('absorption_imaging', True):
                pixel_size = dataset.get('side_pixel_size')
            
            elif dataset.get('bottom_imaging', True) and dataset.get('absorption_imaging', True):
                pixel_size = dataset.get('bottom_pixel_size')
                        
            figure("atomfit - " + prefix)
            params, err = fit(prefix, OD, binsize=max(1, int((OD.shape[0]*OD.shape[1])**0.5/200)), fit_od0=fit_od0, clip=fit_clip)
            #params, err = fit(prefix, OD, binsize=2, fit_od0=fit_od0, clip=fit_clip)
            
            # pixel_size = 4.68e-6
            try:
                if (err[0] != None) and (params[1]>0) and (params[2]>0) and (params[1]<OD.shape[1]) and (params[2]<OD.shape[0]) and (params[3] < 0.8*OD.shape[1]) and (params[4] < 0.8*OD.shape[0]):
                    
                    N = (params[4]*params[3]*params[0] * pixel_size**2/2.9e-13 * 2*pi)
                    u_N = N*sqrt( (err[4]/params[4])**2 + (err[3]/params[3])**2 + (err[0]/params[0])**2 )
                    # print u_N
                else:
                    N = 0
                    u_N = nan
            except:
               N = 0
               u_N = nan
               params = [nan]*5
               err = [nan]*5
            if err[0] == None:
                err = [nan]*5

            results[prefix + "__N"] = abs(N)
            results[prefix + "__u_N"] = abs(u_N)
            results[prefix + "__Amp"] = abs(params[0])
            results[prefix + "__x"] = nan if N==0 else params[1]
            results[prefix + "__u_x"] = nan if N==0 else abs(err[1])
            results[prefix + "__y"] = nan if N==0 else params[2]
            results[prefix + "__u_y"] = nan if N==0 else abs(err[2])
            results[prefix + "__wx"] = nan if N==0 else abs(params[3])
            results[prefix + "__u_wx"] = nan if N==0 else abs(err[3])
            results[prefix + "__wy"] = nan if N==0 else abs(params[4])
            results[prefix + "__u_wy"] = nan if N==0 else abs(err[4])
            results[prefix + "__pixel_size"] = pixel_size
            fit_prefixes.append(prefix)
            

if len(fit_prefixes) > 0:
    prefix = fit_prefixes[0]
    results["N"] = results[prefix + "__N"]
    results["u_N"] = results[prefix + "__u_N"]
    results["Amp"] = results[prefix + "__Amp"]
    results["x"] = results[prefix + "__x"]
    results["u_x"] = results[prefix + "__u_x"]
    results["y"] = results[prefix + "__y"]
    results["u_y"] = results[prefix + "__u_y"]
    results["wx"] = results[prefix + "__wx"]
    results["u_wx"] = results[prefix + "__u_wx"]
    results["wy"] = results[prefix + "__wy"]
    results["u_wy"] = results[prefix + "__u_wy"]
    results["pixel_size"] = results[prefix + "__pixel_size"]

# print(results)
for k, v in results.items():
    run.save_result(k, v)
