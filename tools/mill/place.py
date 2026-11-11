# /// script
# requires-python = ">=3.11"
# dependencies = ["shapely>=2", "matplotlib", "numpy", "scipy"]
# ///
"""Place the carrier on the PCB blank from a scan, and write the job for the Carvera program.

    uv run tools/mill/place.py GRID.npz SCAN_NAME        (after tools/mill/cam.py)

GRID.npz is a height grid of the jig pocket (machine X/Y, 0.2 mm cells, heights above the bed) from
the carvera repo's scan processing. Heights are used only relative to the blank: the scanner's
absolute height can be off by millimetres, and its XY by about 2 mm, so the board keeps MARGIN
clear of anything that isn't blank and the probe confirms the blank before cutting.

Writes:
  tools/mill/blank/<scan>.json, .png   the blank as scanned: its level, what's cut away, and this placement
  tools/mill/out/mill_usb_switch.json  the job: toolpaths, placement, probe spots, expected heights
  tools/mill/out/mill_usb_switch.png   the picture for the program's screen
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage
from shapely import affinity, contains_xy
from shapely.geometry import Polygon

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "tools", "mill", "out")
BLANK = os.path.join(ROOT, "tools", "mill", "blank")

ANCHOR = (-359.208, -235.638)       # machine X, Y of work 0, 0: the pocket's front-left corner
POCKET = (0.0, 150.0, 0.0, 100.0)   # work X, Y of the pocket walls (measured 151.0, 100.8)
WALL_CLEAR = 3.0                    # mm: the cutter's edge stays this far from the walls
MARGIN = 5.0                        # mm from the cutter's edge to anything that is not blank
LEVEL_TOL = 0.6                     # mm: cells this close to the blank's level are blank
FLOOR_MZ = -110.40                  # probe machine Z on the pocket floor (mill_floor_touch.jsonl, 2026-11-08)
PROBE_BALL = 4.0                    # mm: a floor touch stays this far inside a cut-out
MIN_COVER = 0.9                     # share of the footprint the scan must have measured
FLOOR_X_MIN = 40.0                  # work X: floor touches no further left than this


def load_grid(path):
    g = np.load(path)
    z, x0, y0, c = g["merged"], float(g["x0"]), float(g["y0"]), float(g["cell"])
    # crop to the pocket plus a border, in work coordinates
    wx0, wx1, wy0, wy1 = -15.0, 165.0, -15.0, 115.0
    i0, i1 = int((wx0 + ANCHOR[0] - x0) / c), int((wx1 + ANCHOR[0] - x0) / c)
    j0, j1 = int((wy0 + ANCHOR[1] - y0) / c), int((wy1 + ANCHOR[1] - y0) / c)
    sub = np.full((j1 - j0, i1 - i0), np.nan)       # NaN where the grid doesn't reach
    a, b = max(j0, 0), min(j1, z.shape[0])
    p, q = max(i0, 0), min(i1, z.shape[1])
    sub[a - j0:b - j0, p - i0:q - i0] = z[a:b, p:q]
    ox, oy = x0 + i0 * c - ANCHOR[0], y0 + j0 * c - ANCHOR[1]     # work X, Y of cell (0, 0)'s corner
    return sub, ox, oy, c


def classify(z, ox, oy, c):
    """blank level, and masks: blank, cut away (low), other (anything else measured), inside the pocket."""
    ny, nx = z.shape
    X = ox + (np.arange(nx) + 0.5) * c
    Y = oy + (np.arange(ny) + 0.5) * c
    inside = (Y[:, None] > POCKET[2] + 2) & (Y[:, None] < POCKET[3] - 2) & (X[None, :] > POCKET[0] + 2) & (X[None, :] < POCKET[1] - 2)
    v = z[inside & np.isfinite(z)]
    hist, edges = np.histogram(v, bins=np.arange(np.floor(v.min()), np.ceil(v.max()) + 0.1, 0.1))
    level = float(edges[np.argmax(hist)] + 0.05)
    near = np.abs(v - level) < LEVEL_TOL
    level = float(np.median(v[near]))
    fin = np.isfinite(z)
    blank = fin & (np.abs(z - level) < LEVEL_TOL)
    # judge each spot by the cells measured within about 2 mm: not blank there means not blank
    k = int(round(2.2 / c)) | 1
    measured = ndimage.uniform_filter(fin.astype(float), k)
    not_blank = ndimage.uniform_filter((fin & ~blank).astype(float), k) / np.maximum(measured, 1e-6)
    cut = (measured > 0.05) & (not_blank > 0.3) & inside
    cut = ndimage.binary_closing(cut, iterations=3) & inside
    lab, n = ndimage.label(cut)
    sizes = ndimage.sum(cut, lab, range(1, n + 1))
    cutouts = []
    for k, s in enumerate(sizes, 1):
        if s * c * c < 4:       # under 4 mm^2: speckle
            cut[lab == k] = False
            continue
        jj, ii = np.nonzero(lab == k)
        zz = z[lab == k]
        zz = zz[np.isfinite(zz) & (zz < level - 1.0)]
        floor = float(np.median(zz)) if zz.size > 50 else float("nan")
        cutouts.append({"x0": round(ox + ii.min() * c, 1), "x1": round(ox + (ii.max() + 1) * c, 1),
                        "y0": round(oy + jj.min() * c, 1), "y1": round(oy + (jj.max() + 1) * c, 1),
                        "area_mm2": round(float(s * c * c)), "below_blank": round(level - floor, 2), "label": k})
    return level, blank, cut, inside, X, Y, lab, cutouts


def footprint(job, angle):
    """The board plus the cutter, turned by angle about the board origin."""
    b = Polygon(job["board"]["outline"]).buffer(job["board"]["keepout"], join_style="round")
    return affinity.rotate(b, angle, origin=(0, 0))


def place(job, z, ox, oy, c):
    level, blank, cut, inside, X, Y, lab, cutouts = classify(z, ox, oy, c)
    # obstacles: everything in the pocket that isn't blank, spread by the margin
    r = int(round(MARGIN / c))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    keep = ndimage.binary_dilation(cut, structure=(xx ** 2 + yy ** 2) <= r * r)
    best = None
    for angle in (0, 90):
        fp = footprint(job, angle)
        fx0, fy0, fx1, fy1 = fp.bounds
        # the footprint as a mask on the grid, anchored at the board origin
        ii = np.arange(int(np.floor(fx0 / c)), int(np.ceil(fx1 / c)) + 1)
        jj = np.arange(int(np.floor(fy0 / c)), int(np.ceil(fy1 / c)) + 1)
        gx, gy = np.meshgrid((ii + 0.5) * c, (jj + 0.5) * c)
        m = contains_xy(fp, gx, gy)
        # test board origins on a 1 mm grid: free if no kept-out cell falls under the footprint
        for px in np.arange(POCKET[0] + WALL_CLEAR - fx0, POCKET[1] - WALL_CLEAR - fx1 + 1e-9, 1.0):
            for py in np.arange(POCKET[2] + WALL_CLEAR - fy0, POCKET[3] - WALL_CLEAR - fy1 + 1e-9, 1.0):
                ci = ((px + (ii + 0.5) * c - ox) / c).astype(int)
                cj = ((py + (jj + 0.5) * c - oy) / c).astype(int)
                sub = keep[np.ix_(cj, ci)][m]
                cover = np.isfinite(z[np.ix_(cj, ci)][m]).mean()
                if sub.any() or cover < MIN_COVER:
                    continue
                # pack toward the front-right corner (X high, Y low): keeps the big free area in one piece
                score = (POCKET[1] - (px + fx1)) + (py + fy0 - POCKET[2])
                if best is None or score < best[0]:
                    best = (score, px, py, angle, cover)
    if best is None:
        sys.exit("no room for the board on this blank")
    _, px, py, angle, cover = best
    return {"x": float(px), "y": float(py), "angle": angle, "coverage": round(float(cover), 3)}, level, cut, lab, cutouts


def floor_spots(place_xy, z, ox, oy, c, cut, lab, cutouts):
    """Up to two floor touches: the most inside point of the two big cut-outs (over 100 mm2) nearest
    the board. Small ones are mostly scan speckle, and the probe ball doesn't fit in them."""
    d = ndimage.distance_transform_edt(cut) * c
    spots = []
    px, py = place_xy
    X = ox + (np.arange(cut.shape[1]) + 0.5) * c
    big = [q for q in cutouts if q["area_mm2"] > 100]
    for co in sorted(big, key=lambda q: np.hypot((q["x0"] + q["x1"]) / 2 - px, (q["y0"] + q["y1"]) / 2 - py))[:2]:
        # not at low X: the camera mount sits 60 mm to -X of the spindle and has hit things there
        dd = np.where((lab == co["label"]) & (X[None, :] >= FLOOR_X_MIN), d, 0)
        j, i = np.unravel_index(np.argmax(dd), dd.shape)
        if dd[j, i] >= PROBE_BALL:
            spots.append([round(float(ox + (i + 0.5) * c), 2), round(float(oy + (j + 0.5) * c), 2)])
    return spots


def picture(z, ox, oy, c, level, job, pl, floors, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ny, nx = z.shape
    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    ax.imshow(z - level, origin="lower", extent=[ox, ox + nx * c, oy, oy + ny * c], cmap="gray", vmin=-2.5, vmax=0.8)
    ax.add_patch(plt.Rectangle((POCKET[0], POCKET[2]), POCKET[1], POCKET[3], fill=False, ec="#ff4040", lw=1.2))
    a = pl["angle"]

    def w(p):
        return affinity.translate(affinity.rotate(p, a, origin=(0, 0)), pl["x"], pl["y"])
    board = w(Polygon(job["board"]["outline"]))
    ax.fill(*board.exterior.xy, color="#20c060", alpha=0.75)
    for pc in job["outline"]["pieces"]:
        ln = np.array([w_pt(p, pl) for p in pc["pts"]])
        ax.plot(ln[:, 0], ln[:, 1], color="#ff7f11" if pc["tab"] else "#ffd166", lw=3.5 if pc["tab"] else 1.5)
    for p in job["probe"]:
        x, y = w_pt(p, pl)
        ax.plot(x, y, "x", color="magenta", ms=9, mew=2.5)
    for x, y in floors:
        ax.plot(x, y, "+", color="cyan", ms=14, mew=2.5)
    ax.set_xlim(ox, ox + nx * c)
    ax.set_ylim(oy, oy + ny * c)
    ax.set_xlabel("work X, mm")
    ax.set_ylabel("work Y, mm")
    ax.set_title(title, fontsize=10)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def w_pt(p, pl):
    import math
    a = math.radians(pl["angle"])
    return (pl["x"] + math.cos(a) * p[0] - math.sin(a) * p[1], pl["y"] + math.sin(a) * p[0] + math.cos(a) * p[1])


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    grid, scan = sys.argv[1], sys.argv[2]
    with open(os.path.join(OUT, "carrier_toolpaths.json")) as f:
        job = json.load(f)
    z, ox, oy, c = load_grid(grid)
    pl, level, cut, lab, cutouts = place(job, z, ox, oy, c)
    floors = floor_spots(w_pt([job["board"]["length"] / 2, 0], pl), z, ox, oy, c, cut, lab, cutouts)
    deep = [co["below_blank"] for co in cutouts if np.isfinite(co["below_blank"]) and co["area_mm2"] > 100]
    stack = float(np.median(deep)) if deep else 1.7
    job.update({"place": {k: pl[k] for k in ("x", "y", "angle")}, "scan": scan, "floor_spots": floors,
                "stack": round(stack, 2), "expect_floor_mz": FLOOR_MZ, "expect_top_mz": round(FLOOR_MZ + stack, 2)})
    os.makedirs(BLANK, exist_ok=True)
    rec = {"scan": scan, "blank_level_above_bed": round(level, 2), "note": "scan heights are relative: absolute level read about 3.6 mm high on 2026-11-09",
           "cutouts_work_mm": [{k: v for k, v in co.items() if k != "label"} for co in cutouts],
           "placed": {"board": "usb-power-switch carrier", **pl, "footprint_work": [list(map(lambda v: round(v, 2), w_pt(p, pl))) for p in Polygon(job["board"]["outline"]).buffer(1.0).exterior.coords[::4]]},
           "floor_spots": floors}
    with open(os.path.join(BLANK, scan + ".json"), "w") as f:
        json.dump(rec, f, indent=1)
    with open(os.path.join(OUT, "mill_usb_switch.json"), "w") as f:
        json.dump(job, f)
    title = "Scan %s. Grey: blank, dark: cut away. Green: this board (orange tabs).\nMagenta x: blank touches, cyan +: floor touches. Red: pocket walls." % scan
    picture(z, ox, oy, c, level, job, pl, floors, os.path.join(BLANK, scan + ".png"), title)
    picture(z, ox, oy, c, level, job, pl, floors, os.path.join(OUT, "mill_usb_switch.png"), title)
    print("blank level %.2f (scan), stack above floor %.2f, %d cut-outs" % (level, stack, len(cutouts)))
    for co in cutouts:
        print("   cut-out X %(x0).1f-%(x1).1f  Y %(y0).1f-%(y1).1f  %(below_blank).2f below" % co)
    print("board at work X %.1f Y %.1f, turned %d, scan coverage under it %.0f%%" % (pl["x"], pl["y"], pl["angle"], 100 * pl["coverage"]))
    print("floor touches", floors, "expect top %.2f floor %.2f (probe machine Z)" % (job["expect_top_mz"], FLOOR_MZ))


if __name__ == "__main__":
    main()
