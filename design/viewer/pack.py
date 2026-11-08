"""Pack the viewer STLs into the HTML template.

Usage: python pack.py <stl dir> <variant> <template.html> <out.html>

Each STL is deduplicated, quantized to a 0.004 mm grid, and embedded as
base64 so the page is a single self-contained file.
"""
import base64, json, os, struct, sys
import numpy as np

stl_dir, variant, template, out_html = sys.argv[1:5]
Q = 0.004
meshes, lo_all, hi_all = {}, {}, {}
for f in sorted(os.listdir(stl_dir)):
    if not f.endswith('.stl'):
        continue
    b = open(os.path.join(stl_dir, f), 'rb').read()
    n = struct.unpack('<I', b[80:84])[0]
    rec = np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
    v = np.frombuffer(b[84:84 + n * 50], dtype=rec)['v'].reshape(-1, 3).astype(np.float64)
    q = np.round(v / Q).astype(np.int32)
    if np.abs(q).max() >= 32767:
        sys.exit(f'{f}: coordinates too large for int16 at {Q} mm')
    uniq, inv = np.unique(q, axis=0, return_inverse=True)
    idx = inv.reshape(-1).astype(np.uint16 if len(uniq) < 65536 else np.uint32)
    name = f[:-4]
    meshes[name] = {'p': base64.b64encode(uniq.astype('<i2').tobytes()).decode(),
                    'i': base64.b64encode(idx.tobytes()).decode(),
                    'w': 2 if idx.dtype == np.uint16 else 4}
    lo_all[name], hi_all[name] = v.min(0), v.max(0)

# outside size of the case, from the two halves
lo = np.minimum(lo_all['bottom'], lo_all['lid'])
hi = np.maximum(hi_all['bottom'], hi_all['lid'])
size = ' × '.join(f'{d:.2f}'.rstrip('0').rstrip('.') for d in hi - lo)
views = {
    'cable': ('USB laser switch, cable version',
              'RP2040-Zero on the single-sided carrier, in the two-piece case with the AM2464 pigtail and screw clamp.'),
    'molex': ('USB laser switch, Molex version',
              'RP2040-Zero on the single-sided carrier, in the two-piece case with a 2-pin header that plugs in from below.'),
}
title, sub = views[variant]
view = {'variant': variant, 'title': title, 'sub': sub, 'dims': f'{size} mm outside (L × W × H)'}
data = 'const MESH_Q=%g;const VIEW=%s;const MESHES=%s;' % (
    Q, json.dumps(view, ensure_ascii=False), json.dumps(meshes, separators=(',', ':')))
page = open(template).read().replace('/*TITLE*/', title).replace('/*DATA*/', data)
open(out_html, 'w').write(page)
print(f'{out_html}: {len(meshes)} parts, {os.path.getsize(out_html) // 1024} KB, case {size} mm')
