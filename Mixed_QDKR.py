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
    x_m = [1230,1285,1340,1397,1450,1505,1562,1620,1675,1730,1784,1840,1895]
    y_m = [1588,1588,1588,1588,1588,1588,1588,1588,1588,1588,1588,1588,1588]
    x_z = [1230,1285,1340,1397,1450,1505,1562,1620,1675,1730,1784,1840,1895]
    y_z = [1732,1732,1732,1732,1732,1732,1732,1732,1732,1732,1732,1732,1732]
    x_p = [1230,1285,1340,1397,1450,1505,1562,1620,1675,1730,1784,1840,1895]
    y_p = [1880,1880,1880,1880,1880,1880,1880,1880,1880,1880,1880,1880,1880]
    
    od_full = clip(od_full, a_min=0, a_max = None)
    
    figure()
    imshow(od_full)
    plot([x_m], [y_m], "rx", label="mF = -1")
    plot([x_z], [y_z], "gx", label="mF = 0")
    plot([x_p], [y_p], "bx", label="mF = +1")
    show()
    
    radius = int((x_m[1]-x_m[0])/2)
    od_min = 0
    od_max = 0.5
    
    od_m = {}
    od_z = {}
    od_p = {}
    
    for i in range(size(x_m)):
        #make multiple variables such as od_m0, od_m1...until number of spots on each row
        od_m['od_m'+str(i)] = od_full[(y_m[i] - radius): (y_m[i] + radius), (x_m[i] - radius):(x_m[i] + radius)]
        od_z['od_z'+str(i)] = od_full[(y_z[i] - radius): (y_z[i] + radius), (x_z[i] - radius):(x_z[i] + radius)]
        od_p['od_p'+str(i)] = od_full[(y_p[i] - radius): (y_p[i] + radius), (x_p[i] - radius):(x_p[i] + radius)]
    locals().update(od_m)
    locals().update(od_z)
    locals().update(od_p)
    
    #print(od_m['od_m1'])
    
    figure()
    for i in range(size(x_m)):
        subplot(3, size(x_m), i+1)
        imshow(od_m['od_m'+str(i)], vmin = od_min, vmax = od_max)
        title("mF = -1")

        subplot(3, size(x_m), size(x_m)+i+1)
        imshow(od_z['od_z'+str(i)], vmin = od_min, vmax = od_max)
        title("mF = 0")
    
        subplot(3, size(x_m), 2*size(x_m)+i+1)
        imshow(od_p['od_p'+str(i)], vmin = od_min, vmax = od_max)
        title("mF = +1")
    show()
    
    populations = []
    for i in range(size(x_m)):
        populations += [sum(od_m['od_m'+str(i)]), sum(od_z['od_z'+str(i)]), sum(od_p['od_p'+str(i)])]
    populations = array(populations)
    #print(populations)
    #populations is now a 1 x size(x_m) array where each 3rd item referes to a single state
    
    pop_T = sum(populations)
    #print(pop_T)
    
    #print(populations[1::3])
    pop_m = sum(populations[0::3])
    pop_z = sum(populations[1::3])
    pop_p = sum(populations[2::3])
    #print(pop_m, pop_z, pop_p)
    
    population_frac_m = populations[0::3]/pop_T
    population_frac_z = populations[1::3]/pop_T
    population_frac_p = populations[2::3]/pop_T
    #print(population_frac_m)
    #print(population_frac_z)
    #print(population_frac_p)
    
    momentum = list(range(-(size(x_m)-1),(size(x_m)-1)+2,2))
    #print(momentum)
    
    mom_m = sum(population_frac_m*momentum)
    mom_z = sum(population_frac_z*momentum)
    mom_p = sum(population_frac_p*momentum)
    print("momentum -1:", "{:.2e}".format(mom_m))
    print("momentum 0:", "{:.2e}".format(mom_z))
    print("momentum +1:", "{:.2e}".format(mom_p))
    
    results["mom_-1"] = mom_m
    results["mom_0"] = mom_z
    results["mom_+1"] = mom_p
    
run.save_results_dict(results)