# Recovery mode: runs only when the prop code crashed. Self-contained on
# purpose (no other project files needed), so a broken update can always be
# fixed over Wi-Fi: open the prop's address, upload the fixed file, reboot.
import network
import socket
import sys
import time
import os
import machine

try:
    import config
    SSID, PASSWORD, KEY = config.WIFI_SSID, config.WIFI_PASSWORD, config.OTA_KEY
    AP_SSID, AP_PASSWORD = config.AP_SSID, config.AP_PASSWORD
except Exception:
    SSID, PASSWORD, KEY = "", "", "change-me"
    AP_SSID, AP_PASSWORD = "SeasonHouse-Recovery", "boo12345"

PAGE = """<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<title>Prop recovery</title><body style="font:16px system-ui;background:#111;color:#eee;max-width:560px;margin:auto;padding:16px">
<h2 style="color:#f66">Prop code crashed</h2><pre style="white-space:pre-wrap;background:#222;padding:8px">%s</pre>
<p>Upload the fixed file(s), then reboot.</p>
<p><input id=k placeholder="Update key"> <input id=f type=file multiple></p>
<p><button onclick="up()">Upload</button> <button onclick="fetch('/api/reboot?key='+k.value)">Reboot</button></p>
<pre id=o></pre><script>
async function up(){for(const x of f.files){const n=(x.name.endsWith('.html')?'www/':'')+x.name;
const r=await fetch('/api/ota?file='+encodeURIComponent(n)+'&key='+encodeURIComponent(k.value),{method:'POST',body:x});
o.textContent+=n+': '+await r.text()+'\\n'}}</script>"""


def _wifi():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if SSID and not sta.isconnected():
        sta.connect(SSID, PASSWORD)
        t0 = time.time()
        while not sta.isconnected() and time.time() - t0 < 10:
            time.sleep_ms(250)
    if sta.isconnected():
        return sta.ifconfig()[0]
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASSWORD, authmode=3)
    return ap.ifconfig()[0]


def _reply(c, status, body, ctype="text/plain"):
    c.send("HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % (status, ctype, len(body)))
    c.send(body)


def _unq(s):
    out, i = "", 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            out += chr(int(s[i + 1:i + 3], 16))
            i += 3
        else:
            out += s[i]
            i += 1
    return out


def main(err=None):
    msg = "No error given"
    if err is not None:
        msg = "%s: %s" % (type(err).__name__, err)
    ip = _wifi()
    print("RECOVERY MODE at http://%s" % ip)
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 80))
    s.listen(2)
    while True:
        c, _ = s.accept()
        try:
            f = c.makefile("rwb", 0)
            line = f.readline().decode()
            length = 0
            while True:
                h = f.readline()
                if h in (b"\r\n", b""):
                    break
                if h.lower().startswith(b"content-length:"):
                    length = int(h.split(b":")[1])
            target = line.split()[1] if len(line.split()) > 1 else "/"
            path, _, qs = target.partition("?")
            q = {}
            for part in qs.split("&"):
                k, _, v = part.partition("=")
                q[k] = _unq(v)
            if path == "/api/ota":
                name = q.get("file", "")
                if q.get("key") != KEY:
                    _reply(c, "403 Forbidden", "wrong update key")
                elif not name or ".." in name or name.startswith("/") or name == "recovery.py":
                    _reply(c, "400 Bad Request", "file name not allowed")
                else:
                    if name.startswith("www/"):
                        try:
                            os.mkdir("www")
                        except OSError:
                            pass
                    got = 0
                    with open(name + ".new", "wb") as out:
                        while got < length:
                            chunk = f.read(min(1024, length - got))
                            if not chunk:
                                break
                            out.write(chunk)
                            got += len(chunk)
                    if got == length:
                        try:
                            os.remove(name)
                        except OSError:
                            pass
                        os.rename(name + ".new", name)
                        _reply(c, "200 OK", "installed %d bytes" % got)
                    else:
                        os.remove(name + ".new")
                        _reply(c, "400 Bad Request", "upload cut off")
            elif path == "/api/reboot" and q.get("key") == KEY:
                _reply(c, "200 OK", "rebooting")
                c.close()
                time.sleep_ms(300)
                machine.reset()
            else:
                _reply(c, "200 OK", PAGE % msg, "text/html")
        except Exception as e:
            sys.print_exception(e)
        finally:
            c.close()
