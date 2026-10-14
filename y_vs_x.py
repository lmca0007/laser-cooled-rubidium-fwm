##############################################################################################
## KRb y_vs_x.py                                                                            ##
##                                                                                          ##
## This is a "vanilla" plotting script---there should be no fitting or multishot analysis.  ##
## Simply plots values you ask for against values you've chosen.                            ##
## See y_vs_auto for an automated version that plots the requested measurements against     ##
## whatever it detects is being scanned over, or z_vs,y_vs_x.py for an extra dimension :)   ##
##############################################################################################

from lyse import *
from pylab import *
from analysislib.krb2 import aliases


####### NEW WAY OF GETTING DF ONCE LYSE HAS BEEN MODIFIED ##########

# # get the dataframe for the last sequence and check how many sequences we had requested in it.
# df = data(timeout=10,n_sequences = 1)
# no_seq = df["no_sequences_to_analyse"].values[-1]

# # if we asked for more than one, go back and get the df again with the right number!
# if no_seq > 1:
    # df = data(timeout=10,n_sequences = no_seq)
    
########################################################################

####### For now use old way ############################################
df = data(timeout=10)
sequences = [ os.path.split(path)[1][0:15] for path in df['filepath'] ]
sequences_unique = intersect1d(sequences, sequences)
no_seq = df["no_sequences_to_analyse"].values[-1]
# no_seq = 1
df = df[ [sequence in sequences_unique[-no_seq:] for sequence in sequences] ]
#######################################################################

# get the x and y axes to plot from the latest experiment:
x_axis = df["x_axis"].values[-1]
y_axis = df["plot_measurement"].values[-1]
# get the x-values of the datapoints:
x = df[getattr(aliases, x_axis, x_axis)]

# if there is only a string for y, then we only have one thing to plot
if type(y_axis) in (str, string_):
        y = df[getattr(aliases, y_axis,y_axis)]
        
        figure()
        scatter(x,y)
        scatter([x[-1]], [y[-1]], c="red")
        
        xlabel(x_axis)
        ylabel(y_axis)
        if len(x) > 1:
                xlim(x.min() - (x.max() - x.min())/10.0,x.max() + (x.max() - x.min())/10.0)
        
else:
    for i in y_axis:
        y = df[getattr(aliases, i,i)]

        
        figure()
        scatter(x,y)
        scatter([x[-1]], [y[-1]], c="red")
        
        xlabel(x_axis)
        ylabel(i)
        if len(x) > 1:
                xlim(x.min() - (x.max() - x.min())/10.0,x.max() + (x.max() - x.min())/10.0)