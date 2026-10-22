from lyse import *
from pylab import *
from analysislib.krb2 import aliases
from analysislib.common.traces import *

#image_conf = ["bottom", "absorption_rb87"]
image_conf = ["side", "absorption_rb87"]

####### For now use old way ############################################
df = data(timeout=10)
sequences = [ os.path.split(path)[1][0:15] for path in df['filepath'] ]
sequences_unique = intersect1d(sequences, sequences)
no_seq = df["no_sequences_to_analyse"].values[-1]
no_seq = 1
df = df[ [sequence in sequences_unique[-no_seq:] for sequence in sequences] ]
#######################################################################

sigma0 = 1#2.9e-13 # m^2
x1,y1,x2,y2=[1200,1400,1900,2000]

n0_sums = []
ys = []
for fname in df['filepath']:
    run = Run(fname)
    # The crop above is in side camera pixels, so only use shots with that image set
    try:
        atoms = squeeze(float64(run.get_image(*(image_conf + ['atoms']))))
    except Exception:
        print('No %s images in %s, skipping' % (' '.join(image_conf), os.path.basename(fname)))
        continue
    flat = squeeze(float64(run.get_image(*(image_conf + ['flat']))))
    dark = squeeze(float64(run.get_image(*(image_conf + ['dark']))))
    atoms_crop = atoms[y1:y2,x1:x2]
    flat_crop = flat[y1:y2,x1:x2]
    dark_crop = dark[y1:y2,x1:x2]
    atoms_crop -= dark_crop
    flat_crop -= dark_crop
    ratio = atoms_crop/flat_crop
    ratio[ratio <= 0] = 1.0
    ratio[isnan(ratio)] = 1.0
    ratio[isinf(ratio)] = 1.0
    #logratio = log(ratio)
    #logratio_sum = logratio.sum()
    n0 = -1.0/sigma0 * log(ratio)
    n0_sum = n0.sum()
    I_bg = flat.mean()
    if not (isinf(n0_sum) or isnan(n0_sum)):
        y = (flat - atoms).sum()/sigma0
        #n0_sums.append(logratio_sum)
        n0_sums.append(n0_sum)
        ys.append(y)

n0_sums = array(n0_sums)
ys = array(ys)

# A linear fit needs at least two shots
if len(ys) < 2:
    print('Need at least 2 shots with %s images, found %d' % (' '.join(image_conf), len(ys)))
else:
    pars, u_pars = fit_linear(n0_sums, ys)
    print (pars)
    print ('I = %.2f +/- %.2f' % (-pars['m'], u_pars['u_m']))

    figure()
    xp = linspace(min(n0_sums), max(n0_sums), 10)
    plot(xp, linear(xp, pars['m'],pars['c']))#*pars))

    scatter(n0_sums, ys)
    show()