from __future__ import division
from lyse import *
from pylab import *
from scipy.optimize import leastsq
from scipy.special import spence, zeta
from scipy.signal import fftconvolve
import numpy
import matplotlib.gridspec as gridspec
import time
import uncertainties
from scipy.ndimage.interpolation import rotate
from analysislib.common.traces import curve_fit

from analysislib.krb import aliases
g2_1 = 1.644934057834575
lambda_Rb = 780e-9
u = 1.660539e-27
m_Rb = 86.9129*u
k_B = 1.38065e-23
hbar = 1.05457148e-34
bohr_radius = 52.9177211e-12
a_s_Rb = 100.4*bohr_radius

def rebin(a, factor):
    M, N = a.shape
    m, n = M/factor, N/factor
    #if m<M:
    if m<M:
        # print m, M, n, N
        return a.reshape((int(m),int(M/m),int(n),int(N/n))).mean(3).mean(1)
    else:
        return numpy.repeat(np.repeat(a, m/M, axis=0), n/N, axis=1)

def bokeh_blur(image, r=10):
    """Convolves the image with a disc of radius r pixels"""
    from scipy.signal import fftconvolve
    # Make a disc!
    ny, nx = image.shape
    xr = min(r, floor(nx/2+1))
    yr = min(r, floor(ny/2+1))
    x = linspace(-xr,xr,2*xr+1)
    y = linspace(-yr,yr,2*yr+1)
    Y,X = meshgrid(x,y)
    disc = zeros(X.shape)
    disc[(X**2 + Y**2) < r**2] = 1
    # Normalise the disc to unit integral:
    disc /= disc.sum()
    # Convolve using the Fourier method:
    result = fftconvolve(image, disc,mode='same')
    return result
        
def moments(image, usemax=False):
    if usemax:
        # Blur by 10 pixels to diminish background noise
        image = bokeh_blur(image)
    total = image.sum()
    Y,X = indices(image.shape)
    if usemax:
        y0,x0 = [item[0] for item in where(image == image.max())]
    else:
        x0 = (X*image).sum()/total
        y0 = (Y*image).sum()/total
    col = image[:, int(x0)]
    sigma_y = sqrt(abs((arange(col.size)-y0)**2*col).sum()/abs(col.sum()))
    row = image[int(y0), :]
    sigma_x = sqrt(abs((arange(row.size)-x0)**2*row).sum()/abs(row.sum()))
    height = total/(exp(-1/2*((X-x0)/sigma_x)**2 - 1/2*((Y-y0)/sigma_y)**2)).sum()
    return x0, y0, sigma_x, sigma_y, height

def get_offset(image):
    Y,X = indices(image.shape)
    clipped_image = image - mean(image)
    clipped_image[clipped_image < 0] = 0
    x0, y0, sigma_x, sigma_y, height = moments(clipped_image,usemax=True)
    ellipse_radius = 3 # standard deviations
    while True and ellipse_radius > 0:
        condition = ((X-x0)/sigma_x)**2 + ((Y - y0)/sigma_y)**2 > ellipse_radius**2
        if len(image[condition]):
            break
        ellipse_radius -= 1
    offset = mean(image[condition])
    return offset

def get_gaussian_guess(image):
    offset = get_offset(image)
    x0, y0, sigma_x, sigma_y, height = moments(image - offset, usemax=True)
    return x0, y0, sigma_x, sigma_y, height, offset

def gauss_1d(x, x0, sigma_x, peak):
    return peak* exp(-1/2*((x-x0)/sigma_x)**2)

def gauss_2d(X, Y, x0, y0, sigma_x, sigma_y, peak):
    return peak*exp(-1/2*((X-x0)/sigma_x)**2 - 1/2*((Y-y0)/sigma_y)**2)

def tf_1d(x, x0, Rx, peak):
    result = (1 - (x-x0)**2/Rx**2)
    result[result < 0] = 0
    result = peak*result**(3/2)
    return result
    
def tf_2d(X, Y, x0, y0, Rx, Ry, peak):
    result = (1 - (X-x0)**2/Rx**2 - (Y-y0)**2/Ry**2)
    result[result < 0] = 0
    result = peak*result**(3/2)
    return result
    
def enh_gauss_1d(x, x0, sigma_x, peak):
    gaussian = exp(-1/2*((x-x0)/sigma_x)**2)
    result = peak*spence(1-gaussian)/g2_1
    return result
    
def enh_gauss_2d(X, Y, x0, y0, sigma_x, sigma_y, peak):
    gaussian = exp(-1/2*((X-x0)/sigma_x)**2 - 1/2*((Y-y0)/sigma_y)**2)
    result = peak*spence(1-gaussian)/g2_1
    return result
    
def bec_1d(x, x0, Rx, sigma_x, tf_peak, thermal_peak, offset):
    result = tf_1d(x,x0,Rx,tf_peak) + enh_gauss_1d(x,x0,sigma_x,thermal_peak) + abs(offset)
    return result
    
def bec_2d(X, Y, x0, y0, Rx, Ry, sigma_x, sigma_y, tf_peak, thermal_peak, offset):
    result = tf_2d(X,Y,x0,y0,Rx,Ry,tf_peak) + enh_gauss_2d(X,Y,x0,y0,sigma_x,sigma_y,thermal_peak) + abs(offset)
    return result
    
def get_roi_and_offset(image,params):
    ny, nx = image.shape
    Y,X = indices(image.shape)
    x0, Rx, tf_peak_x, offset_x = params['xparams']
    y0, Ry, tf_peak_y, offset_y = params['yparams']
    # Determine the extent of the image:
    xwidth = 4.2*abs(Rx)
    ywidth = 4.2*abs(Ry)
    # Get the background offset of the image:
    background = image[((Y-y0)/ywidth)**2 + ((X-x0)/xwidth)**2 > 1]
    offset = average(background)
    if isnan(offset):
        offset = 0
    # Make it square:
    xwidth = ywidth = max(xwidth,ywidth)    
    miny = int(y0 - ywidth)
    maxy = int(y0 + ywidth)
    minx = int(x0 - xwidth)
    maxx = int(x0 + xwidth)
    # Keep it in bounds (might not be square now)
    miny = max(miny,0)
    minx = max(minx,0)
    maxy = min(ny - 1, maxy)
    maxx = min(nx - 1, maxx)
    # clip it until the limits are all multiples of 12 (will allow
    # integer rebinning of image by 2,3,4 and 6 pixels):
    miny += (int(y0)-miny) % 12
    maxy -= (maxy-int(y0)) % 12
    minx += (int(x0)-minx) % 12
    maxx -= (maxx-int(x0)) % 12
    
    # return the ROI, new centroids and offset:
    return image[miny:maxy, minx:maxx], x0-minx, y0-miny, minx, miny, offset
      
def fit_tf_to_crosshairs_independent(image,initial_guess):
    x0,Rx,tf_peak_x,offset_x = initial_guess['xparams']
    y0,Ry,tf_peak_y,offset_y = initial_guess['yparams']
    ny, nx = image.shape
    x = arange(nx)
    y = arange(ny)
    def tf_1d_with_offset(x, x0, Rx, peak, offset):
        return tf_1d(x, x0, Rx, peak) + abs(offset)
    # We iterate until the x0,y0 centroid converges:
    
    centroids_seen = []
    while (int(x0),int(y0)) not in centroids_seen:
        if not (0 < x0 < nx-1 and 0 < y0 < ny-1):
            raise RuntimeError('fit failed, centroid moved outside image')
        centroids_seen.append((int(x0),int(y0)))
        col = image[:, int(x0)]
        row = image[int(y0), :]
        colparams, colunc = curve_fit(tf_1d_with_offset, y, col, [y0,Ry,tf_peak_y,offset_y],xtol=0.001)
        rowparams, rowunc = curve_fit(tf_1d_with_offset, x, row, [x0,Rx,tf_peak_x,offset_x],xtol=0.001)
        print(rowparams)
        x0,Rx,tf_peak_x,offset_x = rowparams
        y0,Ry,tf_peak_y,offset_y = colparams
        print(x0)
    return {'xparams':rowparams,'yparams':colparams}

def fit_wings_2d_full(image,initial_guess):
    
    ny, nx = image.shape
    Y,X = indices(image.shape)
    x0,y0,Rx,Ry,tf_peak, tf_offset = initial_guess 

    def tf_residuals(params):
        x0,y0,Rx,Ry,tf_peak, offset = params
        err = tf_2d(X,Y,x0,y0,Rx,Ry,tf_peak) + abs(offset) - image
        return err.ravel()
    
    # Fit the thomas-fermi distribution to find x0 and y0, which will then remain fixed:
    tf_params, tf_covariance, z, z, z = leastsq(tf_residuals, [x0,y0,Rx,Ry,tf_peak, tf_offset],
                                                maxfev=4000,full_output=True)
    reduced_chisquared = (tf_residuals(tf_params)**2).sum()/((nx*ny - len(tf_params)))
    try:
        tf_covariance = reduced_chisquared*tf_covariance
    except TypeError:
        tf_covariance = diag(tf_params)**2
    u_tf_params = [sqrt(tf_covariance[i,i]) for i in range(len(tf_params))]                    
    x0, y0, Rx, Ry, tf_peak, offset = tf_params
    u_x0, u_y0, z, z, z, z = u_tf_params
        
    def tf_residuals_fixed_centroid(params):
        Rx,Ry,tf_peak, offset = params
        err = tf_2d(X,Y,x0,y0,Rx,Ry,tf_peak) + abs(offset) - image_sans_thermal
        return err.ravel()
        
    def thermal_residuals_fixed_centroid(params):
        sigma_x, sigma_y, thermal_peak, offset = params
        err = enh_gauss_2d(masked_x,masked_y,x0, y0, sigma_x, sigma_y, thermal_peak) + abs(offset) - masked_image
        return err.ravel()

    sigma_x, sigma_y, thermal_peak, thermal_offset = Rx,Ry,tf_peak,tf_offset
    image_sans_thermal = image
    
    for i in range(4):
        # Fit the thomas-fermi distribution:
        tf_params, tf_covariance, z, z, z = leastsq(tf_residuals_fixed_centroid,
                                                    [Rx,Ry,tf_peak, tf_offset], maxfev=4000,full_output=True)
        reduced_chisquared = (tf_residuals_fixed_centroid(tf_params)**2).sum()/((nx*ny - len(tf_params)))
        try:
            tf_covariance = reduced_chisquared*tf_covariance
        except TypeError:
            tf_covariance = diag(tf_params)**2
        u_tf_params = [sqrt(tf_covariance[i,i]) for i in range(len(tf_params))]
        Rx, Ry, tf_peak, tf_offset = tf_params
        u_Rx, u_Ry, u_tf_peak, u_tf_offset = u_tf_params
        if tf_peak < 0:
            return 'thermal',None,None
        # Use the results to mask the tf-distribution from the image:
        wings = ((X-x0)/Rx)**2 + ((Y-y0)/Ry)**2 > 1
        masked_image = image[wings]
        masked_x = X[wings]
        masked_y = Y[wings]
        
        # Fit a thermal distribution to what's left:
        thermal_params, thermal_covariance, z, z, z = leastsq(thermal_residuals_fixed_centroid,
                                                              [sigma_x, sigma_y, thermal_peak, thermal_offset],
                                                              maxfev=4000,full_output=True)
        reduced_chisquared = (thermal_residuals_fixed_centroid(thermal_params)**2).sum()/((len(masked_x) - len(thermal_params)))
        try:
            thermal_covariance = reduced_chisquared*thermal_covariance
        except TypeError:
            thermal_covariance = diag(thermal_params)**2
        u_thermal_params = [sqrt(thermal_covariance[i,i]) for i in range(len(thermal_params))]
        sigma_x, sigma_y, thermal_peak, thermal_offset = thermal_params
        u_sigma_x, u_sigma_y, u_thermal_peak, u_thermal_offset = u_thermal_params
        
        # Subtract the thermal fit from the data being used to do the t-f fit:
        thermal_fit = enh_gauss_2d(X,Y,x0,y0,sigma_x,sigma_y,thermal_peak)
        image_sans_thermal = image - thermal_fit
        
    params = x0,y0,Rx,Ry,sigma_x,sigma_y,tf_peak,thermal_peak,tf_offset
    # make positive
    params = [abs(result) for result in params]
    u_params = u_x0,u_y0,u_Rx,u_Ry,u_sigma_x,u_sigma_y,u_tf_peak,u_thermal_peak,u_tf_offset
    return 'bec', params, u_params

def fit_bec_2d_full(image,initial_guess):
    ny, nx = image.shape
    Y,X = indices(image.shape)
    def residuals(params):
        x0,y0,Rx,Ry,sigma_x,sigma_y,tf_peak,thermal_peak,offset = params
        err = bec_2d(X, Y, x0, y0, Rx, Ry, sigma_x, sigma_y, tf_peak, thermal_peak, offset) - image
        return err[image < 7].ravel()
    params, covariance, info, mesg, success = leastsq(residuals, initial_guess,maxfev=4000,full_output=True)
    reduced_chisquared = (residuals(params)**2).sum()/((nx*ny - len(params)))
    per_point_variance = reduced_chisquared
    if covariance is None:
        covariance = diag(params**2)
    else:
        covariance = per_point_variance*covariance
    return params, covariance
    
def fit_thermal_2d_full(image,initial_guess):
    ny, nx = image.shape
    Y,X = indices(image.shape)
    x0,y0,sigma_x,sigma_y,thermal_peak, offset = initial_guess  
       
    def residuals(params):
        x0,y0,sigma_x,sigma_y,thermal_peak, offset = params
        err = gauss_2d(X,Y,x0,y0,sigma_x,sigma_y,thermal_peak) + abs(offset) - image
        return err[image < 2].ravel()
    
    # Fit the gaussian distribution:
    params, covariance, z, z, z = leastsq(residuals, [x0,y0,sigma_x,sigma_y,thermal_peak, offset],
                                          maxfev=4000,full_output=True)
    reduced_chisquared = (residuals(params)**2).sum()/((nx*ny - len(params)))
    try:
        covariance = reduced_chisquared*covariance
    except TypeError:
        covariance = diag(params)**2
    return params, covariance
def fit_atoms(image):   
    # A very rough initial guess of the position and size of the atom cloud:
    x0, y0, sigma_x, sigma_y, height, offset = get_gaussian_guess(image)
    
    # Two independent 1d fits to cross-sections through the cloud, finding just the tf-profile:
    firstpass_params = fit_tf_to_crosshairs_independent(image, initial_guess={
                           'xparams': (x0, sigma_x, height, offset),
                           'yparams': (y0, sigma_y, height, offset)})
    x0, Rx, tf_peak_x, offset_x = firstpass_params['xparams']
    y0, Ry, tf_peak_y, offset_y = firstpass_params['yparams']
    
    # Use this data to obtain a smaller image:
    roi_image, x0, y0,  roi_x, roi_y, offset = get_roi_and_offset(image,firstpass_params)
    
    # Should we rebin the image to save time?
    nx,ny = roi_image.shape
    npts = nx*ny
    desired_scale_factor = sqrt(npts/36000)
    available_scale_factors = array([1,2,3,4,6])
    scale_factor = available_scale_factors[argmin(abs(desired_scale_factor - available_scale_factors))]
    rebinned_image = rebin(roi_image,scale_factor)
    x0,y0,Rx,Ry = x0/scale_factor, y0/scale_factor,Rx/scale_factor,Ry/scale_factor

    # Do a full 2d fit to the smaller image:
    tf_peak = 0.5*(tf_peak_x + tf_peak_y)
    sigma_x, sigma_y, thermal_peak, = Rx,Ry,tf_peak/2
    params, covariance = fit_bec_2d_full(rebinned_image,[x0,y0,Rx,Ry,sigma_x,sigma_y,tf_peak,thermal_peak,offset])
    x0,y0,Rx,Ry,sigma_x,sigma_y,tf_peak,thermal_peak,offset = params
    # Make the widths positive:
    params[2:6] = abs(params[2:6])
    if tf_peak > 0:
        print ('found a BEC')
        # great, we have a BEC!
        # scale the first six of the fit parameters (the spatial ones) back to normal:
        params[:6] *= scale_factor
        # And their uncertainties:
        covariance[:,:6] *= scale_factor
        covariance[:6,:] *= scale_factor
        return 'bec', roi_image, params, covariance, roi_x, roi_y
    else:
        print ('thermal (no BEC found)')
        # It's thermal. Fit a thermal distribution to it instead:
        params, u_params = fit_thermal_2d_full(rebinned_image, [x0, y0, Rx, Ry, 0.5*(tf_peak_x + tf_peak_y), offset])
        # scale the first four of the fit parameters (the spatial ones) back to normal:
        params[:4] *= scale_factor
        # And their uncertainties:
        covariance[:,:4] *= scale_factor
        covariance[:4,:] *= scale_factor
        return 'thermal', roi_image, params, covariance, roi_x, roi_y

def plot_results(regime,image,params,prefix=''):
    ny, nx = image.shape
    x = arange(nx)
    y = arange(ny)
    
    figheight = 8
    sideplotheight = figheight/4
    figwidth = (ny/nx*(figheight - sideplotheight) + sideplotheight)
    f = figure('becfit'+(' - %s'%prefix if prefix else ''),figsize=(figwidth,figheight))
    gs = gridspec.GridSpec(2, 2,width_ratios=[sideplotheight, figwidth - sideplotheight],
                                height_ratios=[figheight-sideplotheight, sideplotheight])
    subplot(gs[1])
    title('Optical density')
    imshow(image)
    subplot(gs[0])
    if regime == 'bec':
        x0,y0,Rx,Ry,sigma_x,sigma_y,tf_peak,thermal_peak, offset = params
    else:
        x0,y0,sigma_x,sigma_y,thermal_peak, offset = params
    col = image[:, int(x0)]
    row = image[int(y0), :]
    plot(col,y)
    if regime == 'bec':
        plot(bec_1d(y,y0,Ry,sigma_y,tf_peak,thermal_peak,offset),y, 'k--',linewidth=1.5)
        plot(enh_gauss_1d(y,y0,sigma_y, thermal_peak),y)
        plot(tf_1d(y,y0, Ry, tf_peak),y)
    else:
        plot(gauss_1d(y,y0,sigma_y,thermal_peak) + offset,y,'k--',linewidth=1.5)
    legend(loc='best')
    axis(ymin=y.max(), ymax=y.min())
    subplot(gs[3])
    plot(x,row,label='data')
    if regime == 'bec':
        plot(x,bec_1d(x,x0,Rx,sigma_x,tf_peak,thermal_peak,offset),'k--',linewidth=1.5,label='total fit')
        plot(x,enh_gauss_1d(x,x0,sigma_x, thermal_peak),label='fit (thermal)')
        plot(x,tf_1d(x,x0, Rx, tf_peak),label='fit (condensed)')
    else:
        plot(x, gauss_1d(x,x0,sigma_x,thermal_peak) + offset,'k--',linewidth=1.5,label='fit (thermal)')
    legend(loc='best')
    axis(xmin=x.min(),xmax=x.max())
    subplots_adjust(bottom=.05, top=.95,left=.05, right=.95, wspace=0, hspace=0)
    for ax in gcf().axes:
        ax.set_xticks([])
        ax.set_yticks([])
        
def compute_results_bec(df,run,params,covariance, pixel_size):
    params = uncertainties.correlated_values(params, covariance)
    x0, y0, Rx, Ry, sigma_x, sigma_y, tf_peak, thermal_peak, offset = params
    sigma_0 = 3*lambda_Rb**2/(2*pi)
    enh_gauss_integration_factor = 1/1.36843275344
    N_thermal = enh_gauss_integration_factor * 2*pi* thermal_peak/sigma_0 * sigma_y * sigma_x*pixel_size*pixel_size
    N_tf = 2*pi/5*tf_peak/sigma_0 * Ry * Rx*pixel_size*pixel_size
    F_c = N_tf/(N_tf + N_thermal)
    N = N_thermal + N_tf
    drop_time = df[aliases.tDrop]
    thermal_xwidth = sigma_x*pixel_size
    thermal_ywidth = sigma_y*pixel_size
    Tx = thermal_xwidth**2/drop_time**2 * m_Rb / k_B
    Ty = thermal_ywidth**2/drop_time**2 * m_Rb / k_B
    T_av = (Tx + Ty)/2
    T_c = T_av/(1 - F_c)**(1/3)
    
    mean_field_correction_factor = -3.426
    thermal_debroglie = 2*pi*hbar/sqrt(2*pi*m_Rb*k_B*T_c.nominal_value)
    T_c_correction_factor = mean_field_correction_factor*a_s_Rb/thermal_debroglie
    T_c = T_c *(1 - T_c_correction_factor)
    
    # Calculate mean trap frequency:
    omega = k_B*T_c / (hbar*((N/zeta(3,1))**(1/3) - pi**2/(12*zeta(3,1))))
    
    peak_condensate_density = (15/(128*sqrt(2)) * N_tf * m_Rb**3*omega**3/(hbar**3*a_s_Rb**(3/2)*pi**(3/2)))**(2/5)
    n, u_n = peak_condensate_density.nominal_value, peak_condensate_density.std_dev
    
    n_exponent = int(log10(n))
    n_val = n/10**n_exponent
    u_n_val = u_n/10**n_exponent
    
    figtext(0.02,0.23,r'$\frac{N_c}{N} = %.03f \pm %.03f$'%(F_c.nominal_value, F_c.std_dev))
    figtext(0.02,0.18,r'$T_x = %.01f \pm %.01f\, \rm{nK}$'%(Tx.nominal_value*1e9, Tx.std_dev*1e9))
    figtext(0.02,0.13,r'$T_y = %.01f \pm %.01f\, \rm{nK}$'%(Ty.nominal_value*1e9, Ty.std_dev*1e9))
    figtext(0.02,0.08,r'$T_c = %.01f \pm %.01f\, \rm{nK}$'%(T_c.nominal_value*1e9, T_c.std_dev*1e9))
    figtext(0.02,0.03,r'$n_{\rm{max}} = (%.02f \pm %.02f)\times 10^{%d}\,\rm{cm}^{-3}$'%(n_val,u_n_val,n_exponent-6))
    
    # save things!
    run.save_result('x0', x0.nominal_value)
    run.save_result('u_x0', x0.std_dev)
    run.save_result('y0', y0.nominal_value)
    run.save_result('u_y0', y0.std_dev)
    run.save_result('F_c',F_c.nominal_value)
    run.save_result('u_F_c', F_c.std_dev)
    run.save_result('Tx',Tx.nominal_value)
    run.save_result('u_Tx', Tx.std_dev)
    run.save_result('Ty',Ty.nominal_value)
    run.save_result('u_Ty', Ty.std_dev)
    run.save_result('N',N.nominal_value)
    run.save_result('u_N',N.std_dev)
    run.save_result('T_c', T_c.nominal_value)
    run.save_result('u_T_c', T_c.std_dev)
    run.save_result('u_T_c', T_c.std_dev)
    run.save_result('density',peak_condensate_density.nominal_value)
    run.save_result('u_density',peak_condensate_density.std_dev)   
         
def main(run, df):
    images = {}
    print ("Getting images for becfit")
    with h5py.File(run.h5_path) as h5_file:
        for key, val in h5_file["results"]["OD_calc"].items():
            print (key)
            if key.endswith("__OD"):
                images[key] = val[:]

    for key, image in images.items():
        prefix = key[:-4]
        print ('running becfit - %s'%prefix)
        s = time.time()
        #theta = 0.42
        #image = rotate(image,180*theta/pi)
        try:
            regime,roi_image, params, covariance, roi_x, roi_y = fit_atoms(image)
        except RuntimeError:
            print ('fit failed')
            imshow(image)
            return
        print ('becfit took', time.time() - s, 's')
        plot_results(regime, roi_image, params, prefix)
        if regime == 'bec':
            # add the roi offsets to x0 and y0:
            params[0] += roi_x
            params[1] += roi_y
            prefix = key[:-4]
            orientation = prefix.split("_")[0]
            #pixel_size = df[orientation,'effective_pixel_size']
            pixel_size = df.get('side_pixel_size')
            compute_results_bec(df,run,params,covariance, pixel_size)
        else:
            print ('not a bec, skipping analysis')
        

# if not spinning_top:
# #    path = '/home/bilbo/Desktop/20120521T185042_dipole_load3_7.h5'
# #    path = '/home/bilbo/Desktop/20120528T181418_magnetic_trap_0.h5'
    # path = '/home/bilbo/Desktop/good_bec.h5'
run = Run(path)
df = data(path)  
main(run,df)
# show()