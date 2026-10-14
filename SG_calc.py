from pylab import *
import socket
import lyse, h5py
from analysislib.krb2 import aliases
from analysislib.krb2 import constants

hostname = socket.gethostname()

run = lyse.Run(lyse.path)
dataset = lyse.data(lyse.path)

results = {}
result_arrays = {}
with h5py.File(lyse.path) as h5file:
    od_full = asarray(h5file["results/OD_calc/side_rb87__OD"])
    x_m = 1569
    y_m = 1584#1646#
    x_z = 1569
    y_z = 1732#1795#
    x_p = 1569
    y_p = 1880#1944#
    
    od_full = clip(od_full, a_min=0, a_max = None)
    
    figure()
    imshow(od_full)
    plot([x_m], [y_m], "rx", label="mF = -1")
    plot([x_z], [y_z], "gx", label="mF = 0")
    plot([x_p], [y_p], "bx", label="mF = +1")
    show()
    
    radius = int(0.9*(y_p - y_m)/4)
    od_min = 0
    od_max = 5
    
    od_m = od_full[(y_m - radius): (y_m + radius), (x_m - radius):(x_m + radius)]
    od_z = od_full[(y_z - radius): (y_z + radius), (x_z - radius):(x_z + radius)]
    od_p = od_full[(y_p - radius): (y_p + radius), (x_p - radius):(x_p + radius)]
    
    figure()
    subplot(1, 3, 1)
    imshow(od_m, vmin = od_min, vmax = od_max)
    title("mF = -1")
    
    subplot(1, 3, 2)
    imshow(od_z, vmin = od_min, vmax = od_max)
    title("mF = 0")
    
    subplot(1, 3, 3)
    imshow(od_p, vmin = od_min, vmax = od_max)
    title("mF = +1")
    show()
    
    populations = [sum(od_m), sum(od_z), sum(od_p)]
    populations = array(populations)
    population_all_states = sum(populations)
    results["population_m"] = populations[0]
    results["population_z"] = populations[1]
    results["population_p"] = populations[2]
    results["population"] = population_all_states
    results["p-1"] = populations[0]/population_all_states
    results["p0"] = populations[1]/population_all_states
    results["p+1"] = populations[2]/population_all_states
    
    print("Populations:")
    print("mF = -1:", populations[0])
    print("mF = 0:", populations[1])
    print("mF = +1:", populations[2])
    print("All:", population_all_states)
    print("")
    
    spin_z = (populations[2] - populations[0])/population_all_states
    results["spin_z"] = spin_z
    
    print("spin_z:", spin_z)
    
run.save_results_dict(results)
    