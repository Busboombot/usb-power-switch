"""Split a scan STL into connected patches, flatten each onto its board
plane, and write a height map plus a list of raised features."""
import sys, struct
import numpy as np
from PIL import Image

path, outdir = sys.argv[1], sys.argv[2]
d = open(path, 'rb').read()
n = struct.unpack('<I', d[80:84])[0]
rec = np.frombuffer(d[84:84 + 50 * n], dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))
tri = rec['v'].reshape(-1, 3, 3).astype(np.float64)

# weld vertices, find connected components
allv = tri.reshape(-1, 3)
key = np.round(allv / 1e-4).astype(np.int64)
_, vid = np.unique(key, axis=0, return_inverse=True)
vid = vid.reshape(-1, 3)
parent = np.arange(vid.max() + 1)
def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a
for t in vid:
    r = [find(x) for x in t]
    for x in r[1:]:
        parent[x] = r[0]
roots = np.array([find(t[0]) for t in vid])
labels, counts = np.unique(roots, return_counts=True)
order = np.argsort(-counts)
print('components (triangles):', counts[order][:8])

def min_area_rect(pts):
    from math import atan2
    # convex hull (monotone chain)
    P = sorted(map(tuple, pts))
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo, hi = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0: hi.pop()
        hi.append(p)
    H = np.array(lo[:-1] + hi[:-1])
    best = None
    for i in range(len(H)):
        e = H[(i + 1) % len(H)] - H[i]
        ang = np.arctan2(e[1], e[0])
        c, s = np.cos(-ang), np.sin(-ang)
        R = np.array([[c, -s], [s, c]])
        q = H @ R.T
        w, h = q.max(0) - q.min(0)
        if best is None or w * h < best[0]:
            best = (w * h, ang, w, h)
    return best

for ci, lab in enumerate(labels[order][:2]):
    T = tri[roots == lab]
    V = T.reshape(-1, 3)
    # robust plane fit
    keep = np.ones(len(V), bool)
    for it in range(6):
        c = V[keep].mean(0)
        u, s, vt = np.linalg.svd(V[keep] - c, full_matrices=False)
        nrm = vt[2]
        h = (V - c) @ nrm
        thr = np.percentile(np.abs(h), 60)
        keep = np.abs(h) < max(thr, 0.15)
    if np.percentile(h, 98) < -np.percentile(h, 2):   # features should stick up
        nrm = -nrm; h = -h
    h -= np.median(h[keep])
    ax1 = vt[0]; ax2 = np.cross(nrm, ax1)
    xy = np.stack([(V - c) @ ax1, (V - c) @ ax2], 1)
    area, ang, w, hh = min_area_rect(xy[np.abs(h) < 0.3])
    cs, sn = np.cos(-ang), np.sin(-ang)
    xy = xy @ np.array([[cs, -sn], [sn, cs]]).T
    if w < hh:
        xy = xy[:, ::-1] * [1, -1]; w, hh = hh, w
    xy -= xy[np.abs(h) < 0.3].min(0)
    print(f'patch {ci}: {len(T)} tris, board rect {w:.2f} x {hh:.2f} mm, '
          f'height range {h.min():.2f}..{h.max():.2f}')
    # rasterize each triangle (barycentric), keep the max height per cell
    P3 = np.concatenate([xy, h[:, None]], 1).reshape(-1, 3, 3)
    res = 0.1
    W = int(np.ceil(xy[:, 0].max() / res)) + 2
    Hh = int(np.ceil(xy[:, 1].max() / res)) + 2
    grid = np.full((Hh, W), np.nan)
    for t in P3:
        x0, y0 = np.floor(t[:, :2].min(0) / res).astype(int)
        x1, y1 = np.ceil(t[:, :2].max(0) / res).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, W - 1), min(y1, Hh - 1)
        if x1 < x0 or y1 < y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) * res + res / 2, np.arange(y0, y1 + 1) * res + res / 2)
        a, b, c3 = t
        den = (b[1] - c3[1]) * (a[0] - c3[0]) + (c3[0] - b[0]) * (a[1] - c3[1])
        if abs(den) < 1e-12: continue
        l1 = ((b[1] - c3[1]) * (gx - c3[0]) + (c3[0] - b[0]) * (gy - c3[1])) / den
        l2 = ((c3[1] - a[1]) * (gx - c3[0]) + (a[0] - c3[0]) * (gy - c3[1])) / den
        l3 = 1 - l1 - l2
        inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        z = l1 * a[2] + l2 * b[2] + l3 * c3[2]
        sub = grid[y0:y1 + 1, x0:x1 + 1]
        upd = inside & (np.isnan(sub) | (z > sub))
        sub[upd] = z[upd]
    np.save(f'{outdir}/patch{ci}_grid.npy', grid)
    g = np.nan_to_num(grid, nan=-1.0)
    img = np.clip((g + 0.3) / 3.6, 0, 1)
    rgb = np.stack([img * 255] * 3, -1).astype(np.uint8)
    rgb[np.isnan(grid)] = [255, 230, 230]
    Image.fromarray(rgb[::-1]).resize((W * 4, Hh * 4), Image.NEAREST).save(f'{outdir}/patch{ci}_height.png')
