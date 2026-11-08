"""Measure raised blobs and edge dips in the flattened height grids."""
import sys
import numpy as np

res = 0.1
for name, thr in [('patch0', 0.35), ('patch1', 0.2)]:
    g = np.load(f'{sys.argv[1]}/{name}_grid.npy')
    H, W = g.shape
    valid = ~np.isnan(g)
    base = np.nanmedian(g)
    print(f'\n== {name}: grid {W*res:.1f} x {H*res:.1f} mm, board median z {base:.2f}')
    mask = valid & (g > base + thr)
    # connected components (4-neighbour flood fill)
    lab = np.zeros(g.shape, int); n = 0
    for y in range(H):
        for x in range(W):
            if mask[y, x] and not lab[y, x]:
                n += 1; st = [(y, x)]; lab[y, x] = n
                while st:
                    cy, cx = st.pop()
                    for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                        ny, nx = cy+dy, cx+dx
                        if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = n; st.append((ny, nx))
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(ys) < 30: continue
        z = g[ys, xs] - base
        # size at half of the blob's plateau height (scan edges are blurred)
        top = np.percentile(z, 90)
        core = z > top / 2
        cx0, cx1 = xs[core].min()*res, (xs[core].max()+1)*res
        cy0, cy1 = ys[core].min()*res, (ys[core].max()+1)*res
        print(f'  blob: x {cx0:5.1f}..{cx1:5.1f}  y {cy0:5.1f}..{cy1:5.1f}  '
              f'size {cx1-cx0:4.1f} x {cy1-cy0:4.1f}  center ({(cx0+cx1)/2:5.2f},{(cy0+cy1)/2:5.2f})  '
              f'height {top:4.2f} (max {z.max():4.2f})')
    # edge dips: castellations show up as low spots along the long edges
    for edge, rows in (('y=low', slice(int(0.3/res), int(1.0/res))),
                       ('y=high', slice(int(17.2/res), int(17.9/res)))):
        prof = np.nanmean(g[rows, :], axis=0) - base
        k = 5
        sm = np.convolve(np.nan_to_num(prof), np.ones(k)/k, mode='same')
        mins = [i for i in range(3, len(sm)-3)
                if len(sm[max(i-6,0):i+7]) and sm[i] == min(sm[max(i-6,0):i+7]) and sm[i] < np.nanmedian(sm) - 0.08]
        print(f'  dips along {edge}: ' + ' '.join(f'{m*res:.1f}' for m in mins))
    for edge, cols in (('x=high', slice(W - int(1.0/res), W - int(0.3/res))),):
        prof = np.nanmean(g[:, cols], axis=1) - base
        sm = np.convolve(np.nan_to_num(prof), np.ones(5)/5, mode='same')
        mins = [i for i in range(3, len(sm)-3)
                if len(sm[max(i-6,0):i+7]) and sm[i] == min(sm[max(i-6,0):i+7]) and sm[i] < np.nanmedian(sm) - 0.08]
        print(f'  dips along {edge}: ' + ' '.join(f'{m*res:.1f}' for m in mins))
