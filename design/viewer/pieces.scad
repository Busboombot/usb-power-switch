// Exports one component of the assembled model, in assembly coordinates,
// for the 3D viewer. Run by build.sh:
//   openscad -D 'part="none"' -D 'variant="cable"' -D 'piece="lid"' -o lid.stl pieces.scad
include <../cad/usb_power_switch.scad>
piece = "";

module on_module() { translate([0, -mod_w / 2, mod_z]) children(); }
module mod_holes() {
  for (k = [0 : side_pins - 1], y = [0, mod_w])
    translate([side_x(k), y, -1]) cylinder(d = castle_d, h = 3);
  for (k = [0 : end_pins - 1])
    translate([mod_l, mod_w / 2 + end_y(k), -1]) cylinder(d = castle_d, h = 3);
}
zc_res = -res_body[1] / 2 - 0.3;
module res_body_at(holes) {
  mid = (holes[0] + holes[1]) / 2;
  translate([mid[0], mid[1], zc_res]) rotate([90, 0, 0]) cylinder(d = res_body[1], h = res_body[0], center = true);
}
module res_leads(holes) {
  for (h = holes) translate([h[0], h[1], zc_res]) cylinder(d = 0.6, h = pcb_t - zc_res + 0.8, $fn = 12);
  hull() for (h = holes) translate([h[0], h[1], zc_res]) sphere(d = 0.6, $fn = 12);
}
module screw() {   // M2 x 8 pan head, head seated in the counterbore
  translate([0, 0, z_bot + 0.4]) cylinder(d = 3.8, h = 1.6);
  translate([0, 0, z_bot + 2]) cylinder(d = 2.0, h = 8);
}
jacket_x0 = in_x1 - 0.8;
module wire(i) {
  chain3([[jacket_x0 + 0.2, j1_y[i] * 0.5, z_split], [j1_x + 2.0, j1_y[i], z_split],
          [j1_x, j1_y[i], -1.2], [j1_x, j1_y[i], pcb_t + 0.6]], 1.0);
}

if (piece == "bottom") case_bottom();
else if (piece == "lid") case_lid();
else if (piece == "screws" && variant == "cable") for (s = [-1, 1]) translate([in_x1 + clamp_l / 2, s * screw_y, 0]) screw();
else if (piece == "carrier_fr4") linear_extrude(pcb_t) carrier_outline_2d();
else if (piece == "carrier_copper") translate([0, 0, pcb_t]) linear_extrude(0.04) copper_2d();
else if (piece == "carrier_pads") translate([0, 0, pcb_t + 0.01]) linear_extrude(0.05) union() { castle_pads_2d(); tht_pads_2d(); }
else if (piece == "mod_pcb") on_module() difference() { cube([mod_l, mod_w, mod_t]); mod_holes(); }
else if (piece == "mod_pads") on_module() difference() {
  union() for (z = [-0.03, mod_t]) {
    for (k = [0 : side_pins - 1], y = [0, mod_w - 1.2]) translate([side_x(k) - 0.7, y, z]) cube([1.4, 1.2, 0.03]);
    for (k = [0 : end_pins - 1]) translate([mod_l - 1.2, mod_w / 2 + end_y(k) - 0.7, z]) cube([1.2, 1.4, 0.03]);
  }
  mod_holes();
}
else if (piece == "usb") on_module() translate([0, mod_w / 2, 0])
  xslot(usb_w, usb_h, -usb_protrude, -usb_protrude + usb_len, mod_t + usb_top - usb_h / 2);
else if (piece == "btn_body") on_module() for (p = [boot_pos, reset_pos]) translate([p[0], p[1] + mod_w / 2, mod_t])
  translate([-btn_size[0] / 2, -btn_size[1] / 2, 0]) cube([btn_size[0], btn_size[1], btn_h - 0.5]);
else if (piece == "btn_cap") on_module() for (p = [boot_pos, reset_pos]) translate([p[0], p[1] + mod_w / 2, mod_t])
  translate([-1.2, -0.9, btn_h - 0.5]) cube([2.4, 1.8, 0.5]);
else if (piece == "led") on_module() translate([led_pos[0] - led_size[0] / 2, led_pos[1] + mod_w / 2 - led_size[1] / 2, mod_t]) cube(led_size);
else if (piece == "flash") on_module() translate([flash_pos[0] - flash_size[0] / 2, flash_pos[1] + mod_w / 2 - flash_size[1] / 2, mod_t]) cube(flash_size);
else if (piece == "mod_under") on_module() for (b = bot_parts)
  translate([b[0] - b[2] / 2, b[1] + mod_w / 2 - b[3] / 2, -b[4]]) cube([b[2], b[3], b[4]]);
else if (piece == "r1_body") res_body_at(r1_holes);
else if (piece == "r1_leads") res_leads(r1_holes);
else if (piece == "r2_body") res_body_at(r2_holes);
else if (piece == "r2_leads") res_leads(r2_holes);
else if (piece == "q1_body") translate([q1_x, 0, -q1_standoff - q1_body[2]]) intersection() {
  cylinder(d = q1_body[0], h = q1_body[2]);
  translate([-q1_body[0], -q1_body[0], 0]) cube([q1_body[0] + q1_body[1] - q1_body[0] / 2, 2 * q1_body[0], q1_body[2]]);
}
else if (piece == "q1_leads") for (h = [q1_e, q1_b, q1_c]) translate([h[0], h[1], -q1_standoff - 0.2]) cylinder(d = 0.6, h = pcb_t + q1_standoff + 1.0, $fn = 12);
else if (piece == "hdr_body" && variant == "molex") translate([j1_x, 0, 0]) difference() {
  translate([-hdr_body[0] / 2, -hdr_body[1] / 2, -hdr_body[2]]) cube(hdr_body);
  for (y = j1_y) translate([-0.5, y - 0.5, -hdr_body[2] - 1]) cube([1, 1, 4]);
}
else if (piece == "hdr_pins" && variant == "molex") for (y = j1_y) translate([j1_x - 0.32, y - 0.32, -3]) cube([0.64, 0.64, pcb_t + 3.8]);
else if (piece == "jacket" && variant == "cable") translate([jacket_x0, 0, z_split]) rotate([0, 90, 0]) cylinder(d = cable_d, h = out_x1 - jacket_x0 + 15);
else if (piece == "wire_red" && variant == "cable") wire(0);
else if (piece == "wire_black" && variant == "cable") wire(1);
