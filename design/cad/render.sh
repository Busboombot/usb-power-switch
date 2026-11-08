#!/usr/bin/env bash
# Render preview images of every part into renders/.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p renders
S=usb_power_switch.scad

r() {  # r <output> <camera> <extra -D args...>
  local out=$1 cam=$2; shift 2
  openscad --colorscheme=Tomorrow --imgsize=1600,1100 --autocenter --viewall \
    --camera="$cam" "$@" -o "renders/$out.png" "$S" >/dev/null 2>&1 \
    || { echo "FAILED: $out" >&2; return 1; }
  echo "renders/$out.png"
}

ISO=0,0,0,55,0,30,0
ISO_BACK=0,0,0,55,0,210,0
TOP=0,0,0,0,0,0,0
SIDE=0,0,0,90,0,0,0

r module            $ISO  -D 'part="module"'
r module_bottom     0,0,0,125,0,30,0 -D 'part="module"'
r carrier_top       $ISO  -D 'part="carrier"'
r carrier_underside 0,0,0,125,0,30,0 -D 'part="carrier_assembly"' -D 'variant="molex"'
r carrier_drawing   $TOP  -D 'part="carrier_drawing"' --projection=o
r carrier_assembly  $ISO  -D 'part="carrier_assembly"' -D 'variant="molex"'
for v in molex cable; do
  r "exploded_$v"   $ISO      -D 'part="exploded"' -D "variant=\"$v\""
  r "assembly_$v"   $ISO      -D 'part="assembly"' -D "variant=\"$v\""
  r "assembly_${v}_back" $ISO_BACK -D 'part="assembly"' -D "variant=\"$v\""
  r "section_$v"    $SIDE     -D 'part="section"' -D "variant=\"$v\"" --projection=o --render --backend=manifold
  r "bottom_$v"     $ISO      -D 'part="bottom"'   -D "variant=\"$v\""
  r "lid_$v"        0,0,0,125,0,30,0 -D 'part="lid"' -D "variant=\"$v\""
done
