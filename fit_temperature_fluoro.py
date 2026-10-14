from lyse import *
from pylab import *
from analysislib.krb2 import aliases
from scipy import polyval, polyfit
from analysislib.common.traces import fit_linear
from analysislib.krb2 import constants
from analysislib.krb2.constants.physcon import *
import matplotlib


####### For now use old way ############################################
df = data(timeout=10)
sequences = [ os.path.split(path)[1][0:15] for path in df['filepath'] ]
sequences_unique = intersect1d(sequences, sequences)
no_seq = df["no_sequences_to_analyse"].values[-1]
# no_seq = 1
df = df[ [sequence in sequences_unique[-no_seq:] for sequence in sequences] ]
#######################################################################
## aliases.n_atoms_fit, drop_time, aliases.widthY, aliases.widthX, aliases.pixel_size
#element = dataset[aliases.element]

def temp_fit(t, wy, element=constants.rb87, draw=True, color="blue"):
    m = element.m
    # Assume, wy is in m, so some pixel_size should be used
    t2 = t**2
    wy2 = wy**2
    params, errors = fit_linear(t2, wy2)
    v2 = params['m']
    dv2 = errors['u_m']

    T = m*v2 / (k_B)
    dT = T * dv2/v2

    w0 = params['c']**0.5
    dw0 = errors['u_c'] / params['c'] / 2.
    
    if draw:
        scatter(t2, wy**2, color=color)
        tt = linspace(t2.min() - (t2.max()-t2.min())*0.1, t2.max() + (t2.max()-t2.min())*0.1, 10)
        plot(tt, params['c'] + params['m']*tt, color=color)

    return T, dT, w0, dw0

def temp_plot(t, wy, element=constants.rb87, name="Temperature", label=True):
    fig = figure()
    ax = fig.add_axes([0.12,0.1, 0.82,0.8])
    title(name)
    
    # if (type(wy) != tuple) and (type(wy) != list):
        # wy = [wy]
    #colors=prop_cycle=(cycler('color', ['r', 'g', 'b', 'y'])
    colors = matplotlib.rcParams["axes.prop_cycle"].by_key()['color']
    for i, wy in enumerate(wy):
        c = colors[i]
        T, dT, w0, dw0 = temp_fit(t, wy, element=element, draw=True, color=c)
        text(0.6, 0.2 - i*0.1, "$T=$ %.3e $\\pm$ %.3e K" % (T, dT), fontsize=15, transform=ax.transAxes, color=c)
        text(0.6, 0.15 - i*0.1, "$w_0=$ %.3e $\\pm$ %.3e m" % (w0, dw0), fontsize=15, transform=ax.transAxes, color=c)
    xlabel(r"$t^2\,(s^2)$")
    ylabel(r"$w^2\,(m^2)$")

### Do the actual fit ###
# Do we use fit_frame or fit_frame_roi?
last = df[-1:].dropna()
if "fit_frame" in last:
    script = "fit_frame_roi_fluoro"
elif "fit_frame_roi" in last:
    script = "fit_frame_roi_fluoro"
else:
    script = "fit_frame_roi_fluoro"

if script and shape(df)[0]>2:
    # Get prefixes from frame fitting script
    prefixes = filter(lambda x: x.endswith("__wy"), map(lambda x: x[0], df[script].keys()))
    prefixes = map(lambda x: x[:-4], prefixes)
    for prefix in prefixes:
        # orientation, element, roi = prefix.split("_")
        pixel_size = 4.485e-6 #1/11/18
        t = df["drop_time"]
        wx = df[(script, "wx")] * pixel_size
        wy = df[(script, "wy")] * pixel_size
        # wx = df[(script, prefix + "__wx")] * pixel_size
        # wy = df[(script, prefix + "__wy")] * pixel_size
        
        temp_plot(t, [wx, wy], name=prefix)