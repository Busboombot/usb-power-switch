#!/usr/bin/env bash
# Export printable STLs, already in print orientation:
#   case_bottom_*, case_lid_* (lid flipped upside down)
#   carrier_mock_* (printed upside down, top face on the bed)
#   module_mock
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p stl
ex() {  # ex <name> <-D args...>
  local name=$1; shift
  local log
  log=$(openscad --backend=manifold "$@" -o "stl/$name.stl" usb_power_switch.scad 2>&1) \
    || { echo "FAILED: $name" >&2; echo "$log" >&2; exit 1; }
  if grep -qE 'WARNING|ERROR' <<< "$log"; then
    echo "FAILED (warnings): $name" >&2; grep -E 'WARNING|ERROR' <<< "$log" >&2; exit 1
  fi
  echo "stl/$name.stl"
}
for v in molex cable; do
  ex "case_bottom_$v"  -D 'part="bottom_print"'       -D "variant=\"$v\""
  ex "case_lid_$v"     -D 'part="lid_print"'          -D "variant=\"$v\""
  ex "carrier_mock_$v" -D 'part="carrier_mock_print"' -D "variant=\"$v\""
done
ex module_mock -D 'part="module_mock_print"'
