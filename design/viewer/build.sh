#!/usr/bin/env bash
# Build the interactive 3D viewer pages, viewer/cable.html and viewer/molex.html.
# Each part of the assembly is exported from the OpenSCAD model as its own
# STL (pieces.scad), then packed into template.html by pack.py.
set -euo pipefail
cd "$(dirname "$0")"
out=../../viewer
mkdir -p "$out"

common="bottom lid carrier_fr4 carrier_copper carrier_pads mod_pcb mod_pads usb btn_body btn_cap led flash
        mod_under r1_body r1_leads r2_body r2_leads q1_body q1_leads"
extra() {
  case $1 in
    cable) echo "screws jacket wire_red wire_black" ;;
    molex) echo "hdr_body hdr_pins" ;;
  esac
}

for v in cable molex; do
  dir=stl/$v
  rm -rf "$dir"; mkdir -p "$dir"
  for p in $common $(extra "$v"); do
    log=$(openscad --backend=manifold -D 'part="none"' -D "variant=\"$v\"" -D "piece=\"$p\"" \
            --export-format binstl -o "$dir/$p.stl" pieces.scad 2>&1) \
      || { echo "FAILED: $v/$p" >&2; echo "$log" >&2; exit 1; }
    if grep -qE 'WARNING|ERROR' <<< "$log"; then
      echo "FAILED (warnings): $v/$p" >&2; grep -E 'WARNING|ERROR' <<< "$log" >&2; exit 1
    fi
  done
  uv run -q --with numpy python pack.py "$dir" "$v" template.html "$out/$v.html"
done
