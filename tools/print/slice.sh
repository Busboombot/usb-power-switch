#!/usr/bin/env bash
# Slice the printable STLs (design/cad/stl/, from `just stl`) for a Bambu Lab
# A1 with a 0.4 mm nozzle, generic PLA, on the textured PEI plate.
# Writes design/cad/gcode/<name>.gcode.3mf, ready for bambu_send.py.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
B=${BAMBU_STUDIO:-/Applications/BambuStudio.app/Contents/MacOS/BambuStudio}
P=$here/profiles
S=$root/design/cad/stl
O=$root/design/cad/gcode
mkdir -p "$O"

sl() {  # sl <name> <stl>...   (one plate, parts auto-arranged)
  local name=$1; shift
  # run in $O: Bambu Studio drops a result.json in the current directory
  (cd "$O" && "$B" --slice 0 --arrange 1 \
      --load-settings "$P/machine_a1.json;$P/process_a1.json" \
      --load-filaments "$P/filament_pla_a1.json" \
      --outputdir "$O" --export-3mf "$name.gcode.3mf" "$@" > "$O/$name.log" 2>&1) \
    || { echo "FAILED: $name (see $O/$name.log)" >&2; exit 1; }
  local t
  t=$(unzip -p "$O/$name.gcode.3mf" Metadata/plate_1.gcode | grep -m1 -o 'total estimated time: [^;]*' || true)
  echo "$O/$name.gcode.3mf  ${t:-?}"
}

sl usb_switch_case_cable "$S/case_bottom_cable.stl" "$S/case_lid_cable.stl"
sl usb_switch_case_molex "$S/case_bottom_molex.stl" "$S/case_lid_molex.stl"
sl usb_switch_mockups "$S/carrier_mock_cable.stl" "$S/carrier_mock_molex.stl" "$S/module_mock.stl" "$S/module_mock.stl"
