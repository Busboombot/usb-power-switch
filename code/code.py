"""Laser controller.

Send commands over the USB serial port (115200 baud), one per line:
    on, off, toggle, status, help

GP2 drives the transistor that switches the laser.
The front LED shows the state: dim green = laser off, red = laser on.
"""
import sys
import time
import board
import digitalio
import neopixel_write
import supervisor

LASER_PIN = board.GP2

laser = digitalio.DigitalInOut(LASER_PIN)
laser.switch_to_output(value=False)

led = digitalio.DigitalInOut(board.NEOPIXEL)
led.switch_to_output()

# Most NeoPixels want green-red-blue byte order. If red shows up as green
# on your board, set this to False.
GRB_ORDER = True


def show(r, g, b):
    if GRB_ORDER:
        neopixel_write.neopixel_write(led, bytearray([g, r, b]))
    else:
        neopixel_write.neopixel_write(led, bytearray([r, g, b]))


def set_laser(on):
    laser.value = on
    if on:
        show(40, 0, 0)
    else:
        show(0, 8, 0)


def status():
    print("laser on" if laser.value else "laser off")


HELP = "commands: on, off, toggle, status, help"


def handle(cmd):
    if cmd == "on":
        set_laser(True)
        status()
    elif cmd == "off":
        set_laser(False)
        status()
    elif cmd == "toggle":
        set_laser(not laser.value)
        status()
    elif cmd == "status":
        status()
    elif cmd == "help":
        print(HELP)
    else:
        print("unknown command:", cmd)
        print(HELP)


set_laser(False)
print("Laser controller ready.", HELP)

line = ""
while True:
    while supervisor.runtime.serial_bytes_available:
        ch = sys.stdin.read(1)
        if ch in "\r\n":
            if line.strip():
                print()
                handle(line.strip().lower())
            line = ""
        elif ch in "\x08\x7f":  # backspace
            if line:
                line = line[:-1]
                sys.stdout.write("\b \b")
        elif " " <= ch <= "~":  # ignore other control characters
            line += ch
            sys.stdout.write(ch)  # echo so you can see what you type
    time.sleep(0.01)
