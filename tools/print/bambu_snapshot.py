"""Grab one JPEG frame from a Bambu A1/P1 camera (TLS port 6000). Read-only.

Usage: python bambu_snapshot.py <ip> <ENVVAR with access code> <out.jpg>
"""
import os, socket, ssl, struct, sys

ip, env, out = sys.argv[1], sys.argv[2], sys.argv[3]
code = os.environ[env]
auth = struct.pack('<IIII', 0x40, 0x3000, 0, 0) + b'bblp'.ljust(32, b'\0') + code.encode().ljust(32, b'\0')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
s = ctx.wrap_socket(socket.create_connection((ip, 6000), timeout=15), server_hostname=ip)
s.sendall(auth)

def recv_exact(n):
    buf = b''
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise EOFError('connection closed')
        buf += chunk
    return buf

for attempt in range(3):           # first frame is sometimes stale; keep the third
    hdr = recv_exact(16)
    size = struct.unpack('<I', hdr[:4])[0]
    img = recv_exact(size)
s.close()
if not img.startswith(b'\xff\xd8'):
    sys.exit('not a JPEG')
open(out, 'wb').write(img)
print(out, len(img), 'bytes')
