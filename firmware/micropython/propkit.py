# Bits every prop shares: the wireless-update routes, a cooldown timer and a
# fire-and-forget HTTP call used to set off other props.
import gc
import machine
from compat import asyncio, sleep_ms, ticks_ms, ticks_diff
import ota


def system_routes(srv, before_update=None):
    """/api/ota, /api/files and /api/reboot, the same on every prop."""

    @srv.route("/api/ota")
    async def ota_upload(req):
        if req.method != "POST":
            return 400, {"ok": False, "error": "POST the file as the request body"}
        if before_update:
            before_update()
        res = await ota.receive(req, req.reader.read)
        gc.collect()
        return res

    @srv.route("/api/files")
    def files(req):
        return 200, ota.listing()

    @srv.route("/api/reboot")
    def reboot(req):
        if not ota.check_key(req.arg("key")):
            return 403, {"ok": False, "error": "wrong update key"}
        asyncio.create_task(_reboot())
        return 200, {"ok": True, "rebooting": True}


async def _reboot():
    await sleep_ms(500)
    machine.reset()


def free():
    return getattr(gc, "mem_free", lambda: 0)()


class Cooldown:
    def __init__(self, ms, clock=ticks_ms):
        self.ms = ms
        self.clock = clock
        self.last = clock()        # gives a PIR its warm-up time after boot

    def ready(self):
        return ticks_diff(self.clock(), self.last) > self.ms

    def fire(self):
        self.last = self.clock()


async def http_get(url):
    """GET http://host[:port]/path?query and ignore the answer."""
    try:
        rest = url.split("://", 1)[-1]
        hostport, _, path = rest.partition("/")
        host, _, port = hostport.partition(":")
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, int(port or 80)), 3)
        writer.write(("GET /%s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n" % (path, host)).encode())
        await writer.drain()
        status = await asyncio.wait_for(reader.readline(), 3)
        writer.close()
        await writer.wait_closed()
        print("Triggered", url, status[9:12])
        return True
    except Exception as e:
        print("Could not reach", url, e)
        return False


def trigger_all(urls):
    for u in urls:
        asyncio.create_task(http_get(u))
