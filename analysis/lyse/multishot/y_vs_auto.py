from __future__ import print_function
from lyse import *
from pylab import *
from analysislib.krb2 import aliases
from analysislib.common.imshow_irreg import imshow_irreg
import matplotlib.cm as cm
import csv
import os
import time
# import lmfit

export_to_csv = False

# Get the dataframe from lyse
df = data(timeout=10)

# Get a list of all unique shot sequences
# Each sequence may contain multiple shots (depending on the parameter space
# scan)
sequences = [os.path.split(path)[1][0:15] for path in df['filepath']]
sequences_unique = intersect1d(sequences, sequences)

# Extract the number of sequences to analyse from the last shot received by 
# lyse
no_seq = df["no_sequences_to_analyse"].values[-1]
# no_seq = 2
# slice the DataFrame so that we only have the last N sequences
# where N is equal to no_seq above
offset = 0
if offset:
    df = df[[sequence in sequences_unique[-(no_seq + offset):-offset] for sequence in sequences]]
    # Generate a plot title that contains the sequences we are plotting
    plot_title = ''.join([x + ', ' for x in sequences_unique[-(no_seq+offset):-offset]]) + '\n\n'
else:
    df = df[[sequence in sequences_unique[-(no_seq):] for sequence in sequences]]
    # Generate a plot title that contains the sequences we are plotting
    plot_title = ''.join([x + ', ' for x in sequences_unique[-(no_seq):]]) + '\n\n'

# Pull out global information from the last shot
last_run = Run(df['filepath'][-1])
expansions = last_run.get_globals_expansion()
units = last_run.get_units()

# iterate over the expansion type of every global
# detect which global variables form the axes of our parameter space
independents = []
for global_name, expansion_type in expansions.items():
    # This global is not to be used as an axis of the parameter space.
    # We use it to "trick" runmanager into generating multiple identical shots
    # so that we can see the variation of measured quantities
    if global_name == 'repeats':
        continue

    # If the expansion type is a zip group (not "outer")
    # Then we need to check if it is a zip group that we can automatically 
    # handle
    if expansion_type != "outer":
        # If the expansion type matches the global name, then it is an 
        # automatically created zip group, and we use this value as the axis
        # of our parameter space as it is the root global of the parameter 
        # space
        if expansion_type == global_name:
            independents.append(global_name)

        # If the zip group name matches another global with an expansion type,
        # then we ignore it because we'll catch the root global and use that
        # as the axis of the parameter space
        elif expansion_type in expansions and expansions[expansion_type] == expansion_type:
            pass

        # If it isn't the two above cases, then it means we have a custom 
        # named zip group which we can't yet handle nicely as we don't know
        # which global to use as the parameter space axis
        else:
            raise Exception(
                'This sequence contains globals in a zip group that was not automatically created by runmanager, please use a different plotting script')
                
    # it's an outer product (not a zip group) then use it as an axis of our
    # parameter space
    else:
        independents.append(global_name)

# We can only handle up to a 2D parameter space as plotting anything else is 
# tricky
if len(independents) > 2:
    print(independents)
    raise Exception(
        'There are %s orthogonal globals changing, but this script can only plot up to 2. Please try a universe with more spatial dimensions.' %
        len(independents))


#
# Define a function that can take a DataFrame (or slice of a DataFrame)
# and create a 1D or 2D plot (depending on the dimension of the parameter
# space) for each measurement result specified in a list
#
#   df: The DataFrame
#
#   plot_measurement: The list of measurements (this determine the number of 
#                     plots produced). This list should conatin either a string
#                     or a tuple that will be used to index the DataFrame. 
#                     Strings will also be first checked to see if they exist 
#                     as an attribute of the aliases module, and the value of 
#                     the alias will be used as the DataFrame index instead
#
def y_vs_auto(df, plot_measurement, independents):
    # if plot_measurement is only a single string, convert it to a one item 
    # long list
    if type(plot_measurement) in (str, string_):
            plot_measurement = [plot_measurement]

    # Shots without images have no fit results, so skip measurements that no
    # loaded shot has a column for
    missing = [i for i in plot_measurement if getattr(aliases, i, i) not in df]
    if missing:
        print("No results for %s in these shots, skipping" % ", ".join(missing))
    plot_measurement = [i for i in plot_measurement if i not in missing]

    # if we are not performing a parameter space scan, then we likely have a 
    # single shot on repeat. So do a y_vs_shot style plot
    if len(independents) == 0:
        # Iterate over the list of plot measurements (the measurements to
        # use on the y-axis of a plot)
        for i in plot_measurement:
            # Extract the y values from the dataFrame based on the current
            # plot measurement we are iterating over
            y = df[getattr(aliases, i, i)]

            # Create the figure
            figure()

            # plot the y values
            plot(y.values, "-", linewidth=2)

            # Add labels to the plot axes and a title
            xlabel("Shot")
            ylabel(i)
            title(plot_title)

            # Print out the mean and standard deviation of the data
            # This provides a useful measure of the stability of the measured 
            # quantity
            print("Mean %s = %0.3e +/- %0.3e (%s)" % 
                  (i, mean(y), std(y), std(y) / mean(y) * 100))

    # if we are performing a 1D parameter space scan we do a y_vs_x style plot
    elif len(independents) == 1:
        # Define the x-axis of the plot to match the parameter space axis
        x_axis = independents[0]
        x = df[x_axis]

        # Iterate over the list of plot measurements (the measurements to
        # use on the y-axis of a plot)
        for i in plot_measurement:
            # Extract the y values from the dataFrame based on the current
            # plot measurement we are iterating over
            y = df[getattr(aliases, i, i)]

            # Create the figure
            figure()

            # Create a set of plot colours, one for each separate sequence
            # we are plotting
            colors = cm.rainbow(np.linspace(0, 1, no_seq + 1))
            color_i = 0

            # Group by the sequence name and plot each sequence with a 
            # different colour
            grouped = df.groupby(df[['sequence']].values[:,0])
            for name, group in grouped:
                # for name, group in
                # df.groupby('sequence',as_index=False):
                x_t = group[x_axis]
                y_t = group[getattr(aliases, i, i)]
                scatter(x_t, y_t, color=colors[color_i])
                color_i += 1

            # Add labels to the plot axes and a title
            title(plot_title)
            xlabel("%s (%s)" % (x_axis, units[x_axis]))
            ylabel(i)

            # Calculate averages for points in the paramater space that
            # were run more than once (aka repeat shots)
            avg_x = []
            avg_y = []
            avg_u_y = []
            # Slice the DataFrame based on x-axis (parameter space axis)
            for name, group in df.groupby(x_axis):
                # if there is more than one shot for this point in 
                # parameter space, then calculate the mean and
                # standard deviation and store everything in lists
                if len(group) > 1:
                    avg_x.append(
                        group[x_axis][0])
                    y = group[getattr(aliases, i, i)]
                    avg_y.append(mean(y))
                    avg_u_y.append(std(y))

            # If there is a parameter space point that has more than one
            # shot, then make an error bar plot as well (overlays on the
            # existing plot)
            if avg_x:
                errorbar(avg_x, avg_y, yerr=avg_u_y, c="red", fmt="o")
                max_y = max(avg_y)
                max_index = avg_y.index(max_y)
                # Print out statistics for this plot
                #       max_at:   location in parameter space of maximum value
                #       value is: average y_value at this point with 
                #                 standard deviation if more than one shot
                #                 was run for this point in parameter space
                print('%s max at: %s=%0.3e, value is %0.3e +/- %0.3e (%3.1f)' %
                      (i, x_axis, avg_x[max_index], avg_y[max_index], 
                       avg_u_y[max_index], 
                       avg_u_y[max_index] / avg_y[max_index] * 100))

            # Adust the x-axis limits so that all datapoints are visible rather
            # than a couple being stuck right on the edge
            if len(x) > 1:
                xlim(x.min() - (x.max() - x.min()) / 10.0,
                     x.max() + (x.max() - x.min()) / 10.0)
                    
    # if two things are changing then we do an imshow
    elif len(independents) == 2:
        # Define the x-axis of the plot to match the first parameter space axis
        x_axis = independents[0]
        x = array(df[x_axis])
        # Define the y-axis of the plot to match the second parameter space 
        # axis
        y_axis = independents[1]
        y = array(df[y_axis])
        
        # Iterate over the list of plot measurements (the measurements to
        # use on the z-axis of a plot)
        for i in plot_measurement:
            # Extract the z values from the dataFrame based on the current
            # plot measurement we are iterating over
            z = array(df[getattr(aliases, i, i)])

            # Create the figure
            figure()

            # Make the 2D plot using a custom version of matplotlib.imshow 
            # which can handle irregularly spaced data in the x-y parameter 
            # space. Regions in (x,y) space are coloured based on the z-value
            # of the nearest (x,y,z) point
            imshow_irreg(x, y, z, 
                         method='nearest', aspect='auto', cmap="Blues")

            # Add labels to the plot axes and a title               
            xlabel("%s (%s)" % (x_axis, units[x_axis]))
            ylabel("%s (%s)" % (y_axis, units[y_axis]))
            title("%s\n%s" % (i, plot_title[:-2]))
            # add a colour bar to the 2D plot
            colorbar()

            # Overlay a scatter plot on the 2D plot that shows the actual 
            # locations of the (x,y,z) values on the (x,y) plane within the
            # coloured regions provided by imshow.
            scatter(x, y)
            
            # print out the parameter space corrdinates which contain the 
            # maximum value of the measurement
            z_arg_max = z.argmax()
            print('%s max at: %s=%0.3e, %s=%0.3e' % 
                  (i, x_axis, x[z_arg_max], y_axis, y[z_arg_max]))

    # print line to break up all print statements from this run from those
    # of the next run
    print('')


# 
# The below code calls the above y_vs_auto function
#

# The plot_measurement global lists what to plot. It is a different list for
# absorption and fluorescence imaging (see the Analysis globals group).
y_vs_auto(df, df["plot_measurement"].values[-1], independents)

# Export N_ab and the fluorescence N to a csv, for analysis in Matlab
if export_to_csv:
    csv_file = 'csv_file_' + time.strftime("%Y%m%d-%H%M%S") + '.csv'
    csv_path = 'Z:/Experiments/krb2/4wavemixing/csv_exports/'
    os.makedirs(csv_path, exist_ok=True)
    with open(csv_path + csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(df['OD_calc', 'N_ab'].values)
        writer.writerow(df['fluoro_frame', 'N'].values)
