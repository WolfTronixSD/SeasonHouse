# Scream-o-Meter: guests scream into a microphone, a WLED bar shoots up the
# wall, the dot matrix shows the score and the web page keeps a leaderboard.
# A loud enough scream also sets off the other props.
from machine import Pin
from compat import asyncio, sleep_ms
import config
import settings
import net
import mic
from web import Server
from dfplayer import DFPlayer
from strip import Strip
from max7219 import Matrix
from meter import Meter, SND_TRIGGER
from propkit import system_routes, trigger_all, free


class App:
    def __init__(self):
        self.cfg = settings.load()
        self.mp3 = DFPlayer(self.cfg["vol"])
        self.strip = Strip(config.STRIP_LEDS, config.LED_MODE, self.cfg["wled"], config.PIN_STRIP)
        self.dm = Matrix(config.PIN_DM_DIN, config.PIN_DM_CLK, config.PIN_DM_CS, config.DM_MODULES,
                         flip_x=config.DM_FLIP_X, flip_y=config.DM_FLIP_Y)
        self.mic = mic.Mic(config.PIN_MIC_SCK, config.PIN_MIC_WS, config.PIN_MIC_SD, self.cfg["cal"])
        self.button = Pin(config.PIN_BUTTON, Pin.IN, Pin.PULL_UP)
        self.meter = Meter(self.strip, self.dm, self.mp3, self.cfg["board"])
        self.meter.trigger_on = self.cfg["trigger"]
        self.meter.trigger_db = self.cfg["trigger_db"]
        self.meter.on_trigger = self.scare_others
        self.ip = ""

    def scare_others(self, db):
        print("Scream of %d dB! Setting off the other props" % db)
        trigger_all(config.TRIGGER_URLS)
        if self.meter.phase == "idle":
            self.mp3.play(1, SND_TRIGGER)

    def save(self):
        settings.save(self.cfg)
        self.meter.changed = False

    def status(self):
        m = self.meter
        return {"prop": "scream", "phase": m.phase, "count": m.count() if m.phase == "countdown" else 0,
                "db": round(m.db, 1), "peak": round(m.peak, 1), "score": m.score, "who": m.who, "record": m.record,
                "board": m.board, "vu": [m.lo, m.hi], "trigger": m.trigger_on, "trigger_db": m.trigger_db,
                "urls": config.TRIGGER_URLS, "vol": self.cfg["vol"], "cal": self.cfg["cal"],
                "wled": self.cfg["wled"], "ip": self.ip, "free": free()}

    def routes(self, srv):
        ok = lambda: (200, self.status())

        @srv.route("/")
        def index(req):
            return "file", "www/index.html", "text/html"

        @srv.route("/api/status")
        def status(req):
            return ok()

        @srv.route("/api/round")
        def round_(req):
            started = self.meter.start(req.arg("name"))
            return (200 if started else 409), self.status()

        @srv.route("/api/stop")
        def stop(req):
            self.meter.stop()
            return ok()

        @srv.route("/api/clear")
        def clear(req):
            self.meter.clear()
            self.save()
            return ok()

        @srv.route("/api/trigger")
        def trigger(req):
            if req.arg("on"):
                self.cfg["trigger"] = self.meter.trigger_on = req.arg("on") == "1"
            if req.arg("db"):
                self.cfg["trigger_db"] = self.meter.trigger_db = max(60, min(130, int(req.arg("db"))))
            self.save()
            return ok()

        @srv.route("/api/cal")
        def cal(req):
            self.cfg["cal"] = self.mic.offset = int(req.arg("db", str(config.MIC_OFFSET_DB)))
            self.save()
            return ok()

        @srv.route("/api/vol")
        def vol(req):
            self.cfg["vol"] = max(0, min(30, int(req.arg("v", "20"))))
            self.mp3.volume(self.cfg["vol"])
            self.save()
            return ok()

        @srv.route("/api/wled")
        def wled_route(req):
            if req.arg("host"):
                self.cfg["wled"] = req.arg("host")
                self.strip.set_host(self.cfg["wled"])
                self.save()
            return ok()

        system_routes(srv, self.meter.stop)

    async def listen(self):
        while True:
            try:
                self.meter.feed(await self.mic.read_db())
            except Exception as e:
                print("Mic error:", e)
                await sleep_ms(500)

    async def loop(self):
        pressed = False
        while True:
            self.meter.update()
            down = self.button.value() == 0
            if down and not pressed:
                self.meter.start()
            pressed = down
            if self.meter.changed:
                self.save()
            await sleep_ms(40)

    async def run(self):
        self.ip, _ = net.connect()
        srv = Server()
        self.routes(srv)
        await srv.start(80)
        print("Scream-o-Meter ready")
        asyncio.create_task(self.listen())
        await self.loop()


def main():
    asyncio.run(App().run())
