# RP2040-Zero scan

`rp2040-zero-scan.stl` is a Revopoint 3D scan of the module: one patch of
the top side and one of the bottom, in arbitrary positions. The scripts
turn it into the measurements used in `../cad/usb_power_switch.scad`.

```sh
mkdir -p out
uv run --with numpy --with pillow python analyze.py rp2040-zero-scan.stl out   # flatten each patch, write height grids
uv run --with numpy python measure.py out                                      # list raised parts with sizes and heights
uv run --with numpy --with pillow python overlay.py out                        # draw the model's outlines on the height maps
```

- `analyze.py` splits the mesh into its two patches, fits the board plane
  of each, rotates it flat with the long edge along x, and rasterizes a
  height map at 0.1 mm.
- `measure.py` finds parts that stand above the board and reports each
  one's size, measured at half its height because the scan blurs edges.
- `overlay.py` draws the part outlines from the model over the height
  maps, as a check: `overlay_top.png`, `overlay_bottom.png`.

On the top patch, x = 0 is the USB end. On the bottom patch, x = 0 is the
far end, so model x = 23.5 − scan x. The bottom patch is a little short
(23.1 mm), so its x positions are only good to about ±0.5 mm.
