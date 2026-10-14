from pylab import *
import lyse

run = lyse.Run(lyse.path)
dataset = lyse.data(lyse.path)

# The Andor camera saves frames as (1, ny, nx), so squeeze to (ny, nx)
orientation = None
mot_shot = False
pic = dark = None
for cam in ('side', 'bottom'):
    try:
        pic = squeeze(float64(run.get_image(cam, 'fluorescence_rb87', 'atoms')))
        orientation = cam
        break
    except Exception:
        pass
if pic is None:
    try:
        pic = squeeze(float64(run.get_image('side', 'MOT_shot', 'atoms')))
        orientation = 'side'
        mot_shot = True
    except Exception:
        print('no atoms pic found')

if pic is not None:
    try:
        dark = squeeze(float64(run.get_image(orientation, 'fluorescence_rb87', 'dark')))
    except Exception:
        print('no dark image found')

    if not mot_shot:
        # roi_* globals are side camera pixels, so other cameras use the full frame
        if dataset.get('roi_full', True) or orientation != 'side':
            y2, x2 = pic.shape
            x1, y1 = 0, 0
        else:
            x1, y1, x2, y2 = [int(dataset.get(k)) for k in ('roi_x1', 'roi_y1', 'roi_x2', 'roi_y2')]
        atoms = pic[y1:y2, x1:x2]
        height = y2 - y1
        if dark is not None:
            empty = dark[y1:y2, x1:x2]
        else:
            # No dark frame: use the area of equal size below the ROI
            empty = pic[y1+height:y2+height, x1:x2]
    else:
        atoms = pic
        empty = array([pic[-1, -1] * pic.size])

    N = atoms.sum() - empty.sum()

    run.save_result("N", N)
    run.save_result_array('%s_fluoro_img' % orientation, atoms - empty)

    figure()
    imshow(atoms, cmap="gray")
    colorbar()
    title("Fluorescence image")

    figure()
    imshow(atoms - empty, cmap="gray")
    colorbar()
    title("Fluorescence image minus dark")
