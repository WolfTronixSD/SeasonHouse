"""PC tests for the Lightning Window, Scream-o-Meter, Cauldron of Doom and
Rat Express firmware, with fake ESP32 hardware.

Run: python3 tests/test_props.py
"""
import asyncio
import json
import math
import os
import random
import shutil
import socket
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import stage_prop  # noqa: E402


# ---------------------------------------------------------------- fake ESP32
class Pin:
    IN, OUT, PULL_UP = 0, 1, 2
    levels = {}

    def __init__(self, n, mode=0, pull=None, value=None):
        self.n = n
        if value is not None:
            Pin.levels[n] = value
        Pin.levels.setdefault(n, 1 if pull == Pin.PULL_UP else 0)

    def value(self, v=None):
        if v is None:
            return Pin.levels[self.n]
        Pin.levels[self.n] = v

    __call__ = value


class PWM:
    def __init__(self, pin, freq=0, duty_u16=0):
        self.f, self.d = freq, duty_u16

    def freq(self, f=None):
        if f is not None:
            self.f = f
        return self.f

    def duty_u16(self, d=None):
        if d is not None:
            self.d = d
        return self.d


class Timer:
    PERIODIC = 1

    def __init__(self, n):
        self.cb = None

    def init(self, period, mode, callback):
        self.cb = callback


class UART:
    def __init__(self, *a, **k):
        self.sent = []

    def write(self, b):
        self.sent.append(bytes(b))


class SPI:
    def __init__(self, *a, **k):
        self.sent = []

    def write(self, b):
        self.sent.append(bytes(b))


class I2S:
    RX, MONO = 0, 0

    def __init__(self, *a, **k):
        pass


class NeoPixel:
    def __init__(self, pin, n):
        self.px = [(0, 0, 0)] * n
        self.writes = 0

    def __setitem__(self, i, v):
        self.px[i] = v

    def write(self):
        self.writes += 1


machine = types.ModuleType("machine")
machine.Pin, machine.PWM, machine.Timer, machine.UART, machine.SPI, machine.I2S = Pin, PWM, Timer, UART, SPI, I2S
machine.reset = lambda: None
sys.modules["machine"] = machine
sys.modules["network"] = types.ModuleType("network")
neopixel = types.ModuleType("neopixel")
neopixel.NeoPixel = NeoPixel
sys.modules["neopixel"] = neopixel


class Clock:
    def __init__(self):
        self.t = 0

    def __call__(self):
        return self.t


class FakeMP3:
    def __init__(self):
        self.log = []

    def play(self, folder, track):
        self.log.append(("play", folder, track))

    def volume(self, v):
        self.log.append(("vol", v))

    def stop(self):
        self.log.append(("stop",))

    def loop(self, on=True):
        self.log.append(("loop", on))

    def plays(self):
        return [e[2] for e in self.log if e[0] == "play"]


class FakeStrip:
    def __init__(self, n=30):
        self.n = n
        self.px = [(0, 0, 0)] * n
        self.frames = []

    def set(self, i, rgb):
        self.px[i] = tuple(int(v) for v in rgb)

    def fill(self, rgb):
        self.px = [tuple(rgb)] * self.n

    def show(self):
        self.frames.append(list(self.px))

    def release(self):
        pass

    def brightness(self):
        return max(sum(p) for p in self.px)


class FakeMatrix:
    def __init__(self):
        self.shown = []

    def show(self, text):
        if not self.shown or self.shown[-1] != text:
            self.shown.append(text)

    def tick(self):
        pass


# ---------------------------------------------------------------- loading a prop
class PropCase(unittest.TestCase):
    """Stages one prop into a temp folder and imports its modules from there."""
    PROP = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        stage_prop.stage(self.PROP, self.tmp)
        self.cwd = os.getcwd()
        os.chdir(self.tmp)
        for f in os.listdir(self.tmp):
            if f.endswith(".py"):
                sys.modules.pop(f[:-3], None)
        sys.path.insert(0, self.tmp)
        Pin.levels.clear()

    def tearDown(self):
        sys.path.remove(self.tmp)
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp)

    def mod(self, name):
        __import__(name)
        return sys.modules[name]

    def web(self, app, calls):
        """Start the prop's real web server on localhost and run calls(get)."""
        web = self.mod("web")

        async def scenario():
            srv = web.Server()
            app.routes(srv)
            server = await srv.start(0)
            port = server.sockets[0].getsockname()[1]

            async def get(path):
                r, w = await asyncio.open_connection("127.0.0.1", port)
                w.write(("GET %s HTTP/1.1\r\nHost: x\r\n\r\n" % path).encode())
                await w.drain()
                data = await r.read()
                w.close()
                head, _, body = data.partition(b"\r\n\r\n")
                code = int(head.split()[1])
                return code, (json.loads(body) if body[:1] in b"{[" else body)

            await calls(get)
            server.close()

        asyncio.run(scenario())
        sock = getattr(getattr(app, "strip", None), "sock", None)
        if sock:
            sock.close()


# ---------------------------------------------------------------- Lightning Window
class LightningTests(PropCase):
    PROP = "lightning"

    def storm(self, seed=1):
        storm = self.mod("storm")
        self.clock = Clock()
        self.strip, self.mp3, self.sil = FakeStrip(), FakeMP3(), Pin(25, Pin.OUT, value=0)
        return storm.Storm(self.strip, self.mp3, self.sil, 26, self.clock, random.Random(seed).randint)

    def run_strike(self, s, **kw):
        """Strike, then step 5 ms at a time until the thunder plays. Returns
        (thunder delay ms, first flash ms, silhouette ever on)."""
        info = s.strike(**kw)
        t0, first, sil = self.clock.t, None, False
        while True:
            s.update()
            if first is None and self.strip.frames and self.strip.brightness() > 0:
                first = self.clock.t - t0
            sil = sil or self.sil.value() == 1
            if self.mp3.plays():
                return self.clock.t - t0, first, sil, info
            self.clock.t += 5

    def test_flash_comes_first_and_thunder_follows_one_to_three_seconds_later(self):
        for seed in range(20):
            s = self.storm(seed)
            delay, first, _, info = self.run_strike(s)
            self.assertEqual(first, 0)
            self.assertTrue(1000 <= delay <= 3005, delay)
            near = delay < 1600
            self.assertEqual(self.mp3.plays()[0] in (1, 2, 3), near)
            # further away = quieter
            vol = [e[1] for e in self.mp3.log if e[0] == "vol"][-1]
            self.assertLessEqual(vol, 26)

    def test_every_tenth_strike_shows_the_axe_man(self):
        s = self.storm()
        shown = []
        for n in range(1, 31):
            self.mp3.log.clear()
            _, _, sil, _ = self.run_strike(s)
            while s.busy():                  # let the flash finish
                s.update()
                self.clock.t += 5
            self.assertEqual(self.sil.value(), 0)
            if sil:
                shown.append(n)
        self.assertEqual(shown, [10, 20, 30])

    def test_close_strike_cracks_quickly(self):
        s = self.storm(3)
        delay, _, _, info = self.run_strike(s, close=True)
        self.assertLess(delay, 1600)
        self.assertTrue(info["near"])

    def test_auto_storm_keeps_striking(self):
        s = self.storm(5)
        s.set_auto(True, 3)
        for _ in range(60 * 200):            # one minute
            s.update()
            self.clock.t += 5
        self.assertGreaterEqual(s.count, 5)

    def test_strip_streams_to_wled_over_udp(self):
        strip = self.mod("strip")
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            rx.bind(("127.0.0.1", strip.PORT))
        except OSError:
            self.skipTest("UDP port 21324 busy")
        rx.settimeout(2)
        st = strip.Strip(600, "wled", "127.0.0.1")
        st.fill((10, 20, 30))
        st.show()
        a, b = rx.recv(2000), rx.recv(2000)
        rx.close()
        self.assertEqual(a[:4], bytes((4, 2, 0, 0)))
        self.assertEqual(len(a), 4 + 489 * 3)
        self.assertEqual(b[:4], bytes((4, 2, 489 >> 8, 489 & 255)))
        self.assertEqual(len(b), 4 + 111 * 3)
        self.assertEqual(a[4:7], bytes((10, 20, 30)))
        st.sock.close()

    def test_web_api(self):
        app = self.mod("app").App()

        async def calls(get):
            code, body = await get("/")
            self.assertEqual(code, 200)
            self.assertIn(b"LIGHTNING", body)
            code, s = await get("/api/strike?kind=axe")
            self.assertTrue(s["busy"])
            self.assertTrue(s["last"]["silhouette"])
            code, s = await get("/api/storm?on=1&level=3")
            self.assertTrue(s["auto"])
            self.assertEqual(s["level"], 3)
            code, s = await get("/api/every?n=5")
            self.assertEqual(s["every"], 5)
            code, s = await get("/api/stop")
            self.assertFalse(s["auto"])
            self.assertFalse(s["busy"])

        self.web(app, calls)
        with open("settings.json") as f:
            self.assertEqual(json.load(f)["every"], 5)


# ---------------------------------------------------------------- Scream-o-Meter
class ScreamTests(PropCase):
    PROP = "screamometer"

    def meter(self):
        m = self.mod("meter")
        self.clock = Clock()
        self.mp3, self.dm, self.strip = FakeMP3(), FakeMatrix(), FakeStrip(40)
        self.board = []
        return m.Meter(self.strip, self.dm, self.mp3, self.board, self.clock)

    def test_level_of_a_sine(self):
        mic = self.mod("mic")
        amp = 0.1 * 2 ** 31
        samples = [int(amp * math.sin(i * 0.3)) + 12345 for i in range(512)]
        # rms of a sine = amp/sqrt(2): 0.0707 full scale = -23 dBFS -> 97 dB
        self.assertAlmostEqual(mic.level_db(samples), 97.0, delta=0.5)
        self.assertEqual(mic.level_db([0] * 512), 0)

    def play_round(self, m, levels, name=""):
        self.assertTrue(m.start(name))
        for _ in range(3000 // 40):
            m.feed(60)
            m.update()
            self.clock.t += 40
        m.update()
        self.assertEqual(m.phase, "listen")
        i = 0
        while m.phase == "listen":
            m.feed(levels[i % len(levels)])
            i += 1
            m.update()
            self.clock.t += 30
        return m.score

    def test_round_counts_down_then_scores_the_loudest_moment(self):
        m = self.meter()
        score = self.play_round(m, [80, 92, 104, 99], "Wolfgang")
        self.assertEqual(score, 104)
        self.assertEqual(self.dm.shown[:4], ["3", "2", "1", "SCREAM!"])
        self.assertEqual(self.dm.shown[-1], "104 DB")
        self.assertEqual(self.board, [{"name": "Wolfgang", "db": 104}])
        self.assertTrue(m.record)
        self.assertEqual(self.mp3.plays(), [1, 2])     # countdown, new record

    def test_leaderboard_sorted_and_capped(self):
        m = self.meter()
        for db in (90, 110, 70, 95, 100, 101, 102, 103, 80, 85, 88, 99):
            self.play_round(m, [db])
            while m.phase == "result":
                m.update()
                self.clock.t += 200
        self.assertEqual(len(self.board), 10)
        self.assertEqual([e["db"] for e in self.board], sorted([e["db"] for e in self.board], reverse=True))
        self.assertEqual(self.board[0]["db"], 110)
        self.assertNotIn(70, [e["db"] for e in self.board])

    def test_loud_scream_sets_off_other_props_once_per_cooldown(self):
        m = self.meter()
        fired = []
        m.on_trigger = fired.append
        self.clock.t = 100000
        for db in (70, 105, 108, 70):
            m.feed(db)
            self.clock.t += 50
        self.assertEqual(fired, [105])
        self.clock.t += 25000
        m.feed(101)
        self.assertEqual(fired, [105, 101])

    def test_vu_bar_fills_with_the_level(self):
        m = self.meter()
        m.feed(85)                            # half way between 55 and 115
        m.update()
        lit = sum(1 for p in self.strip.px if max(p) > 100)
        self.assertTrue(18 <= lit <= 22, lit)
        self.assertEqual(self.strip.px[0][1], 255)  # green at the bottom

    def test_web_api(self):
        mic = self.mod("mic")

        class FakeMic:
            def __init__(self, *a, **k):
                self.offset = 120

            async def read_db(self):
                await asyncio.sleep(0.03)
                return 70

        mic.Mic = FakeMic
        a = self.mod("app")
        app = a.App()

        async def calls(get):
            code, s = await get("/api/status")
            self.assertEqual(s["phase"], "idle")
            code, s = await get("/api/round?name=Ann")
            self.assertEqual(code, 200)
            self.assertEqual(s["phase"], "countdown")
            code, s = await get("/api/round")
            self.assertEqual(code, 409)
            code, s = await get("/api/trigger?on=0&db=95")
            self.assertFalse(s["trigger"])
            self.assertEqual(s["trigger_db"], 95)

        self.web(app, calls)


# ---------------------------------------------------------------- Cauldron of Doom
class CauldronTests(PropCase):
    PROP = "cauldron"

    def app(self):
        a = self.mod("app")
        app = a.App()
        app.rig.mp3 = self.mp3 = FakeMP3()
        app.rig.wled = lambda slot: self.lights.append(slot)
        self.lights = []
        return app

    def run_until_idle(self, app, limit_ms=60000):
        peak, fog_seen, t = 0, False, 0
        while app.eng.current is not None and t < limit_ms:
            app.tick(10)
            peak = max(peak, app.rig.position())
            fog_seen = fog_seen or app.rig.fog_ctl.on
            t += 10
            # speed up WAITs: move the engine's wait target into the past
            if app.eng.wait_until is not None:
                app.eng.wait_until = app.eng.clock() - 1
        for _ in range(500):
            app.tick(10)
        return peak, fog_seen

    def test_the_hand_rises_out_of_the_fog_and_goes_back(self):
        app = self.app()
        app.rig.fog_ctl.mode = "off"
        self.assertTrue(app.eng.start("rise"))
        peak, fog = self.run_until_idle(app)
        self.assertGreaterEqual(peak, 990)
        self.assertTrue(fog)
        self.assertFalse(app.rig.fog_ctl.on)                  # fog back off after the scare
        self.assertLessEqual(abs(app.rig.position()), 5)      # hand hidden again
        self.assertEqual(self.lights[0], 2)
        self.assertEqual(self.lights[-1], 1)
        self.assertIn(("loop", True), self.mp3.log)            # bubbling resumed
        self.assertEqual(self.mp3.plays()[-1], 1)

    def test_every_scare_ends_with_the_hand_down(self):
        shows = self.mod("shows")
        app = self.app()
        for sh in shows.SHOWS:
            self.assertTrue(app.eng.start(sh["id"]), sh["id"])
            self.run_until_idle(app)
            self.assertLessEqual(abs(app.rig.position()), 5, sh["id"])
        for s in shows.SCARY:
            self.assertTrue(any(x["id"] == s for x in shows.SHOWS))

    def test_fog_cycles_and_rests_after_a_long_run(self):
        a = self.mod("app")
        config = self.mod("config")
        clock = Clock()
        pin = Pin(26, Pin.OUT, value=0)
        fog = a.Fog(pin, Pin(35, Pin.IN, Pin.PULL_UP), "cycle", clock)
        states = []
        for _ in range(0, 120000, 1000):
            fog.update()
            states.append(pin.value())
            clock.t += 1000
        on_share = sum(states) / len(states)
        self.assertAlmostEqual(on_share, config.FOG_CYCLE_ON_MS / (config.FOG_CYCLE_ON_MS + config.FOG_CYCLE_OFF_MS), delta=0.05)
        fog.mode = "on"
        clock.t = 10 ** 7
        rested = False
        for _ in range(0, 200000, 1000):
            fog.update()
            rested = rested or (pin.value() == 0 and fog.since != 0)
            clock.t += 1000
        self.assertTrue(rested)

    def test_web_api(self):
        app = self.app()

        async def calls(get):
            code, s = await get("/api/status")
            self.assertEqual(len(s["shows"]), 5)
            code, s = await get("/api/run?show=peek")
            self.assertEqual(s["show"], "peek")
            code, s = await get("/api/fog?mode=on")
            self.assertEqual(s["fog"], "on")
            code, s = await get("/api/hand?down=5&up=160")
            self.assertEqual((s["hand_down"], s["hand_up"]), (5, 160))
            code, s = await get("/api/stop")
            self.assertEqual(s["show"], "")

        self.web(app, calls)


# ---------------------------------------------------------------- Rat Express
class RatTests(PropCase):
    PROP = "rat"

    def test_every_run_crosses_the_floor_and_goes_home(self):
        motion = self.mod("motion")
        show = self.mod("show")
        shows = self.mod("shows")
        config = self.mod("config")

        class Rig:
            drop = config.DROP_STEPS

            def __init__(self):
                self.p = motion.Profile()
                self.snd = []

            def ready(self):
                return True

            def halt(self):
                pass

            def move_to(self, s, sp):
                self.p.set(max(0, min(self.drop, int(s))), *motion.SPEEDS[sp])

            def moving(self):
                return self.p.moving()

            def position(self):
                return int(self.p.pos)

            def play(self, n):
                assert 1 <= n <= 6
                self.snd.append(n)

            def stop_sound(self):
                pass

        for sh in shows.SHOWS:
            t = [0]
            rig = Rig()
            eng = show.ShowEngine(rig, [{"id": "rat", "label": "Rat", "shows": shows.SHOWS}], clock=lambda: t[0])
            self.assertTrue(eng.start(sh["id"]))
            far = 0
            while eng.current is not None and t[0] < 60000:
                eng.tick()
                rig.p.step(0.005)
                t[0] += 5
                far = max(far, rig.position())
            self.assertIsNone(eng.current, sh["id"])
            self.assertEqual(rig.position(), 0, sh["id"])
            self.assertGreaterEqual(far, config.DROP_STEPS * 0.8, sh["id"])
            self.assertTrue(rig.snd, sh["id"])

    def test_web_api(self):
        app = self.mod("app").App()
        app.rig.winch.homed = True
        app.rig.mp3 = FakeMP3()

        async def calls(get):
            code, s = await get("/api/status")
            self.assertEqual(s["len"], 6000)
            code, s = await get("/api/run?show=dash")
            self.assertEqual(s["show"], "dash")
            code, s = await get("/api/stop")
            self.assertEqual(s["show"], "")
            code, s = await get("/api/setlen?steps=4500")
            self.assertEqual(s["len"], 4500)

        self.web(app, calls)


if __name__ == "__main__":
    unittest.main(verbosity=1)
