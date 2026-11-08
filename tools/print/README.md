# Printing tools

Scripts for slicing the case and sending it to the Bambu Lab printers over
the LAN. They were used to print the first fit-test set.

| File | What it does |
|------|--------------|
| `slice.sh` | Slices `design/cad/stl/` into three plates in `design/cad/gcode/` (`just slice`) |
| `bambu_status.py` | Prints a printer's state, progress, temperatures and loaded filament. Read-only |
| `bambu_snapshot.py` | Saves one frame from the printer's camera. Read-only |
| `bambu_send.py` | Uploads a `.gcode.3mf` and starts it, using the external spool |
| `flatten_profile.py` | Merges a Bambu Studio system profile with the profiles it inherits from |
| `profiles/` | The flattened A1 profiles `slice.sh` uses |

## Plates

| Plate | Parts | Time (A1, 0.2 mm layers) |
|-------|-------|--------------------------|
| `usb_switch_case_cable` | cable-version bottom and lid | about 28 min |
| `usb_switch_case_molex` | Molex-version bottom and lid | about 25 min |
| `usb_switch_mockups` | both carrier mockups, two module mockups | about 22 min |

## Talking to a printer

The printers must be in LAN mode. Each script takes the printer's address
and serial number, and the **name** of an environment variable holding its
access code, so the code never appears on the command line. Addresses,
serials and access codes are in the busboom-home-network repo
(`docs/3d-printers.md` and `.env`).

```sh
export VERLET_ACCESS_CODE=...   # from busboom-home-network/.env
uv run --with paho-mqtt python tools/print/bambu_status.py verlet=<ip>,<serial>,VERLET_ACCESS_CODE
uv run python tools/print/bambu_snapshot.py <ip> VERLET_ACCESS_CODE plate.jpg
uv run --with paho-mqtt python tools/print/bambu_send.py <ip> <serial> VERLET_ACCESS_CODE \
    design/cad/gcode/usb_switch_case_cable.gcode.3mf "usb switch case"
```

Check the plate is clear before sending (the snapshot helps). `bambu_send.py`
uploads over FTPS (port 990), checks the size, starts the print over MQTT
(port 8883) with bed levelling on and the other calibrations off, and
reports the printer's status for about 40 seconds.

## The profiles

`profiles/` holds Bambu Studio 02.08.02.61 system profiles, flattened with
`flatten_profile.py`:

- `machine_a1.json`: Bambu Lab A1 0.4 nozzle. The A1 start and end G-code
  from the "Bambu Lab A1 0.4 nozzle template" profiles is merged in. The
  generic start G-code is not safe on an A1.
- `process_a1.json`: 0.20mm Standard @BBL A1, with `curr_bed_type` set to
  "Textured PEI Plate" (65 °C bed; the default is Cool Plate at 35 °C).
- `filament_pla_a1.json`: Generic PLA @BBL A1.
