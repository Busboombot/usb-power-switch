"""Draw the model's part outlines over the scan height maps."""
import sys
import numpy as np
from PIL import Image, ImageDraw

out = sys.argv[1]
S = 12          # pixels per mm
res = 0.1
cy = 8.95       # scan y of the board centerline (USB center)

def heightmap(name, lo, hi):
    g = np.load(f'{out}/{name}_grid.npy')
    img = np.clip((np.nan_to_num(g, nan=lo) - lo) / (hi - lo), 0, 1)
    rgb = np.stack([img * 200 + 30] * 3, -1).astype(np.uint8)
    im = Image.fromarray(rgb[::-1]).resize((int(g.shape[1] * res * S), int(g.shape[0] * res * S)), Image.BILINEAR)
    return im, g.shape[0] * res

def rect(d, Hmm, x0, x1, y0, y1, col):
    d.rectangle([x0 * S, (Hmm - y1) * S, x1 * S, (Hmm - y0) * S], outline=col, width=2)

# top: x from USB end, y = cy + model y
im, Hmm = heightmap('patch0', -0.3, 3.3)
d = ImageDraw.Draw(im)
for (x, y), (sx, sy), lab in [((16.0, -4.6), (4.2, 3.2), 'BOOT'), ((16.1, 4.45), (4.2, 3.2), 'RESET'),
                              ((15.65, 0), (1.9, 1.6), 'LED'), ((12.4, 0), (2.0, 2.9), 'flash')]:
    rect(d, Hmm, x - sx / 2, x + sx / 2, cy + y - sy / 2, cy + y + sy / 2, (255, 60, 60))
    d.text(((x - sx / 2) * S + 2, (Hmm - cy - y - sy / 2) * S + 2), lab, fill=(255, 220, 0))
rect(d, Hmm, -1.25, 6.7, cy - 4.47, cy + 4.47, (255, 60, 60))
d.text((4, (Hmm - cy) * S), 'USB', fill=(255, 220, 0))
rect(d, Hmm, 0, 23.5, cy - 9, cy + 9, (80, 160, 255))
im.save(f'{out}/overlay_top.png')

# bottom: scan x runs from the far end; model x = 23.5 - scan x
im, Hmm = heightmap('patch1', -0.3, 1.3)
d = ImageDraw.Draw(im)
for x, y, sx, sy, lab in [(12.55, 0, 7.3, 7.3, 'RP2040'), (19.0, 0, 2.6, 3.3, 'crystal'), (3.05, 0, 3.1, 2.1, 'reg')]:
    X = 23.5 - x
    rect(d, Hmm, X - sx / 2, X + sx / 2, 9.15 + y - sy / 2, 9.15 + y + sy / 2, (255, 60, 60))
    d.text(((X - sx / 2) * S + 2, (Hmm - 9.15 - sy / 2) * S + 2), lab, fill=(255, 220, 0))
im.save(f'{out}/overlay_bottom.png')
