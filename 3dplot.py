from __future__ import division
from lyse import *
from analysislib.common.traces import curve_fit
from scipy.optimize import leastsq
from scipy.special import spence
from pylab import *
import matplotlib.gridspec as gridspec
from mpl_toolkits.mplot3d import Axes3D
import numpy
import os
from mayavi import mlab
#import mayavi.mlab

crap_3d = False

if not 'path' in locals():
    df = data()
    paths = df['filepath'].values[-20:]
    #paths = paths[[1,3,5,6,7]]
else:
    paths = [path]

print (paths)

for path in paths:
    run = Run(path)
    
    image = run.get_image('side', 'absorption', 'OD')
    subimg = image[800:1050,670:920]

    #imshow(subimg)
    if crap_3d:
        fig = figure()
        Y,X = indices(subimg.shape)
        Y[:,:] = Y[::-1,:]
        ax = fig.add_subplot(111, projection='3d')
        ax.plot_surface(X, Y, subimg,cmap=cm.jet,linewidth=0,rstride=4,cstride=4,vmax=2)
        ax.set_zlim3d(0, 1.5)
        savefig('/home/beclab/Desktop/movie/' + os.path.split(path)[-1][:-3] + '.png')

    else:
#        gs0 = gridspec.GridSpec(1, 2)
#        ax = gcf().add_subplot(gs0[1])
#        flipped_image = subimg[::-1,:]
        ydim, xdim = subimg.shape
        mlab.figure(1, fgcolor=(1, 1, 1), bgcolor=(0, 0, 0), size=(800,800))
        mlab.surf(subimg,vmax=1,extent=[0,xdim,0,ydim,0,100*subimg.max()],reset_zoom=(path==paths[0]))
        mlab.view(distance=900,focalpoint=[0,0,-100])
        #mlab.show()
        mlab.savefig('/home/beclab/Desktop/movie/' + os.path.split(path)[-1][:-3] + '_mlab.png')
        mlab.close()
