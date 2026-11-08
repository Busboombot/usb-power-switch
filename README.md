# usb-power-switch

Turns a small 5 V line laser on and off from a Waveshare RP2040-Zero
running CircuitPython. You control it by sending commands over the
board's USB serial port.

- `code/`: the CircuitPython code. Everything in it is copied to the
  board's `CIRCUITPY` drive.
- `design/`: circuit design ([design/circuit.md](design/circuit.md)) and
  the carrier board and case model ([design/mockup.md](design/mockup.md)).
- `viewer/`: interactive 3D views of the assembled case, built from the
  model by `just viewer`. Open them on the project site:
  [cable version](https://busboombot.github.io/usb-power-switch/viewer/cable.html),
  [Molex version](https://busboombot.github.io/usb-power-switch/viewer/molex.html).
- `tools/print/`: slicing and Bambu printer scripts
  ([tools/print/README.md](tools/print/README.md)).

## Usage

```sh
just deploy    # copy code/ to /Volumes/CIRCUITPY (the board restarts by itself)
just monitor   # open the serial console
just render    # preview images of the board and case
just stl       # printable case STLs
just viewer    # rebuild the 3D viewer pages (commit viewer/ to update the site)
just slice     # slice the STLs for a Bambu A1
```

Needs a recent [OpenSCAD](https://openscad.org) development snapshot (for the manifold backend),
[uv](https://docs.astral.sh/uv/) for the Python scripts, and Bambu Studio
for slicing.

In the console, type `on`, `off`, `toggle`, `status` or `help` and press
Enter.
