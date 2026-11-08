"""Read-only status of Bambu printers over LAN MQTT.

Usage: uv run --with paho-mqtt python bambu_status.py NAME=ip,serial,ENVVAR ...
Access codes are read from the environment variables named; never printed.
Sends only pushall (a status request).
"""
import json, os, ssl, sys, time
import paho.mqtt.client as mqtt

def status(name, ip, serial, code):
    out = {}
    def on_connect(c, u, f, rc, p=None):
        c.subscribe(f"device/{serial}/report")
        c.publish(f"device/{serial}/request", json.dumps({"pushing": {"sequence_id": "1", "command": "pushall"}}))
    def on_message(c, u, m):
        d = json.loads(m.payload).get('print', {})
        if 'gcode_state' in d:
            out.update({k: d.get(k) for k in ('gcode_state', 'mc_percent', 'mc_remaining_time', 'subtask_name',
                                              'nozzle_diameter', 'nozzle_type', 'bed_temper', 'nozzle_temper',
                                              'print_error', 'sdcard')})
            ams = (d.get('ams') or {})
            out['ams'] = [{'unit': a.get('id'),
                           'trays': [{'slot': t.get('id'), 'type': t.get('tray_type'), 'color': t.get('tray_color'),
                                      'name': t.get('tray_sub_brands'), 'remain': t.get('remain')}
                                     for t in a.get('tray', [])]} for a in ams.get('ams', [])]
            out['tray_now'] = ams.get('tray_now')
            vt = d.get('vt_tray') or {}
            out['external_spool'] = {'type': vt.get('tray_type'), 'color': vt.get('tray_color'), 'name': vt.get('tray_sub_brands')}
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.username_pw_set('bblp', code)
    c.tls_set(cert_reqs=ssl.CERT_NONE); c.tls_insecure_set(True)
    c.on_connect = on_connect; c.on_message = on_message
    try:
        c.connect(ip, 8883, 15); c.loop_start(); time.sleep(6); c.loop_stop(); c.disconnect()
    except Exception as e:
        out['error'] = str(e)
    return out

for arg in sys.argv[1:]:
    name, rest = arg.split('=', 1)
    ip, serial, env = rest.split(',')
    print(name, json.dumps(status(name, ip, serial, os.environ[env]), indent=1))
