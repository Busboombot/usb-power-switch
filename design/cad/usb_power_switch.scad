// USB power switch: RP2040-Zero on a single-sided through-hole carrier
// board, in a two-piece case.
//
// Select what to build with -D on the command line, e.g.
//   openscad -D 'part="lid"' -D 'variant="cable"' -o lid.stl usb_power_switch.scad
//
// Coordinates (mm): x runs along the length, x = 0 at the USB end of the
// module and carrier. y runs across: +y is the GP0..GP8 side of the
// module, -y the 5V/GND/3V3 side. z = 0 is the underside of the carrier.
//
// The carrier has copper on its top side only. The module sits on that
// side. Through-hole parts go in from the underside (bodies hang below
// the board) and are soldered on the top, so every joint is on one side.

/* [Selection] */
// module, carrier, carrier_drawing, carrier_assembly, bottom, lid, assembly, exploded, section,
// bottom_print, lid_print, carrier_mock_print, module_mock_print
part = "exploded";
// "molex" (vertical 0.1in header, plugs in from the bottom) or "cable" (pigtail with strain relief)
variant = "cable";

$fn = 48;
eps = 0.01;

// ===================== RP2040-Zero (Waveshare) =====================
mod_w = 18;
mod_l = 23.5;          // Waveshare drawing; the scan measures 23.53
mod_t = 1.0;
mod_bot_h = 1.05;      // tallest part on the underside (regulator, from scan)
pitch = 2.54;
side_pins = 9;         // castellations on each long side
end_pins = 5;          // castellations on the end opposite the USB
pin_off = (mod_l - (side_pins - 1) * pitch) / 2;  // first side pin from USB end (ASSUMED centered)
castle_d = 1.0;

usb_w = 8.94;          // USB-C receptacle
usb_h = 3.26;
usb_len = 7.95;        // back of the shell is 6.7 from the board edge (scan)
usb_protrude = 1.25;   // past the module's front edge
usb_top = 3.15;        // top of USB shell above module top surface (scan: 3.14)
btn_h = 2.5;           // button height above module top surface (scan: 2.45-2.49)
btn_size = [4.2, 3.2];  // button footprint (scan blur reads 4.4 x 3.5)

// Top-side parts, [x, y]: x from the USB end, y from the board centerline.
// Measured from a 3D scan of the module (design/scan/). BOOT is on the
// 5V side, RESET on the GP0 side; both sit the same distance from the USB.
boot_pos  = [16.0, -4.6];
reset_pos = [16.1,  4.45];
led_pos   = [15.65, 0];
led_size  = [1.9, 1.6, 0.7];
flash_pos = [12.4, 0];
flash_size = [2.0, 2.9, 0.56];
// Underside parts: [x, y, size x, size y, height], measured from the scan.
// x positions are +/- 0.5 (that side of the scan is incomplete).
bot_parts = [
  [12.55, 0, 7.3, 7.3, 0.92],   // RP2040
  [19.0,  0, 2.6, 3.3, 0.76],   // crystal
  [ 3.05, 0, 3.1, 2.1, 1.05],   // regulator
];

side_names_neg = ["5V","GND","3V3","GP29","GP28","GP27","GP26","GP15","GP14"];
side_names_pos = ["GP0","GP1","GP2","GP3","GP4","GP5","GP6","GP7","GP8"];
end_names      = ["GP9","GP10","GP11","GP12","GP13"];   // +y to -y

function side_x(k) = pin_off + k * pitch;
function end_y(k)  = (2 - k) * pitch;

// ===================== Carrier board =====================
pcb_t = 1.6;
car_margin = 2.5;              // carrier beyond module on each side (room for two traces)
car_w = mod_w + 2 * car_margin;
car_l = 39;
pad_band = 0.9;                // safe band under the module edge
pad_in = 0.7;                  // pad copper under module (0.2 back from cutout)
pad_out = 0.8;                 // pad copper past module edge (solder fillet)
pad_w = 1.5;
solder_gap = 0.1;
mod_z = pcb_t + solder_gap;    // module underside height

// Single-layer routing: two lanes outside the castellation pads
trace_w = 0.4;
lane_in = mod_w / 2 + pad_out + 0.45;   // 10.25
lane_out = lane_in + 0.7;               // 10.95

// Through-hole parts. Holes are [x, y].
tht_drill = 1.0;
tht_pad = 2.0;                 // big pads: holes are unplated on a single-sided board
res_pitch = 10.16;             // 1/4 W axial resistor lying flat
r1_holes = [[26.5,  6.5], [26.5,  6.5 - res_pitch]];  // 1k:  GP2 -> base
r2_holes = [[29.5, -6.5 + res_pitch], [29.5, -6.5]];  // 10k: base -> GND
q1_x = 33.5;                   // TO-92 standing, legs at 2.54 pitch (E B C)
q1_e = [q1_x, -pitch];
q1_b = [q1_x, 0];
q1_c = [q1_x, pitch];
q1_pad = 1.8;

// J1: two holes, 0.1in pitch. Header pins or 20 AWG pigtail wires.
j1_x = 36.5;
j1_y = [-pitch / 2, pitch / 2];  // pin 1 = +5V, pin 2 = LASER-
j1_drill = 1.1;
j1_pad = 2.0;

// Female header (stand-in for the Molex part), mounted under the board
hdr_body = [2.54, 5.08, 8.5];

// Cable: AM2464, 2 x 20 AWG, 3.4 mm OD
cable_d = 3.4;

// Part bodies under the board
res_body = [6.3, 2.4];         // length, diameter
q1_body = [4.8, 3.7, 4.5];     // width (across legs), depth, height
q1_standoff = 1.0;

// Traces, all on the top copper: [width, [points]]
traces = [
  // +5V: outer lane on the -y side, then up to J1 pin 1
  [trace_w, [[side_x(0), -9.3], [side_x(0), -lane_out], [j1_x, -lane_out], [j1_x, j1_y[0]]]],
  // GND: inner lane on the -y side -> R2 -> Q1 emitter
  [trace_w, [[side_x(1), -9.3], [side_x(1), -lane_in], [r2_holes[1][0], -lane_in],
             r2_holes[1], [q1_x, r2_holes[1][1]], q1_e]],
  // GP2: lane on the +y side -> R1
  [trace_w, [[side_x(2), 9.3], [side_x(2), lane_in], [r1_holes[0][0], lane_in], r1_holes[0]]],
  // R1 -> base, R2 -> base
  [trace_w, [r1_holes[1], q1_b]],
  [trace_w, [r2_holes[0], q1_b]],
  // collector -> J1 pin 2 (LASER-)
  [trace_w, [q1_c, [j1_x, j1_y[1]]]],
];

// ===================== Case =====================
wall = 1.5;
floor_t = 1.2;
lid_t = 1.2;
clr = 0.3;                     // carrier-to-wall clearance
under_gap = 6.0;               // below carrier: standing TO-92 is ~5.5
corner_r = 1.5;
bend_gap = 3.0;                // cable variant: room for wires to turn up into J1
clamp_l = 8.0;                 // cable variant: strain-relief block length
chan_d = 3.5;                  // cable channel bore
ridge_d = 2.7;                 // bore at the ridges (bite into the jacket)
ridge_x = [1.8, 4.0, 6.2];     // ridge positions within the clamp block
screw_y = 5.2;                 // clamp screws at +/- this
screw_clear = 2.4;             // M2 clearance in the bottom half
screw_head = 4.2;              // counterbore for M2 pan head
screw_head_depth = 2.0;
screw_pilot = 1.7;             // M2 self-tapping into the lid
screw_pilot_depth = 7.0;

z_floor = -under_gap;
// Molex version: thicker floor so the bottom is flat and the header stands
// 0.3 proud of it (a raised box under the floor would not print).
z_bot = variant == "molex" ? -hdr_body[2] + 0.3 : z_floor - floor_t;
z_split = -2.5;                // through the cable center, below the carrier
ceil_z = mod_z + mod_t + max(usb_top, btn_h) + 0.4;
z_top = ceil_z + lid_t;

usb_zc = mod_z + mod_t + usb_top - usb_h / 2;
hdr_end = -hdr_body[2];        // header hangs below the carrier
turret_bot = hdr_end + 0.3;    // bottom face around the header (Molex version)

in_x0 = -clr;
in_x1 = variant == "cable" ? car_l + clr + bend_gap : car_l + clr;
out_x0 = in_x0 - wall;
out_x1 = variant == "cable" ? in_x1 + clamp_l : in_x1 + wall;
in_w = car_w + 2 * clr;
out_w = in_w + 2 * wall;

rail_in = car_w / 2 - 0.9;     // rails support the carrier's outer 0.9 mm
rail_gap = 0.15;               // rails to lid wall

// ===================== Colors =====================
c_pcb_mod = "#1f56b5";
c_pcb_car = "#1d6b3a";
c_gold = "#d4a838";
c_copper = "#c8743a";
c_silver = "#c0c0c0";
c_black = "#202020";
c_res = "#d9c09a";
c_case = "#e8e4dc";
c_lid = "#9fc3e6";

// ===================== Helpers =====================
module rbox(x0, x1, y0, y1, z0, z1, r) {
  hull() for (x = [x0 + r, x1 - r], y = [y0 + r, y1 - r])
    translate([x, y, z0]) cylinder(r = r, h = z1 - z0);
}

module box(x0, x1, y0, y1, z0, z1) {
  translate([x0, y0, z0]) cube([x1 - x0, y1 - y0, z1 - z0]);
}

module xslot(w, h, x0, x1, zc) {     // stadium-shaped hole along x
  r = h / 2;
  hull() for (y = [-(w / 2 - r), w / 2 - r])
    translate([x0, y, zc]) rotate([0, 90, 0]) cylinder(r = r, h = x1 - x0);
}

module path(pts, w, h) {
  for (i = [0 : len(pts) - 2])
    hull() for (p = [pts[i], pts[i + 1]])
      translate(p) cylinder(d = w, h = h, $fn = 16);
}

module chain3(pts, d) {
  for (i = [0 : len(pts) - 2]) hull() for (p = [pts[i], pts[i + 1]]) translate(p) sphere(d = d, $fn = 12);
}

// ===================== RP2040-Zero mock =====================
module rp2040_zero() {
  // board with castellated half-holes
  color(c_pcb_mod) difference() {
    cube([mod_l, mod_w, mod_t]);
    for (k = [0 : side_pins - 1], y = [0, mod_w])
      translate([side_x(k), y, -eps]) cylinder(d = castle_d, h = mod_t + 2 * eps);
    for (k = [0 : end_pins - 1])
      translate([mod_l, mod_w / 2 + end_y(k), -eps]) cylinder(d = castle_d, h = mod_t + 2 * eps);
  }
  // castellation pads, top and bottom
  color(c_gold) for (z = [-0.03, mod_t]) difference() {
    union() {
      for (k = [0 : side_pins - 1], y = [0, mod_w - 1.2])
        translate([side_x(k) - 0.7, y, z]) cube([1.4, 1.2, 0.03]);
      for (k = [0 : end_pins - 1])
        translate([mod_l - 1.2, mod_w / 2 + end_y(k) - 0.7, z]) cube([1.2, 1.4, 0.03]);
    }
    for (k = [0 : side_pins - 1], y = [0, mod_w])
      translate([side_x(k), y, -1]) cylinder(d = castle_d, h = 3);
    for (k = [0 : end_pins - 1])
      translate([mod_l, mod_w / 2 + end_y(k), -1]) cylinder(d = castle_d, h = 3);
  }
  // USB-C receptacle, mounted at the front edge
  color(c_silver) translate([0, mod_w / 2, 0])
    xslot(usb_w, usb_h, -usb_protrude, -usb_protrude + usb_len, mod_t + usb_top - usb_h / 2);
  // buttons
  for (p = [boot_pos, reset_pos]) translate([p[0], p[1] + mod_w / 2, mod_t]) {
    color(c_silver) translate([-btn_size[0] / 2, -btn_size[1] / 2, 0]) cube([btn_size[0], btn_size[1], btn_h - 0.5]);
    color("white") translate([-1.2, -0.9, btn_h - 0.5]) cube([2.4, 1.8, 0.5]);
  }
  // RGB LED
  color("white") translate([led_pos[0] - led_size[0] / 2, led_pos[1] + mod_w / 2 - led_size[1] / 2, mod_t]) cube(led_size);
  // flash chip
  color(c_black) translate([flash_pos[0] - flash_size[0] / 2, flash_pos[1] + mod_w / 2 - flash_size[1] / 2, mod_t]) cube(flash_size);
  // underside: RP2040, crystal, regulator, GP17..25 pads
  for (b = bot_parts) color(b[4] < 0.8 ? c_silver : c_black)
    translate([b[0] - b[2] / 2, b[1] + mod_w / 2 - b[3] / 2, -b[4]]) cube([b[2], b[3], b[4]]);
  color(c_gold) for (k = [0 : 8]) translate([4 + k * 2.0, 1.6, -0.03]) cube([0.9, 1.5, 0.03]);
}

// Module placed on the carrier
module module_placed() {
  translate([0, -mod_w / 2, mod_z]) rp2040_zero();
}

// ===================== Carrier =====================
all_holes = concat(r1_holes, r2_holes, [q1_e, q1_b, q1_c]);

module carrier_outline_2d() {
  difference() {
    translate([0, -car_w / 2]) square([car_l, car_w]);
    // cutout for the module's underside parts, open at the USB end
    translate([-1, -(mod_w / 2 - pad_band)]) square([mod_l - pad_band + 1, mod_w - 2 * pad_band]);
    for (h = all_holes) translate(h) circle(d = tht_drill);
    for (y = j1_y) translate([j1_x, y]) circle(d = j1_drill);
  }
}

module castle_pads_2d() {
  for (k = [0 : side_pins - 1], s = [-1, 1])
    translate([side_x(k) - pad_w / 2, s > 0 ? mod_w / 2 - pad_in : -mod_w / 2 - pad_out])
      square([pad_w, pad_in + pad_out]);
  for (k = [0 : end_pins - 1])
    translate([mod_l - pad_in, end_y(k) - pad_w / 2]) square([pad_in + pad_out, pad_w]);
}

module tht_pads_2d() {
  for (h = concat(r1_holes, r2_holes)) translate(h) difference() { circle(d = tht_pad); circle(d = tht_drill); }
  for (h = [q1_e, q1_b, q1_c]) translate(h) difference() { circle(d = q1_pad); circle(d = tht_drill); }
  for (y = j1_y) translate([j1_x, y]) difference() { circle(d = j1_pad); circle(d = j1_drill); }
}

module copper_2d() {
  castle_pads_2d();
  tht_pads_2d();
  for (t = traces) for (i = [0 : len(t[1]) - 2])
    hull() for (p = [t[1][i], t[1][i + 1]]) translate(p) circle(d = t[0], $fn = 16);
}

// a lead from a hole, down to the body, plus the clipped end above the copper
module lead(h, z_body) {
  color(c_silver) translate([h[0], h[1], z_body]) cylinder(d = 0.6, h = pcb_t - z_body + 0.8, $fn = 12);
}

module resistor(holes, band) {
  zc = -res_body[1] / 2 - 0.3;
  mid = (holes[0] + holes[1]) / 2;
  for (h = holes) lead(h, zc);
  color(c_silver) hull() for (h = holes) translate([h[0], h[1], zc]) sphere(d = 0.6, $fn = 12);
  translate([mid[0], mid[1], zc]) rotate([90, 0, 0]) {
    color(c_res) cylinder(d = res_body[1], h = res_body[0], center = true);
    color(band) translate([0, 0, res_body[0] / 2 - 1.2]) cylinder(d = res_body[1] + 0.05, h = 0.5);
  }
}

module to92() {
  z1 = -q1_standoff;
  z0 = z1 - q1_body[2];
  for (h = [q1_e, q1_b, q1_c]) lead(h, z1 - 0.2);
  // D-shaped body, flat face toward +x
  color(c_black) translate([q1_x, 0, z0]) intersection() {
    cylinder(d = q1_body[0], h = q1_body[2]);
    translate([-q1_body[0], -q1_body[0], 0]) cube([q1_body[0] + q1_body[1] - q1_body[0] / 2, 2 * q1_body[0], q1_body[2]]);
  }
}

module carrier() {
  color(c_pcb_car) linear_extrude(pcb_t) carrier_outline_2d();
  color(c_copper) translate([0, 0, pcb_t]) linear_extrude(0.04) copper_2d();
  color(c_gold) translate([0, 0, pcb_t + 0.01]) linear_extrude(0.04) union() { castle_pads_2d(); tht_pads_2d(); }
}

module carrier_parts() {
  resistor(r1_holes, "brown");
  resistor(r2_holes, "orange");
  to92();
}

module carrier_drawing() {
  // flat view of the copper side, with labels; render with an orthographic top camera
  color("#2e7d4f") linear_extrude(0.1) carrier_outline_2d();
  color("#e08a3c") translate([0, 0, 0.1]) linear_extrude(0.05) copper_2d();
  color(c_gold) translate([0, 0, 0.15]) linear_extrude(0.05) union() { castle_pads_2d(); tht_pads_2d(); }
  // outlines of the parts underneath
  color("#dddddd") translate([0, 0, 0.3]) linear_extrude(0.02) {
    for (r = [r1_holes, r2_holes]) translate((r[0] + r[1]) / 2) outline_2d([res_body[1], res_body[0]]);
    translate([q1_x - q1_body[0] / 2 + q1_body[1] / 2, 0]) outline_2d([q1_body[1], q1_body[0]]);
  }
  // module outline
  color("#1f56b5") translate([0, 0, 0.4]) linear_extrude(0.02) difference() {
    translate([0, -mod_w / 2]) square([mod_l, mod_w]);
    translate([0.15, -mod_w / 2 + 0.15]) square([mod_l - 0.3, mod_w - 0.3]);
  }
  // labels
  color("black") translate([0, 0, 0.5]) linear_extrude(0.02) {
    for (k = [0 : side_pins - 1]) {
      translate([side_x(k), -car_w / 2 - 0.4]) rotate(90) text(side_names_neg[k], size = 0.75, halign = "right", valign = "center");
      translate([side_x(k),  car_w / 2 + 0.4]) rotate(90) text(side_names_pos[k], size = 0.75, halign = "left", valign = "center");
    }
    for (k = [0 : end_pins - 1])
      translate([mod_l - 1.1, end_y(k)]) text(end_names[k], size = 0.6, halign = "right", valign = "center");
    translate([mod_l / 2 - 1, 0]) text("cutout", size = 1.2, halign = "center", valign = "center");
    translate([mod_l / 2 - 1, -2]) text("(module underside parts)", size = 0.7, halign = "center", valign = "center");
    translate([-0.5, 0]) rotate(90) text("USB end", size = 1.0, halign = "center", valign = "bottom");
    translate([j1_x + 1.4, j1_y[0]]) text("+5V", size = 0.7, valign = "center");
    translate([j1_x + 1.4, j1_y[1]]) text("LASER-", size = 0.7, valign = "center");
    translate([j1_x, 3.0]) text("J1", size = 0.8, halign = "center");
    translate([q1_x + 1.3, q1_e[1]]) text("E", size = 0.6, valign = "center");
    translate([q1_x + 1.3, q1_b[1]]) text("B", size = 0.6, valign = "center");
    translate([q1_x + 1.3, q1_c[1]]) text("C", size = 0.6, valign = "center");
    translate([q1_x, -4.6]) text("Q1", size = 0.8, halign = "center");
    translate([r1_holes[0][0] - 1.4, 1.4]) rotate(90) text("R1 1k", size = 0.6, halign = "center");
    translate([r2_holes[0][0] + 1.4, -1.4]) rotate(90) text("R2 10k", size = 0.6, halign = "center", valign = "top");
  }
  color("black") translate([0, 0, 0.5]) linear_extrude(0.02) {
    translate([0, -car_w / 2 - 5.5]) text("Copper side (one layer). Gray outlines: parts mounted on the other side.", size = 0.8);
    translate([0, -car_w / 2 - 7.0]) text(str("carrier ", car_l, " x ", car_w, " mm, 1.6 mm FR4; module footprint ", mod_l, " x ", mod_w), size = 0.8);
  }
}

module outline_2d(sz) {
  difference() {
    square(sz, center = true);
    square(sz - [0.3, 0.3], center = true);
  }
}

// ===================== Case =====================
module case_solid() {
  difference() {
    union() {
      rbox(out_x0, out_x1, -out_w / 2, out_w / 2, z_bot, z_top, corner_r);
    }
    // main cavity
    box(in_x0, in_x1, -in_w / 2, in_w / 2, z_floor, ceil_z);
    // USB opening and a shallow recess so the plug's overmold can seat
    xslot(usb_w + 0.5, usb_h + 0.5, out_x0 - 1, in_x0 + eps, usb_zc);
    xslot(12.0, 6.6, out_x0 - 1, out_x0 + 0.5, usb_zc);
    // LED window, button pinholes
    translate([led_pos[0], led_pos[1], ceil_z - 1]) cylinder(d = 2.0, h = 20);
    for (p = [boot_pos, reset_pos]) translate([p[0], p[1], ceil_z - 1]) cylinder(d = 1.5, h = 20);
    if (variant == "molex")
      translate([j1_x, 0, 0]) box(-hdr_body[0] / 2 - 0.25, hdr_body[0] / 2 + 0.25,
                                  -hdr_body[1] / 2 - 0.25, hdr_body[1] / 2 + 0.25, turret_bot - 1, z_floor + 1);
    if (variant == "cable") {
      // cable channel with a flared mouth
      translate([in_x1 - 1, 0, z_split]) rotate([0, 90, 0]) cylinder(d = chan_d, h = clamp_l + 2);
      translate([out_x1 - 1.0, 0, z_split]) rotate([0, 90, 0]) cylinder(d1 = chan_d, d2 = chan_d + 1.2, h = 1.0 + eps);
    }
  }
  // gripping ridges in the channel
  if (variant == "cable")
    for (rx = ridge_x) translate([in_x1 + rx, 0, z_split]) rotate([0, 90, 0])
      difference() {
        cylinder(d = chan_d + 0.2, h = 0.8, center = true);
        cylinder(d = ridge_d, h = 2, center = true);
      }
}

// What belongs to the bottom half: everything below the split, plus the
// strip of front wall under the USB opening up to the receptacle's
// widest point, so the lid can come straight down over the receptacle.
module bottom_region() {
  box(out_x0 - 5, out_x1 + 5, -out_w, out_w, z_bot - 20, z_split);
  box(out_x0 - 5, in_x0 + eps, -(usb_w / 2 + 0.25), usb_w / 2 + 0.25, z_bot - 20, usb_zc);
}

module clamp_screws_bottom() {   // heads in the bottom face
  if (variant == "cable")
    for (s = [-1, 1]) translate([in_x1 + clamp_l / 2, s * screw_y, 0]) {
      translate([0, 0, z_bot - 1]) cylinder(d = screw_clear, h = z_split - z_bot + 2);
      translate([0, 0, z_bot - 1]) cylinder(d = screw_head, h = screw_head_depth + 1);
    }
}

module clamp_screws_lid() {      // pilot holes in the lid
  if (variant == "cable")
    for (s = [-1, 1]) translate([in_x1 + clamp_l / 2, s * screw_y, z_split - 1])
      cylinder(d = screw_pilot, h = screw_pilot_depth + 1);
}

module case_bottom() {
  difference() {
    union() {
      intersection() { case_solid(); bottom_region(); }
      // side rails hold the carrier up; above the split they also locate the lid
      for (s = [-1, 1]) scale([1, s, 1])
        box(in_x0, car_l, rail_in, in_w / 2 - rail_gap, z_floor - eps, 0);
      // back corner supports (middle left open for the cable's wires)
      for (s = [-1, 1]) scale([1, s, 1])
        box(car_l - 1.2, car_l + clr - rail_gap, 6.0, in_w / 2 - rail_gap, z_floor - eps, 0);
      // fill the gap between the rails and the walls below the split
      for (s = [-1, 1]) scale([1, s, 1])
        box(in_x0, car_l, rail_in, in_w / 2 + eps, z_floor - eps, z_split);
    }
    clamp_screws_bottom();
  }
}

module case_lid() {
  difference() {
    union() {
      difference() { case_solid(); bottom_region(); }
      // posts that press the carrier's back corners down onto the supports
      for (s = [-1, 1])
        translate([car_l - 1.0, s * (car_w / 2 - 1.6), 0])
          box(-0.8, 0.8, -0.8, 0.8, pcb_t + 0.05, ceil_z + eps);
    }
    clamp_screws_lid();
  }
}

// ===================== Stand-ins for the connector and cable =====================
module header_mock() {
  translate([j1_x, 0, 0]) {
    color(c_black) difference() {
      translate([-hdr_body[0] / 2, -hdr_body[1] / 2, -hdr_body[2]]) cube(hdr_body);
      for (y = j1_y) translate([-0.5, y - 0.5, -hdr_body[2] - 1]) cube([1, 1, 4]);
    }
  }
  for (y = j1_y) color(c_gold) translate([j1_x - 0.32, y - 0.32, -3]) cube([0.64, 0.64, pcb_t + 3.8]);
}

module cable_mock() {
  jacket_x0 = in_x1 - 0.8;
  color("#3a3a3a") translate([jacket_x0, 0, z_split]) rotate([0, 90, 0]) cylinder(d = cable_d, h = out_x1 - jacket_x0 + 15);
  for (i = [0, 1]) color(i == 0 ? "red" : "#111111")
    chain3([[jacket_x0 + 0.2, j1_y[i] * 0.5, z_split],
            [j1_x + 2.0, j1_y[i], z_split],
            [j1_x, j1_y[i], -1.2],
            [j1_x, j1_y[i], pcb_t + 0.6]], 1.0);
}

module contents() {
  carrier();
  carrier_parts();
  module_placed();
  if (variant == "molex") header_mock(); else cable_mock();
}

// ===================== Printable fit-test mockups =====================
// Carrier mockup: the carrier plate with blocks standing in for the parts
// underneath. J1 holes are opened up so real 20 AWG wires go through.
mock_j1_drill = 1.8;

module carrier_mock() {
  linear_extrude(pcb_t) difference() {
    translate([0, -car_w / 2]) square([car_l, car_w]);
    translate([-1, -(mod_w / 2 - pad_band)]) square([mod_l - pad_band + 1, mod_w - 2 * pad_band]);
    for (y = j1_y) translate([j1_x, y]) circle(d = mock_j1_drill);
  }
  zc = -res_body[1] / 2 - 0.3;
  for (r = [r1_holes, r2_holes]) {
    mid = (r[0] + r[1]) / 2;
    translate([mid[0], mid[1], zc]) rotate([90, 0, 0]) cylinder(d = res_body[1], h = res_body[0], center = true);
    translate([mid[0] - 0.6, mid[1] - res_body[0] / 2, zc]) cube([1.2, res_body[0], -zc + eps]);
  }
  // TO-92, solid down to the board (stands in for body + legs)
  translate([q1_x, 0, -q1_standoff - q1_body[2]]) intersection() {
    cylinder(d = q1_body[0], h = q1_body[2] + q1_standoff + eps);
    translate([-q1_body[0], -q1_body[0], 0])
      cube([q1_body[0] + q1_body[1] - q1_body[0] / 2, 2 * q1_body[0], q1_body[2] + q1_standoff + eps]);
  }
  if (variant == "molex")
    translate([j1_x - hdr_body[0] / 2, -hdr_body[1] / 2, -hdr_body[2]]) cube([hdr_body[0], hdr_body[1], hdr_body[2] + eps]);
}

// Module mockup: board, USB-C, buttons, LED and flash chip as one solid.
module module_mock() {
  difference() {
    cube([mod_l, mod_w, mod_t]);
    for (k = [0 : side_pins - 1], y = [0, mod_w])
      translate([side_x(k), y, -eps]) cylinder(d = castle_d, h = mod_t + 2 * eps, $fn = 16);
    for (k = [0 : end_pins - 1])
      translate([mod_l, mod_w / 2 + end_y(k), -eps]) cylinder(d = castle_d, h = mod_t + 2 * eps, $fn = 16);
  }
  translate([0, mod_w / 2, 0]) intersection() {
    xslot(usb_w, usb_h, -usb_protrude, -usb_protrude + usb_len, mod_t + usb_top - usb_h / 2);
    translate([-5, -10, 0]) cube([20, 20, 10]);    // keep it above the board's underside
  }
  for (p = [boot_pos, reset_pos]) translate([p[0] - btn_size[0] / 2, p[1] + mod_w / 2 - btn_size[1] / 2, mod_t - eps])
    cube([btn_size[0], btn_size[1], btn_h + eps]);
  translate([led_pos[0] - led_size[0] / 2, led_pos[1] + mod_w / 2 - led_size[1] / 2, mod_t - eps]) cube(led_size + [0, 0, eps]);
  translate([flash_pos[0] - flash_size[0] / 2, flash_pos[1] + mod_w / 2 - flash_size[1] / 2, mod_t - eps]) cube(flash_size + [0, 0, eps]);
}

// ===================== Part selection =====================
if (part == "module") rp2040_zero();
else if (part == "carrier") carrier();
else if (part == "carrier_drawing") carrier_drawing();
else if (part == "carrier_assembly") contents();
else if (part == "bottom") color(c_case) case_bottom();
else if (part == "lid") color(c_lid) case_lid();
else if (part == "bottom_print") translate([0, 0, -z_bot]) case_bottom();
else if (part == "lid_print") translate([0, 0, z_top]) rotate([180, 0, 0]) case_lid();
else if (part == "carrier_mock_print") translate([0, 0, pcb_t]) rotate([180, 0, 0]) carrier_mock();
else if (part == "module_mock_print") module_mock();
else if (part == "mock_assembly") {
  color("#7fbf7f") carrier_mock();
  color("#7f9fdf") translate([0, -mod_w / 2, mod_z]) module_mock();
}
else if (part == "assembly") {
  contents();
  color(c_case) case_bottom();
  color(c_lid, 0.45) case_lid();
}
else if (part == "exploded") {
  contents();
  color(c_case) translate([0, 0, -16]) case_bottom();
  color(c_lid) translate([0, 0, 26]) case_lid();
}
else if (part == "section") difference() {
  union() {
    contents();
    color(c_case) case_bottom();
    color(c_lid) case_lid();
  }
  box(-20, 80, -40, 0.0, -20, 40);  // remove -y half: cut through USB and cable centers
}
