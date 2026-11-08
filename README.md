# usb-power-switch

Turns a small 5 V line laser on and off from a Waveshare RP2040-Zero
running CircuitPython. You control it by sending commands over the
board's USB serial port.

- `code/`: the CircuitPython code. Everything in it is copied to the
  board's `CIRCUITPY` drive.
- `design/`: circuit design. See [design/circuit.md](design/circuit.md).

## Usage

```sh
just deploy    # copy code/ to /Volumes/CIRCUITPY (the board restarts by itself)
just monitor   # open the serial console
```

In the console, type `on`, `off`, `toggle`, `status` or `help` and press
Enter.
