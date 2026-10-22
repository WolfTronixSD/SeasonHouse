# Lightning Window: a strip behind a sheer curtain flickers like lightning,
# thunder rolls 1-3 s later, and every 10th strike a light outside throws the
# shadow of a cardboard axe man onto the curtain.
from machine import Pin
from compat import asyncio, sleep_ms
import config
import settings
import net
from web import Server
from dfplayer import DFPlayer
from strip import Strip
from storm import Storm
from propkit import system_routes, Cooldown, free


class App:
    def __init__(self):
        self.cfg = settings.load()
        self.mp3 = DFPlayer(self.cfg["vol"])
        self.strip = Strip(config.STRIP_LEDS, config.LED_MODE, self.cfg["wled"], config.PIN_STRIP,
                           idle=config.MOONLIGHT)
        self.sil = Pin(config.PIN_SILHOUETTE, Pin.OUT, value=0)
        self.pir = Pin(config.PIN_PIR, Pin.IN)
        self.storm = Storm(self.strip, self.mp3, self.sil, self.cfg["vol"])
        self.storm.count = self.cfg.get("strikes", 0)
        self.storm.every = self.cfg["every"]
        self.storm.set_auto(self.cfg["auto"], self.cfg["level"])
        self.armed = self.cfg["armed"]
        self.cool = Cooldown(config.MOTION_COOLDOWN_MS)
        self.ip = ""
        self.strip.release()

    def save(self):
        self.cfg["strikes"] = self.storm.count
        settings.save(self.cfg)

    def status(self):
        s = self.storm
        return {"prop": "storm", "strikes": s.count, "every": s.every, "next_sil": s.every - s.count % s.every if s.every else 0,
                "auto": s.auto, "level": s.level, "armed": self.armed, "vol": self.cfg["vol"],
                "busy": s.busy(), "last": s.last, "wled": self.cfg["wled"], "mode": config.LED_MODE,
                "pir": bool(self.pir.value()), "ip": self.ip, "free": free()}

    def routes(self, srv):
        ok = lambda: (200, self.status())

        @srv.route("/")
        def index(req):
            return "file", "www/index.html", "text/html"

        @srv.route("/api/status")
        def status(req):
            return ok()

        @srv.route("/api/strike")
        def strike(req):
            kind = req.arg("kind")
            self.storm.strike(close=kind in ("close", "axe"), silhouette=True if kind == "axe" else None)
            return ok()

        @srv.route("/api/storm")
        def storm(req):
            self.cfg["auto"] = req.arg("on", "1" if self.storm.auto else "0") == "1"
            self.cfg["level"] = int(req.arg("level", str(self.storm.level)))
            self.storm.set_auto(self.cfg["auto"], self.cfg["level"])
            self.save()
            return ok()

        @srv.route("/api/every")
        def every(req):
            self.cfg["every"] = self.storm.every = max(0, int(req.arg("n", "10")))
            self.save()
            return ok()

        @srv.route("/api/stop")
        def stop(req):
            self.storm.set_auto(False)
            self.cfg["auto"] = False
            self.storm.stop()
            self.save()
            return ok()

        @srv.route("/api/arm")
        def arm(req):
            self.armed = self.cfg["armed"] = req.arg("on") == "1"
            self.save()
            return ok()

        @srv.route("/api/vol")
        def vol(req):
            self.cfg["vol"] = self.storm.volume = max(0, min(30, int(req.arg("v", "20"))))
            self.mp3.volume(self.cfg["vol"])
            self.save()
            return ok()

        @srv.route("/api/sound")
        def sound(req):
            self.mp3.volume(self.cfg["vol"])
            self.mp3.play(1, int(req.arg("t", "1")))
            return ok()

        @srv.route("/api/wled")
        def wled_route(req):
            if req.arg("host"):
                self.cfg["wled"] = req.arg("host")
                self.strip.set_host(self.cfg["wled"])
                self.save()
            return ok()

        system_routes(srv, self.storm.stop)

    async def loop(self):
        saved = self.storm.count
        while True:
            self.storm.update()
            if self.armed and self.pir.value() and self.cool.ready() and not self.storm.busy():
                print("Motion! Close strike")
                self.storm.strike(close=True)
                self.cool.fire()
            if self.storm.count - saved >= 5:       # don't wear out the flash
                saved = self.storm.count
                self.save()
            await sleep_ms(8)

    async def run(self):
        self.ip, _ = net.connect()
        srv = Server()
        self.routes(srv)
        await srv.start(80)
        print("Lightning Window ready")
        await self.loop()


def main():
    asyncio.run(App().run())
