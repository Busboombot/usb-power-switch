"""Upload a sliced .gcode.3mf to a Bambu A1/P1 over FTPS and start it over MQTT.

Usage: python bambu_send.py <ip> <serial> <ENVVAR with access code> <file.gcode.3mf> <task name>
Uses the external spool (no AMS). Watches status for ~40 s and reports it.
"""
import ftplib, json, os, ssl, sys, time
import paho.mqtt.client as mqtt

ip, serial, env, path, task = sys.argv[1:6]
code = os.environ[env]
name = os.path.basename(path)


class ImplicitFTPS(ftplib.FTP_TLS):
    """FTPS with TLS from the first byte (port 990), reusing the session on data connections."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._sock = None

    @property
    def sock(self):
        return self._sock

    @sock.setter
    def sock(self, value):
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value, server_hostname=self.host)
        self._sock = value

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session)
        return conn, size

    def storbinary(self, cmd, fp, blocksize=32768):
        # like ftplib's, but without conn.unwrap(), which hangs on Bambu printers
        self.voidcmd('TYPE I')
        with self.transfercmd(cmd) as conn:
            while True:
                buf = fp.read(blocksize)
                if not buf:
                    break
                conn.sendall(buf)
        return self.voidresp()


ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ftp = ImplicitFTPS(context=ctx, timeout=60)
ftp.connect(ip, 990)
ftp.login('bblp', code)
ftp.prot_p()
with open(path, 'rb') as f:
    ftp.storbinary(f'STOR {name}', f)
remote_size = ftp.size(name)
ftp.quit()
local_size = os.path.getsize(path)
print(f'uploaded {name}: {remote_size} bytes (local {local_size})')
if remote_size != local_size:
    sys.exit('size mismatch, not starting')

state = {}
def on_connect(c, u, f, rc, p=None):
    c.subscribe(f'device/{serial}/report')
    c.publish(f'device/{serial}/request', json.dumps({'print': {
        'sequence_id': '0', 'command': 'project_file', 'param': 'Metadata/plate_1.gcode',
        'project_id': '0', 'profile_id': '0', 'task_id': '0', 'subtask_id': '0',
        'subtask_name': task, 'file': name, 'url': f'file:///sdcard/{name}', 'md5': '',
        'timelapse': False, 'bed_type': 'auto', 'bed_levelling': True, 'bed_leveling': True,
        'flow_cali': False, 'vibration_cali': False, 'layer_inspect': False,
        'use_ams': False, 'ams_mapping': []}}))
    c.publish(f'device/{serial}/request', json.dumps({'pushing': {'sequence_id': '1', 'command': 'pushall'}}))
def on_message(c, u, m):
    d = json.loads(m.payload).get('print', {})
    for k in ('gcode_state', 'subtask_name', 'print_error', 'mc_percent', 'stg_cur', 'result', 'reason'):
        if k in d:
            state[k] = d[k]

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.username_pw_set('bblp', code)
c.tls_set(cert_reqs=ssl.CERT_NONE)
c.tls_insecure_set(True)
c.on_connect = on_connect
c.on_message = on_message
c.connect(ip, 8883, 30)
c.loop_start()
for i in range(8):
    time.sleep(5)
    c.publish(f'device/{serial}/request', json.dumps({'pushing': {'sequence_id': str(i + 2), 'command': 'pushall'}}))
c.loop_stop()
c.disconnect()
print('status:', json.dumps(state))
