# Cauldron of Doom: an ultrasonic mister fogs a bowl inside the cauldron, WLED
# glows green underneath, the MP3 bubbles away, and when someone walks past a
# servo raises a hand out of the fog.
from machine import Pin
from compat import asyncio, sleep_ms, ticks_ms, ticks_diff, ticks_add, randint
import config
import settings
import net
import wled
from web import Server
from dfplayer import DFPlayer
from servo import Servo
from show import ShowEngine
from shows import SHOWS, SCARY, SOUNDS
from propkit import system_routes, Cooldown, free


class Fog:
    """The mist maker: off / cycle / on, plus scares that force it on, with a
    rest after a long run and an optional low-water cut-out."""

    def __init__(self, pin, water, mode, clock=ticks_ms):
        self.pin = pin
        self.water = water
        self.mode = mode
        self.clock = clock
        self.boost = False
        self.on = False
        self.since = clock()
        self.rest_until = None

    def water_low(self):
        return config.HAS_WATER_SWITCH and self.water.value() == 1

    def update(self):
        now = self.clock()
        want = self.boost or self.mode == "on"
        if self.mode == "cycle" and not self.boost:
            period = config.FOG_CYCLE_ON_MS + config.FOG_CYCLE_OFF_MS
            want = now % period < config.FOG_CYCLE_ON_MS
        if self.rest_until is not None:
            if ticks_diff(now, self.rest_until) < 0:
                want = False
            else:
                self.rest_until = None
        if self.on and ticks_diff(now, self.since) > config.FOG_MAX_ON_MS:
            self.rest_until = ticks_add(now, config.FOG_REST_MS)
            want = False
        if self.water_low():
            want = False
        if want != self.on:
            self.on = want
            self.since = now
            self.pin.value(1 if want else 0)


class Rig:
    """What the show engine can do with the cauldron. MOVE = the hand."""

    drop = 1000

    def __init__(self, cfg):
        self.cfg = cfg
        self.hand = Servo(config.PIN_SERVO, start=cfg["hand_down"])
        self.mp3 = DFPlayer(cfg["vol"])
        self.fog_ctl = Fog(Pin(config.PIN_MIST, Pin.OUT, value=0), Pin(config.PIN_WATER, Pin.IN, Pin.PULL_UP), cfg["fog"])
        self.looping = False

    def angle(self, steps):
        lo, hi = self.cfg["hand_down"], self.cfg["hand_up"]
        return lo + (hi - lo) * steps / 1000

    def ready(self):
        return True

    def halt(self):
        self.hand.move(self.cfg["hand_down"], config.HAND_SPEEDS[2])
        self.mp3.stop()
        self.looping = False
        self.fog_ctl.boost = False

    def move_to(self, steps, speed):
        self.hand.move(self.angle(max(0, min(1000, steps))), config.HAND_SPEEDS[speed])

    def moving(self):
        return self.hand.moving()

    def position(self):
        lo, hi = self.cfg["hand_down"], self.cfg["hand_up"]
        return int(round((self.hand.pos - lo) * 1000 / ((hi - lo) or 1)))

    def play(self, slot):
        if self.looping:
            self.mp3.loop(False)
            self.looping = False
        self.mp3.play(1, slot)

    def bubble(self):
        self.mp3.play(1, 1)
        self.mp3.loop(True)
        self.looping = True

    def stop_sound(self):
        self.mp3.stop()
        self.looping = False

    def eyes(self, mode):
        pass

    def chitter(self, ms):
        pass

    def wled(self, slot):
        asyncio.create_task(wled.preset(self.cfg["wled"], config.WLED_BASE + slot))

    def fog(self, on):
        self.fog_ctl.boost = bool(on)


class App:
    def __init__(self):
        self.cfg = settings.load()
        self.rig = Rig(self.cfg)
        self.eng = ShowEngine(self.rig, [{"id": "cauldron", "label": "Cauldron of Doom", "shows": SHOWS}])
        self.pir = Pin(config.PIN_PIR, Pin.IN)
        self.armed = self.cfg["armed"]
        self.party = False
        self.cool = Cooldown(config.MOTION_COOLDOWN_MS)
        self.next_party = ticks_ms()
        self.was_running = False
        self.ip = ""

    def save(self):
        settings.save(self.cfg)

    def idle(self):
        """Back to the resting cauldron: hand down, green glow, bubbling."""
        self.rig.hand.move(self.cfg["hand_down"], config.HAND_SPEEDS[2])
        if self.cfg["bubbling"]:
            self.rig.bubble()
        self.rig.wled(1)

    def triggers(self):
        if self.eng.current:
            return
        if self.armed and self.pir.value() and self.cool.ready():
            print("Motion!")
            self.eng.start(SCARY[randint(0, len(SCARY) - 1)])
            self.cool.fire()
        elif self.party and ticks_diff(ticks_ms(), self.next_party) >= 0:
            self.eng.start(SHOWS[randint(0, len(SHOWS) - 1)]["id"])
            self.cool.fire()
            self.next_party = ticks_add(ticks_ms(), randint(config.PARTY_MIN_MS, config.PARTY_MAX_MS))

    def status(self):
        r = self.rig
        return {"prop": "cauldron", "show": self.eng.current or "", "armed": self.armed, "party": self.party,
                "fog": r.fog_ctl.mode, "mist": r.fog_ctl.on, "water_low": r.fog_ctl.water_low(),
                "bubbling": self.cfg["bubbling"], "vol": self.cfg["vol"], "wled": self.cfg["wled"],
                "hand": max(0, min(100, r.position() // 10)), "hand_down": self.cfg["hand_down"], "hand_up": self.cfg["hand_up"],
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
            self.idle()
            return ok()

        @srv.route("/api/fog")
        def fog(req):
            if req.arg("mode") in ("off", "cycle", "on"):
                self.cfg["fog"] = self.rig.fog_ctl.mode = req.arg("mode")
                self.save()
            return ok()

        @srv.route("/api/bubble")
        def bubble(req):
            self.cfg["bubbling"] = req.arg("on") == "1"
            self.save()
            if self.cfg["bubbling"]:
                self.rig.bubble()
            else:
                self.rig.stop_sound()
            return ok()

        @srv.route("/api/hand")
        def hand(req):
            if req.arg("down"):
                self.cfg["hand_down"] = max(0, min(180, int(req.arg("down"))))
            if req.arg("up"):
                self.cfg["hand_up"] = max(0, min(180, int(req.arg("up"))))
            if req.arg("down") or req.arg("up"):
                self.save()
            if req.arg("go") == "up":
                self.rig.move_to(1000, 2)
            elif req.arg("go") == "down":
                self.rig.move_to(0, 2)
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
            t = int(req.arg("t", "1"))
            if t == 1:
                self.rig.bubble()
            else:
                self.rig.play(t)
            return ok()

        @srv.route("/api/wled")
        def wled_route(req):
            if req.arg("host"):
                self.cfg["wled"] = req.arg("host")
                self.save()
            if req.arg("slot"):
                self.rig.wled(int(req.arg("slot")))
            return ok()

        system_routes(srv, self.eng.stop)

    def tick(self, dt_ms):
        self.eng.tick()
        running = self.eng.current is not None
        if self.was_running and not running:
            self.idle()                      # a scare just ended
        self.was_running = running
        self.triggers()
        self.rig.hand.update(dt_ms)
        self.rig.fog_ctl.update()

    async def loop(self):
        last = ticks_ms()
        while True:
            now = ticks_ms()
            self.tick(ticks_diff(now, last))
            last = now
            await sleep_ms(10)

    async def run(self):
        self.ip, _ = net.connect()
        srv = Server()
        self.routes(srv)
        await srv.start(80)
        self.idle()
        print("Cauldron of Doom ready")
        await self.loop()


def main():
    asyncio.run(App().run())
