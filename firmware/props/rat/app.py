# Rat Express: a stepper pulls a loop of fishing line along the baseboard and a
# toy rat clipped to it scurries across the floor, right behind people's
# ankles, with squeaks from the MP3. Same winch code as the ceiling prop.
from machine import Pin
from compat import asyncio, sleep_ms, ticks_ms, ticks_diff, ticks_add, randint
import config
import settings
import net
from web import Server
from dfplayer import DFPlayer
from motion import Winch
from show import ShowEngine
from shows import SHOWS, SCARY, SOUNDS
from propkit import system_routes, Cooldown, free


class Rig:
    def __init__(self, cfg):
        self.winch = Winch(cfg["len"])
        self.mp3 = DFPlayer(cfg["vol"])

    @property
    def drop(self):
        return self.winch.drop

    def ready(self):
        return self.winch.homed and not self.winch.homing

    def halt(self):
        self.winch.stop()
        self.mp3.stop()

    def move_to(self, steps, speed):
        self.winch.move_to(steps, speed)

    def moving(self):
        return self.winch.moving()

    def position(self):
        return self.winch.position()

    def play(self, slot):
        self.mp3.play(1, slot)

    def stop_sound(self):
        self.mp3.stop()

    def eyes(self, mode):
        pass

    def wled(self, slot):
        pass

    def chitter(self, ms):
        pass

    def fog(self, on):
        pass


class App:
    def __init__(self):
        self.cfg = settings.load()
        self.rig = Rig(self.cfg)
        self.eng = ShowEngine(self.rig, [{"id": "rat", "label": "Rat Express", "shows": SHOWS}])
        self.pir = Pin(config.PIN_PIR, Pin.IN)
        self.armed = self.cfg["armed"]
        self.party = False
        self.cool = Cooldown(config.MOTION_COOLDOWN_MS)
        self.next_party = ticks_ms()
        self.ip = ""

    def save(self):
        settings.save(self.cfg)

    def triggers(self):
        if self.eng.current or not self.rig.ready():
            return
        if self.armed and self.pir.value() and self.cool.ready():
            print("Motion!")
            if self.eng.start(SCARY[randint(0, len(SCARY) - 1)]):
                self.cool.fire()
        elif self.party and ticks_diff(ticks_ms(), self.next_party) >= 0:
            self.eng.start(SHOWS[randint(0, len(SHOWS) - 1)]["id"])
            self.cool.fire()
            self.next_party = ticks_add(ticks_ms(), randint(config.PARTY_MIN_MS, config.PARTY_MAX_MS))

    def status(self):
        w = self.rig.winch
        return {"prop": "rat", "show": self.eng.current or "", "pos": w.position(), "len": w.drop,
                "moving": w.moving(), "homed": w.homed, "homing": w.homing, "top": w.top(),
                "armed": self.armed, "party": self.party, "vol": self.cfg["vol"],
                "shows": [{"id": s["id"], "label": s["label"], "hint": s["hint"]} for s in SHOWS], "sounds": SOUNDS,
                "pir": bool(self.pir.value()), "ip": self.ip, "free": free()}

    def routes(self, srv):
        ok = lambda: (200, self.status())

        @srv.route("/")
        def index(req):
            return "file", "www/index.html", "text/html"

        @srv.route("/api/status")
        def status(req):
            return ok()

        @srv.route("/api/run")
        def run(req):
            started = self.eng.start(req.arg("show"))
            if started:
                self.cool.fire()
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

        @srv.route("/api/setlen")
        def setlen(req):
            n = int(req.arg("steps", "0")) or self.rig.winch.position()
            if n > 100:
                self.rig.winch.drop = self.cfg["len"] = n
                self.save()
            return ok()

        @srv.route("/api/arm")
        def arm(req):
            self.armed = self.cfg["armed"] = req.arg("on") == "1"
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

        @srv.route("/api/sound")
        def sound(req):
            self.rig.play(int(req.arg("t", "1")))
            return ok()

        system_routes(srv, self.eng.stop)

    async def loop(self):
        while True:
            self.eng.tick()
            self.triggers()
            await sleep_ms(5)

    async def run(self):
        self.ip, _ = net.connect()
        srv = Server()
        self.routes(srv)
        await srv.start(80)
        self.rig.winch.home()
        print("Rat Express ready")
        await self.loop()


def main():
    asyncio.run(App().run())
