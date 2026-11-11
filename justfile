device := "/Volumes/CIRCUITPY"

# List available targets
default:
    @just --list

# Copy the code/ directory onto the CircuitPython board
deploy:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -d "{{device}}" ]; then
        echo "{{device}} is not mounted. Is the board plugged in?" >&2
        exit 1
    fi
    cp -RX code/ "{{device}}/"
    # macOS adds com.apple.provenance to files anyway, which shows up on the
    # FAT drive as ._ files. Remove them.
    find "{{device}}" -name '._*' -type f -not -path '*/.Trashes/*' -delete
    sync
    echo "Deployed code/ to {{device}}"

# Render preview images of the board and case into design/cad/renders/
render:
    design/cad/render.sh

# Export printable case STLs into design/cad/stl/
stl:
    design/cad/stl.sh

# Build the interactive 3D viewer pages, viewer/cable.html and viewer/molex.html
viewer:
    design/viewer/build.sh

# Slice the printable STLs for a Bambu A1 into design/cad/gcode/
slice: stl
    tools/print/slice.sh

# Carvera toolpaths for the carrier board into tools/mill/out/
cam:
    uv run -q tools/mill/cam.py

# Place the carrier on a scanned PCB blank: just place GRID.npz SCAN_NAME
place grid scan: cam
    uv run -q tools/mill/place.py {{grid}} {{scan}}

# Open the board's serial console (quit: Ctrl-A, K, Y)
monitor:
    #!/usr/bin/env bash
    set -euo pipefail
    port=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)
    if [ -z "$port" ]; then
        echo "No /dev/cu.usbmodem* port found. Is the board plugged in?" >&2
        exit 1
    fi
    exec screen "$port" 115200
