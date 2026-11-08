# usb-power-switch

Turns a small 5 V line laser on and off from a Waveshare RP2040-Zero
running CircuitPython. You control it by sending commands over the
board's USB serial port.

- `code/`: the CircuitPython code. Everything in it is copied to the
  board's `CIRCUITPY` drive.
- `design/`: circuit design ([design/circuit.md](design/circuit.md)) and
  the carrier board and case model ([design/mockup.md](design/mockup.md)).

## Usage

```sh
just deploy    # copy code/ to /Volumes/CIRCUITPY (the board restarts by itself)
just monitor   # open the serial console
just render    # preview images of the board and case
just stl       # printable case STLs
```

In the console, type `on`, `off`, `toggle`, `status` or `help` and press
Enter.
