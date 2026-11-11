# /// script
# requires-python = ">=3.11"
# dependencies = ["shapely>=2", "matplotlib", "numpy"]
# ///
"""Toolpaths for milling the carrier board on the Carvera, from the OpenSCAD model.

    uv run tools/mill/cam.py        (or: just cam)

Reads the copper, outline, holes and tabs from design/cad/usb_power_switch.scad and writes
tools/mill/out/carrier_toolpaths.json and carrier_toolpaths.png.

Everything is in board coordinates: mm, x from the USB end, y from the centreline, copper side up.
No Z values for the surface: the Test and Dev program on kinsey probes the blank, places the board
and turns these paths into G-code. Depths here are below the probed surface (isolation) or relative
to the blank's underside (drilling, outline, tabs).

Job sequence: T4 isolate, T3 clear, T6 drill, T5 mill the J1 holes, T1 cut out. All six are the
standard buildout, so the changer does every swap.

The board has no solder mask, so every bit of copper that isn't a pad or a trace is milled off:
T4 cuts a ring round all the copper, plus more rings wherever T3 can't reach (the 0.6 mm gaps
between the lanes and the castellation pads, corners). T3, a 1 mm flat end mill, pockets the rest.
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, MultiLineString, Point, Polygon
from shapely.ops import substring, unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCAD = os.path.join(ROOT, "design", "cad", "usb_power_switch.scad")
OUT = os.path.join(ROOT, "tools", "mill", "out")
OPENSCAD = os.environ.get("OPENSCAD", "openscad")

# Tools and settings: starting values for FR4 from projects/tool-racks/README.md (carvera repo)
ISO = {"tool": 4, "name": "30 deg V-bit, 0.2 tip", "tip": 0.2, "angle": 30.0, "depth": 0.08,
       "rpm": 12000, "feed": 300, "plunge": 100}
CLR = {"tool": 3, "name": "1.0 mm flat end mill", "dia": 1.0, "depth": 0.1, "rpm": 12000, "feed": 300,
       "plunge": 100, "inset": 0.6, "step": 0.45}
DRILL = {"tool": 6, "name": "1.0 mm carbide drill", "dia": 1.0, "rpm": 12000, "plunge": 100,
         "below": 0.5, "pecks": 2}
HOLES = {"tool": 5, "name": "0.8 mm corn cutter", "dia": 0.8, "rpm": 12000, "feed": 120, "plunge": 60,
         "below": 0.5, "pitch": 0.3, "segs": 24}
OUTLINE = {"tool": 1, "name": "2.0 mm corn cutter", "dia": 2.0, "rpm": 10000, "feed": 300,
           "plunge": 100, "step": 0.4, "below": 0.1}
TRAVEL = 2.0        # mm above the surface between cuts


def openscad(script, out, quiet=True):
    with tempfile.NamedTemporaryFile("w", suffix=".scad", delete=False) as f:
        f.write(script)
    try:
        r = subprocess.run([OPENSCAD, *(["-q"] if quiet else []), "-o", out, f.name], capture_output=True, text=True)
    finally:
        os.unlink(f.name)
    if r.returncode != 0:
        sys.exit("openscad failed: " + r.stderr[-500:])
    return r.stderr


def model_data(tmp):
    """Numbers from the model, by echo. part="none" renders nothing of its own."""
    names = ["car_l", "car_w", "tab_w", "tab_t", "tabs", "tht_drill", "j1_drill", "j1_x", "j1_y",
             "r1_holes", "r2_holes", "q1_e", "q1_b", "q1_c", "mod_l", "mod_w", "pad_band", "iso_gap", "tht_gap"]
    echo = "echo(CAM = [%s]);" % ", ".join(names)
    err = openscad('include <%s>\npart = "none";\n%s\ncube(0.01);\n' % (SCAD, echo), os.path.join(tmp, "x.stl"), quiet=False)
    m = re.search(r"ECHO: CAM = (\[.*\])", err)
    if not m:
        sys.exit("no CAM echo from openscad:\n" + err[-500:])
    return dict(zip(names, json.loads(m.group(1))))


def svg_polygons(path):
    """OpenSCAD's 2D SVG: every ring as a polygon, y flipped back to model y."""
    polys = []
    for d in re.findall(r' d="([^"]+)"', open(path).read()):
        for ring in re.split(r"(?=M)", d):
            pts = [(float(x), -float(y)) for x, y in re.findall(r"(-?[\d.e+-]+),(-?[\d.e+-]+)", ring)]
            if len(pts) > 2:
                polys.append(Polygon(pts).buffer(0))
    return polys


def shapes(tmp):
    cu_svg, ol_svg = os.path.join(tmp, "cu.svg"), os.path.join(tmp, "ol.svg")
    openscad("use <%s>\n$fn = 96;\ncopper_2d();\n" % SCAD, cu_svg)
    openscad("use <%s>\n$fn = 96;\ncarrier_outline_2d();\n" % SCAD, ol_svg)
    copper = unary_union(svg_polygons(cu_svg))      # pads come out filled; their holes are drilled
    board = max(svg_polygons(ol_svg), key=lambda p: p.area)
    return copper, Polygon(board.exterior)


def geoms(g):
    return list(g.geoms) if hasattr(g, "geoms") else [g]


def lines_of(g):
    out = []
    for p in geoms(g):
        if isinstance(p, Polygon):
            out += [LineString(r.coords) for r in [p.exterior, *p.interiors]]
        elif isinstance(p, LineString):
            out.append(p)
        elif isinstance(p, MultiLineString):
            out += list(p.geoms)
    return out


def order_paths(paths, start=(0.0, 0.0)):
    """Greedy nearest-next. Open paths may run backwards; closed rings start at their nearest vertex."""
    left, out, here = list(paths), [], np.array(start)
    while left:
        best = None
        for i, p in enumerate(left):
            c = np.array(p)
            if len(c) > 2 and np.allclose(c[0], c[-1]):
                k = int(np.argmin(((c[:-1] - here) ** 2).sum(1)))
                d, cand = ((c[k] - here) ** 2).sum(), np.vstack([c[k:-1], c[:k + 1]])
            else:
                d0, d1 = ((c[0] - here) ** 2).sum(), ((c[-1] - here) ** 2).sum()
                d, cand = (d0, c) if d0 <= d1 else (d1, c[::-1])
            if best is None or d < best[0]:
                best = (d, i, cand)
        _, i, cand = best
        left.pop(i)
        out.append(cand)
        here = cand[-1]
    return out


def vbit_width():
    return ISO["tip"] + 2 * ISO["depth"] * math.tan(math.radians(ISO["angle"] / 2))


def rings(copper, off, keep, simplify=0.003):
    out = []
    for ln in lines_of(copper.buffer(off, quad_segs=32).boundary.intersection(keep)):
        ln = ln.simplify(simplify)
        if ln.length > 0.05:
            out.append([tuple(p) for p in ln.coords])
    return out


def swept(paths, r):
    return unary_union([LineString(p).buffer(r, quad_segs=8) for p in paths if len(p) > 1])


def clearing(copper, board):
    """T3 pocket over the whole board: the cutter's centre stays CLR["inset"] from the copper and
    on the board (its edge may run up to r past the outline, which T1 cuts away). Rings step inward
    until nothing is left; a step under the radius leaves nothing between rings."""
    r = CLR["dia"] / 2
    if CLR["step"] > r:
        sys.exit("T3 step %.2f is over its radius: it would leave copper between rings" % CLR["step"])
    locus = board.difference(copper.buffer(CLR["inset"], quad_segs=32))
    paths, k = [], 0
    while True:
        ring = locus.buffer(-k * CLR["step"], quad_segs=16)
        if ring.is_empty:
            break
        for ln in lines_of(ring):
            ln = ln.simplify(0.005)
            if ln.length > 0.05:
                paths.append([tuple(p) for p in ln.coords])
        k += 1
    return order_paths(paths, start=(0.0, -12.0))


def isolation(copper, board, clear):
    """T4. The first ring, width/2 out, goes all round every island and is what isolates the nets.
    Further rings, width/2 apart, run only where copper would still be left after that ring and T3:
    the gaps too narrow for the 1 mm cutter (0.6 between the lanes and the castellation pads), and
    corners. Rings width/2 apart cover any gap up to twice the last offset: once a ring's offset is
    over half a gap it disappears there, so a coarser step can skip the middle of a gap."""
    width = vbit_width()
    islands = geoms(copper)
    # every net must stay its own island after the first pass, with a little to spare
    merged = geoms(copper.buffer(width / 2 + 0.02))
    if len(merged) != len(islands):
        sys.exit("isolation check failed: %d copper islands merge into %d at a %.3f mm cut"
                 % (len(islands), len(merged), width))
    # rings may run 0.15 past the outline (cut away by T1), so no sliver is left along the module cutout
    keep = board.buffer(0.15)
    first = rings(copper, width / 2, keep)
    need = board.difference(copper).difference(swept(first, width / 2)).difference(swept(clear, CLR["dia"] / 2))
    need = need.buffer(-0.005).buffer(0.005)        # drop slivers thinner than 0.01
    paths, offsets = list(first), [width / 2]
    k = 2
    while not need.is_empty and k * width / 2 <= CLR["inset"] + CLR["dia"] / 2:
        off = k * width / 2
        near = need.buffer(width / 2)
        extra = []
        for p in rings(copper, off, keep):
            for ln in lines_of(LineString(p).intersection(near)):
                if ln.length > 0.05:
                    extra.append([tuple(q) for q in ln.coords])
        if extra:
            offsets.append(off)
            paths += extra
            need = need.difference(swept(extra, width / 2)).buffer(-0.005).buffer(0.005)
        k += 1
    return order_paths(paths, start=(0.0, -12.0)), width, offsets


def drills(d):
    holes = [*d["r1_holes"], *d["r2_holes"], d["q1_e"], d["q1_b"], d["q1_c"]]
    return [list(map(float, c[0])) for c in order_paths([[tuple(h)] for h in holes], start=(26.0, 8.0))]


def j1_holes(d):
    """J1's wire holes, milled with T5: a helix down at radius (hole - tool) / 2."""
    holes = [[float(d["j1_x"]), float(y)] for y in d["j1_y"]]
    return holes, round((d["j1_drill"] - HOLES["dia"]) / 2, 3)


def outline(board, d):
    """Outside profile, climb cut (clockwise seen from above), split into pieces at the tabs."""
    r = OUTLINE["dia"] / 2
    path = board.buffer(r, quad_segs=16, join_style="round")
    ring = LineString(path.exterior.coords)
    if Polygon(ring).exterior.is_ccw:
        ring = LineString(list(ring.coords)[::-1])
    L = ring.length
    s0 = ring.project(Point(d["car_l"] + r, 0.0))     # start in the middle of the back edge
    spans = []
    for x, side in d["tabs"]:
        s = (ring.project(Point(x, side * (d["car_w"] / 2 + r))) - s0) % L
        h = d["tab_w"] / 2 + r
        spans.append((s - h, s + h))
    spans.sort()
    cuts = [0.0]
    for a, b in spans:
        cuts += [a, b]
    cuts.append(L)
    pieces = []
    for k in range(len(cuts) - 1):
        a, b = cuts[k], cuts[k + 1]
        seg = substring(ring, (s0 + a) % L, (s0 + b) % L) if (s0 + a) % L < (s0 + b) % L or b - a >= L else None
        if seg is None:     # piece wraps past the ring's own start
            seg = LineString(list(substring(ring, (s0 + a) % L, L).coords) + list(substring(ring, 0, (s0 + b) % L).coords)[1:])
        pieces.append({"tab": k % 2 == 1, "pts": [list(map(float, p)) for p in seg.coords]})
    return pieces, L


def probe_spots(d):
    """Blank-top probe touches in board coordinates, a 3 x 3 grid over the board's box."""
    xs = (1.0, d["car_l"] / 2, d["car_l"] - 1.0)
    ys = (-(d["car_w"] / 2 - 1.0), 0.0, d["car_w"] / 2 - 1.0)
    return [[x, y] for y in ys for x in xs]


def length(paths):
    return sum(LineString(p).length for p in paths if len(p) > 1)


def preview(copper, board, iso, clear, holes, j1, j1_r, pieces, spots, d, width, offsets, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(13, 9), dpi=130)
    ax.fill(*board.exterior.xy, color="#2e8b57", zorder=1)
    for g in geoms(copper):
        ax.fill(*g.exterior.xy, color="#c8743a", zorder=2)
    swept = unary_union([LineString(p).buffer(CLR["dia"] / 2) for p in clear if len(p) > 1]
                        + [LineString(p).buffer(width / 2) for p in iso if len(p) > 1]).intersection(board)
    for g in geoms(swept):
        ax.fill(*g.exterior.xy, color="#d9d4c7", zorder=2.5)
        for r in g.interiors:
            ax.fill(*r.xy, color="#2e8b57", zorder=2.6)
    for g in geoms(copper):
        ax.fill(*g.exterior.xy, color="#c8743a", zorder=2.7)
    for p in clear:
        c = np.array(p)
        ax.plot(c[:, 0], c[:, 1], color="#7a5cff", lw=0.5, zorder=3.5)
    for p in iso:
        c = np.array(p)
        ax.plot(c[:, 0], c[:, 1], color="#4cc9f0", lw=0.7, zorder=4)
    for h in holes:
        ax.add_patch(plt.Circle(h, DRILL["dia"] / 2, color="black", zorder=6))
    for h in j1:
        ax.add_patch(plt.Circle(h, j1_r + HOLES["dia"] / 2, color="#202020", zorder=6))
        ax.add_patch(plt.Circle(h, j1_r, fill=False, ec="white", lw=0.8, zorder=6.5))
    for pc in pieces:
        c = np.array(pc["pts"])
        ax.plot(c[:, 0], c[:, 1], color="#ff7f11" if pc["tab"] else "#ffd166", lw=4 if pc["tab"] else 1.6, zorder=5)
    a = np.array(pieces[0]["pts"][0])
    ax.annotate("T1 start", a, a + [1.5, 2.5], fontsize=9, arrowprops={"arrowstyle": "->"})
    for x, y in spots:
        ax.plot(x, y, "x", color="magenta", ms=10, mew=2, zorder=7)
    ax.set_aspect("equal")
    ax.set_xlim(-3, d["car_l"] + 3)
    ax.set_ylim(-d["car_w"] / 2 - 3, d["car_w"] / 2 + 3)
    ax.grid(True, alpha=0.25)
    ax.set_xlabel("x, mm from the USB end")
    ax.set_ylabel("y, mm from the centreline")
    ax.set_title("Carrier %g x %g mm, copper side up.  Blue: T4 isolation (%d rings, %.2f wide)  Beige: bare after T4 + T3 (purple: T3 paths)\n"
                 "Black: T6 drill  Black with white ring: T5 J1 holes %.1f mm  Yellow: T1 outline  Orange: tabs  Magenta: probe touches"
                 % (d["car_l"], d["car_w"], len(offsets), width, d["j1_drill"]), fontsize=10)
    fig.savefig(path, bbox_inches="tight", facecolor="white")


def main():
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        d = model_data(tmp)
        copper, board = shapes(tmp)
    clear = clearing(copper, board)
    iso, width, offsets = isolation(copper, board, clear)
    left = board.difference(copper).difference(swept(iso, width / 2)).difference(swept(clear, CLR["dia"] / 2))
    biggest = max((g.area for g in geoms(left)), default=0.0)
    holes = drills(d)
    j1, j1_r = j1_holes(d)
    pieces, ring_len = outline(board, d)
    spots = probe_spots(d)
    passes = math.ceil(1.9 / OUTLINE["step"])
    turns = math.ceil((1.9 + HOLES["below"]) / HOLES["pitch"]) + 1
    est = {"isolate_s": round(length(iso) / ISO["feed"] * 60 + len(iso) * 2),
           "clear_s": round(length(clear) / CLR["feed"] * 60 + len(clear) * 2),
           "drill_s": round(len(holes) * 6),
           "holes_s": round(len(j1) * (turns * 2 * math.pi * j1_r / HOLES["feed"] * 60 + 4)),
           "outline_s": round(ring_len * passes / OUTLINE["feed"] * 60)}
    job = {
        "board": {"length": d["car_l"], "width": d["car_w"],
                  "outline": [list(map(float, p)) for p in board.exterior.coords],
                  "keepout": OUTLINE["dia"]},
        "isolate": dict(ISO, passes=len(offsets), width=round(width, 3), offsets=[round(o, 3) for o in offsets], paths=[[list(map(float, q)) for q in p] for p in iso]),
        "clear": dict(CLR, paths=[[list(map(float, q)) for q in p] for p in clear]),
        "drill": dict(DRILL, holes=holes),
        "holes": dict(HOLES, hole=d["j1_drill"], r=j1_r, holes=j1),
        "outline": dict(OUTLINE, tab_t=d["tab_t"], pieces=pieces),
        "probe": spots,
        "travel": TRAVEL,
        "estimate": est,
        "source": os.path.relpath(SCAD, ROOT),
    }
    with open(os.path.join(OUT, "carrier_toolpaths.json"), "w") as f:
        json.dump(job, f, indent=1)
    preview(copper, board, iso, clear, holes, j1, j1_r, pieces, spots, d, width, offsets, os.path.join(OUT, "carrier_toolpaths.png"))
    print("board %g x %g, %d copper islands, all isolated at a %.3f mm cut" % (d["car_l"], d["car_w"], len(geoms(copper)), width))
    print("T4: %d paths, %.0f mm; T3: %d paths, %.0f mm (copper left off the pads and traces: %.3f mm2, largest bit %.4f mm2); T6: %d holes; T5: %d holes %.1f mm; "
          "T1: outline %.1f mm, %d tabs" % (len(iso), length(iso), len(clear), length(clear), left.area, biggest, len(holes), len(j1),
                                             d["j1_drill"], ring_len, len(d["tabs"])))
    print("estimate: " + ", ".join("%s %d s" % (k[:-2], v) for k, v in est.items()) + ", total %.0f min" % (sum(est.values()) / 60))
    print("wrote", os.path.relpath(OUT, ROOT) + "/carrier_toolpaths.{json,png}")


if __name__ == "__main__":
    main()
