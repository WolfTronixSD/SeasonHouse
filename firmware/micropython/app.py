# SeasonHouse ceiling prop: wires the winch, sound, eyes, lights, sensors and
# the web page together. main.py starts this; if it crashes, main.py starts
# recovery.py so you can still upload a fix over Wi-Fi.
import gc
import machine
from machine import Pin
from compat import asyncio, sleep_ms, ticks_ms, ticks_diff, ticks_add, randint
import config
import settings
import net
import ota
import wled
from show import ShowEngine, load_seasons
from motion import Winch
from dfplayer import DFPlayer
from fx import Eyes, Chitter, EYE_MODES
from web import Server


class Rig:
    """What the show engine can do with the hardware."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.winch = Winch(cfg["drop"])
        self.mp3 = DFPlayer(cfg["vol"])
        self.eye = Eyes()
        self.buzz = Chitter()
        self.season_index = 0

    @property
    def drop(self):
        return self.winch.drop

    def ready(self):
        return self.winch.homed and not self.winch.homing

    def halt(self):
        self.winch.stop()
        self.mp3.stop()
        self.buzz.stop()
        self.eye.set("glow")

    def move_to(self, steps, speed):
        self.winch.move_to(steps, speed)

    def moving(self):
        return self.winch.moving()

    def position(self):
        return self.winch.position()

    def play(self, slot):
        self.mp3.play(self.season_index + 1, slot)

    def stop_sound(self):
        self.mp3.stop()

    def eyes(self, mode):
        self.eye.set(mode)

    def wled(self, slot):
        asyncio.create_task(wled.preset(self.cfg["wled"], self.season_index * 10 + slot))

    def chitter(self, ms):
        self.buzz.start(ms)


class App:
    def __init__(self):
        self.cfg = settings.load()
        self.seasons = load_seasons()
        self.rig = Rig(self.cfg)
        self.eng = ShowEngine(self.rig, self.seasons)
        self.eng.set_season(self.cfg["season"])
        self.rig.season_index = self.eng.season
        self.armed = self.cfg["armed"]
        self.party = False
        self.pir = Pin(config.PIN_PIR, Pin.IN)
        now = ticks_ms()
        self.last_scare = now          # gives the PIR its warm-up time
        self.next_party = now
        self.ip = ""

    def save(self):
        settings.save(self.cfg)

    # ------------------------------------------------------------ triggers
    def triggers(self):
        if self.eng.current or not self.rig.ready():
            return
        now = ticks_ms()
        S = self.eng.S
        if self.armed and self.pir.value() and ticks_diff(now, self.last_scare) > config.MOTION_COOLDOWN_MS:
            print("Motion!")
            if self.eng.start(S["scary"][randint(0, len(S["scary"]) - 1)]):
                self.last_scare = now
            return
        if self.party and ticks_diff(now, self.next_party) >= 0:
            self.eng.start(S["shows"][randint(0, len(S["shows"]) - 1)]["id"])
            self.last_scare = now
            self.next_party = ticks_add(now, randint(config.PARTY_MIN_MS, config.PARTY_MAX_MS))

    async def control_loop(self):
        while True:
            self.eng.tick()
            self.triggers()
            self.rig.eye.update()
            self.rig.buzz.update()
            await sleep_ms(5)

    # ------------------------------------------------------------ web API
    def status(self):
        w = self.rig.winch
        return {"season": self.eng.S["id"], "show": self.eng.current or "", "pos": w.position(), "drop": w.drop,
                "moving": w.moving(), "homed": w.homed, "homing": w.homing, "armed": self.armed,
                "party": self.party, "vol": self.cfg["vol"], "eyes": self.rig.eye.mode, "mp3": True,
                "wled": self.cfg["wled"], "ip": self.ip, "pir": bool(self.pir.value()), "top": w.top(),
                "free": getattr(gc, "mem_free", lambda: 0)()}

    def season_info(self):
        S = self.eng.S
        return {"season": S["id"], "character": S["char"],
                "seasons": [{"id": s["id"], "label": s["label"]} for s in self.seasons],
                "shows": [{"id": s["id"], "label": s["label"], "hint": s["hint"]} for s in S["shows"]],
                "sounds": S["sounds"], "wled": S["wled"]}

    def routes(self, srv):
        ok = lambda: (200, self.status())

        @srv.route("/")
        def index(req):
            return "file", "www/index.html", "text/html"

        @srv.route("/api/status")
        def status(req):
            return ok()

        @srv.route("/api/season")
        def season(req):
            s = req.arg("s")
            if s and s != self.eng.S["id"] and self.eng.set_season(s):
                self.rig.season_index = self.eng.season
                self.cfg["season"] = s
                self.save()
                self.rig.wled(1)
            return 200, self.season_info()

        @srv.route("/api/run")
        def run(req):
            started = self.eng.start(req.arg("show"))
            if started:
                self.last_scare = ticks_ms()
            return (200 if started else 409), self.status()

        @srv.route("/api/stop")
        def stop(req):
            self.eng.stop()
            return ok()

        @srv.route("/api/home")
        def home(req):
            self.eng.stop()
            self.rig.winch.home()
            return ok()

        @srv.route("/api/jog")
        def jog(req):
            if not self.eng.current and not self.rig.winch.homing:
                self.rig.winch.jog(int(req.arg("steps", "0")))
            return ok()

        @srv.route("/api/setdrop")
        def setdrop(req):
            d = int(req.arg("steps", "0")) or self.rig.winch.position()
            if d > 100:
                self.rig.winch.drop = d
                self.cfg["drop"] = d
                self.save()
            return ok()

        @srv.route("/api/arm")
        def arm(req):
            self.armed = req.arg("on") == "1"
            self.cfg["armed"] = self.armed
            self.save()
            return ok()

        @srv.route("/api/party")
        def party(req):
            self.party = req.arg("on") == "1"
            self.next_party = ticks_add(ticks_ms(), 15000)
            return ok()

        @srv.route("/api/vol")
        def vol(req):
            self.cfg["vol"] = max(0, min(30, int(req.arg("v", "20"))))
            self.rig.mp3.volume(self.cfg["vol"])
            self.save()
            return ok()

        @srv.route("/api/eyes")
        def eyes(req):
            if req.arg("mode") in EYE_MODES:
                self.rig.eye.set(req.arg("mode"))
            return ok()

        @srv.route("/api/sound")
        def sound(req):
            self.rig.play(int(req.arg("t", "1")))
            return ok()

        @srv.route("/api/chitter")
        def chitter(req):
            self.rig.chitter(800)
            return ok()

        @srv.route("/api/wled")
        def wled_route(req):
            if req.arg("host"):
                self.cfg["wled"] = req.arg("host")
                self.save()
            if req.arg("slot"):
                self.rig.wled(int(req.arg("slot")))
            return ok()

        # ---- wireless updates
        @srv.route("/api/ota")
        async def ota_upload(req):
            if req.method != "POST":
                return 400, {"ok": False, "error": "POST the file as the request body"}
            self.eng.stop()
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
            asyncio.create_task(self._reboot())
            return 200, {"ok": True, "rebooting": True}

    async def _reboot(self):
        await sleep_ms(500)
        machine.reset()

    async def run(self):
        self.ip, _ = net.connect()
        srv = Server()
        self.routes(srv)
        await srv.start(80)
        self.rig.winch.home()
        self.rig.wled(1)
        print("Ready. Season:", self.eng.S["label"])
        await self.control_loop()


def main():
    asyncio.run(App().run())
