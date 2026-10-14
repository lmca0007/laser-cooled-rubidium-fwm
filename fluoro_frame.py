from pylab import *
import lyse

run = lyse.Run(lyse.path)
dataset = lyse.data(lyse.path)

mot_shot = False
try:
    pic = float64(run.get_image('side', 'fluorescence_k41', 'atoms'))
    orientation = 'side'
except:
    try:
        pic = float64(run.get_image('side', 'fluorescence_k39', 'atoms'))
        orientation = 'side'
    except:
        try:
            pic = float64(run.get_image('side', 'fluorescence_rb87', 'atoms'))
            orientation = 'side'
        except:
            try:
                pic = float64(run.get_image('side', 'fluorescence_rb85', 'atoms'))
                orientation = 'side'
            except:
                try:
                    pic = float64(run.get_image('side', 'MOT_shot', 'atoms'))
                    orientation = 'side'
                    mot_shot = True
                except:
                    pic = None
                    print('no atoms pic found')
            
try:
    dark = float64(run.get_image('side', 'fluorescence_rb87', 'dark'))
except:
    try:
        dark = float64(run.get_image('side', 'fluorescence_rb85', 'dark'))
    except:
        dark = None
        print('no dark image found')
    
if pic is not None:
    if not mot_shot:
        #x1,y1,x2,y2 = dataset[orientation, 'roi0']
        #x1,y1,x2,y2 = (0,0,2752,2200)
        if dataset.get('roi_full',True):
          x1,y1,x2,y2 = 0,0,2752,2200 #1200,825,1500,1250
        else:
          x1,y1,x2,y2 = [dataset.get('roi_x1'),dataset.get('roi_y1'),dataset.get('roi_x2'),dataset.get('roi_y2')]
          
          
            
        ## Subtract an area under the ROI of equal size to subtract ####
        atoms = pic[y1:y2,x1:x2]
        ## Subtract an area under the ROI of equal size to subtract ####
        height = y2-y1
        if dark is not None:
            empty = dark[y1:y2,x1:x2]
        else:
            empty = pic[y1+height:y2+height, x1:x2]
    else:
        atoms = pic
        empty = array([pic[-1,-1]*pic.size])

    ###
    #outer = pic.copy()
    #outer[y1:y2,x1:x2] = 0.0
    #mean_pixel = outer.sum() / (outer.shape[0] * outer.shape[1] - (y2-y1)*(x2-x1))
    #empty_sum = mean_pixel * (x2-x1)*(y2-y1)
    ###

    N = atoms.sum() - empty.sum()

    run.save_result("N", N)
    
    run.save_result_array('%s_fluoro_img'%orientation, atoms-empty)
    pic /= 4095.0
    figure()
    imshow(atoms,cmap="gray")
    cbar = colorbar()
    title("Fluorescence image")
    cbar.set_label("Fraction of camera saturation")
    
    figure()
    imshow(atoms-empty,cmap="gray")
    cbar = colorbar()
    title("Fluorescence image")
    cbar.set_label("Fraction of camera saturation")
    