# Laser switch circuit

A Waveshare RP2040-Zero running CircuitPython switches a small 5 V line
laser on and off. The laser is powered from the board's USB 5 V. An NPN
transistor switches the laser's ground connection, and the board drives
the transistor from pin GP2.

## Parts

| Ref | Part | Notes |
|-----|------|-------|
| U1  | Waveshare RP2040-Zero | Powered and controlled over USB-C |
| Q1  | 2N2222 or 2N3904 NPN transistor | Good to about 100 mA of laser current; see "Laser current" below |
| R1  | 1 kΩ resistor | Base resistor, GP2 to Q1 base. Use 470 Ω if the laser draws 50–100 mA |
| R2  | 10 kΩ resistor | Pull-down, Q1 base to GND. Keeps the laser off during boot and reset |
| L1  | 5 V line laser module | Must have its own driver board (see below) |

## Schematic

```
U1 5V ────────────────────── L1 +  (red)
                             L1 −  (black)
                                │
                                C
U1 GP2 ──[ R1 1kΩ ]──┬───── B  Q1 (NPN)
                     │          E
                  [R2 10kΩ]     │
                     │          │
U1 GND ──────────────┴──────────┘
```

## Connections

| From | To |
|------|----|
| U1 5V | L1 + |
| L1 − | Q1 collector |
| U1 GP2 | R1 |
| R1 (other end) | Q1 base, R2 |
| R2 (other end) | GND |
| Q1 emitter | GND |

## Design notes

- **Low-side switching.** The laser's + wire stays on 5 V and the
  transistor connects its − wire to ground. With an NPN transistor the
  base only needs to be about 0.7 V above ground, which the 3.3 V GPIO
  provides easily.
- **Base current.** With R1 = 1 kΩ: (3.3 V − 0.7 V) / 1 kΩ ≈ 2.6 mA, enough
  to fully switch on about 50 mA of laser current. R1 = 470 Ω gives about
  5.5 mA, good to about 100 mA. Both are within what an RP2040 pin can
  supply.
- **Laser current.** Measure or look up what the laser draws at 5 V.
  - Up to about 50 mA: R1 = 1 kΩ.
  - 50–100 mA: R1 = 470 Ω.
  - More than 100 mA: replace Q1 with a logic-level N-channel MOSFET
    (for example the AO3400) wired the same way: drain to L1 −, source to
    GND, gate through about 100 Ω to GP2, and 10 kΩ from gate to GND.
- **Laser driver.** Most small line-laser modules have a constant-current
  driver built in and run straight from 5 V. A bare laser diode, with no
  small circuit board on it, must not be connected this way. It needs a
  current-limiting driver.
- **Never drive the laser directly from GP2.** An RP2040 pin can only
  supply a few milliamps at 3.3 V.
- **USB power budget.** The laser's current comes out of the USB port
  together with the board's own (about 25 mA). A normal USB port supplies
  500 mA, so this is not a concern for a small laser.
- **Pinout.** Check the transistor's datasheet for which leg is emitter,
  base and collector. It varies between packages and manufacturers.

## Firmware interface

`code/code.py` reads commands from the USB serial console (115200 baud),
one per line: `on`, `off`, `toggle`, `status`, `help`. The front
NeoPixel shows the state: dim green means the laser is off, red means it
is on.
