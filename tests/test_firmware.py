"""PC tests for the MicroPython firmware, with fake ESP32 hardware.

Run: python3 tests/test_firmware.py
"""
import asyncio
import os
import shutil
import sys
import tempfile
import types
import unittest

FW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "firmware", "micropython")
sys.path.insert(0, FW)


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


machine = types.ModuleType("machine")
machine.Pin, machine.PWM, machine.Timer, machine.UART = Pin, PWM, Timer, UART
machine.reset = lambda: None
sys.modules["machine"] = machine
sys.modules["network"] = types.ModuleType("network")   # only used at runtime by net.py

import config  # noqa: E402
import motion  # noqa: E402
import ota  # noqa: E402
import web  # noqa: E402
from show import ShowEngine, load_seasons  # noqa: E402


class FakeRig:
    """Simulates the winch with the real motion maths, everything else is logged."""

    def __init__(self):
        self.p = motion.Profile()
        self.drop = config.DROP_STEPS
        self.log = []

    def ready(self):
        return True

    def halt(self):
        self.p.set(int(self.p.pos), self.p.vmax, self.p.acc)

    def move_to(self, steps, speed):
        steps = max(0, min(self.drop, int(steps)))
        self.p.set(steps, *motion.SPEEDS[speed])
        self.log.append(("move", steps))

    def moving(self):
        return self.p.moving()

    def position(self):
        return int(self.p.pos)

    def play(self, slot):
        assert 1 <= slot <= 8, slot
        self.log.append(("snd", slot))

    def stop_sound(self):
        self.log.append(("sndstop",))

    def eyes(self, mode):
        assert mode in ("off", "glow", "full", "pulse", "flicker", "blink", "disco"), mode
        self.log.append(("eyes", mode))

    def wled(self, slot):
        assert 1 <= slot <= 4, slot
        self.log.append(("wled", slot))

    def chitter(self, ms):
        self.log.append(("chit", ms))


class ShowTests(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        os.chdir(FW)
        self.seasons = load_seasons()

    def tearDown(self):
        os.chdir(self.cwd)

    def run_show(self, season, show):
        t = [0]
        rig = FakeRig()
        eng = ShowEngine(rig, self.seasons, clock=lambda: t[0])
        self.assertTrue(eng.set_season(season))
        self.assertTrue(eng.start(show))
        deepest = 0
        while eng.current is not None:
            eng.tick()
            rig.p.step(0.01)
            t[0] += 10
            deepest = max(deepest, rig.position())
            self.assertLess(t[0], 180000, "%s/%s never finished" % (season, show))
        return rig, t[0], deepest

    def test_every_show_finishes_back_home(self):
        n = 0
        for s in self.seasons:
            for sh in s["shows"]:
                rig, ms, deepest = self.run_show(s["id"], sh["id"])
                self.assertLessEqual(deepest, config.DROP_STEPS)
                self.assertEqual(rig.position(), 0, "%s/%s ends at %d" % (s["id"], sh["id"], rig.position()))
                n += 1
        self.assertEqual(n, sum(len(s["shows"]) for s in self.seasons))

    def test_classic_drop_reaches_the_bottom_fast(self):
        rig, ms, deepest = self.run_show("halloween", "drop")
        self.assertEqual(deepest, config.DROP_STEPS)
        self.assertIn(("snd", 2), rig.log)
        self.assertLess(ms, 40000)

    def test_scary_lists_name_real_shows(self):
        for s in self.seasons:
            ids = {sh["id"] for sh in s["shows"]}
            self.assertTrue(set(s["scary"]) <= ids, s["id"])
            self.assertEqual(len(s["sounds"]), 8)
            self.assertEqual(len(s["wled"]), 4)


class MotionTests(unittest.TestCase):
    def test_profile_respects_speed_and_lands_on_target(self):
        p = motion.Profile()
        p.set(3200, config.FAST_SPEED, config.FAST_ACCEL)
        top = 0
        for _ in range(1000):
            p.step(0.01)
            top = max(top, abs(p.vel))
        self.assertEqual(p.pos, 3200)
        self.assertLessEqual(top, config.FAST_SPEED)

    def test_winch_resets_to_zero_at_top_switch(self):
        Pin.levels.clear()
        w = motion.Winch(config.DROP_STEPS)
        Pin.levels[config.PIN_HOME_SW] = 1          # switch open
        w.home()
        for _ in range(20):
            w._tick(None)
        self.assertTrue(w.homing)
        Pin.levels[config.PIN_HOME_SW] = 0          # clicks
        w._tick(None)
        self.assertTrue(w.homed)
        self.assertEqual(w.position(), 0)
        Pin.levels[config.PIN_HOME_SW] = 1
        w.move_to(1000, 0)
        for _ in range(300):
            w._tick(None)
        self.assertEqual(w.position(), 1000)
        self.assertGreater(w.pwm.f, 0)

    def test_winch_creeps_up_until_switch_after_drift(self):
        Pin.levels.clear()
        w = motion.Winch(config.DROP_STEPS)
        w.homed = True
        Pin.levels[config.PIN_HOME_SW] = 1
        w.p.pos = 500.0
        w.move_to(0, 0)
        for _ in range(300):
            w._tick(None)
            if w.settle:
                break
        self.assertGreater(w.settle, 0, "should keep creeping because the switch is not pressed")
        w._tick(None)
        self.assertEqual(w.dir.value(), 1 - config.DIR_DOWN, "creeping must go up")
        self.assertTrue(w.moving())
        Pin.levels[config.PIN_HOME_SW] = 0
        w._tick(None)
        self.assertFalse(w.moving())
        self.assertEqual(w.settle, 0)


class OtaTests(unittest.TestCase):
    def test_names(self):
        for good in ("app.py", "www/index.html", "seasons.json", "my_prop-2.py"):
            self.assertTrue(ota.valid_name(good), good)
        for bad in ("../x.py", "/app.py", "a/b/c.py", "lib/x.py", "x.exe", "", "www/", "a b.py"):
            self.assertFalse(ota.valid_name(bad), bad)


class WebTests(unittest.TestCase):
    """Starts the real App on localhost with fake hardware and calls the API."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for f in os.listdir(FW):
            src = os.path.join(FW, f)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(self.tmp, f))
            else:
                shutil.copy(src, self.tmp)
        self.cwd = os.getcwd()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp)

    def test_api(self):
        import app

        async def http(port, method, path, body=b""):
            r, w = await asyncio.open_connection("127.0.0.1", port)
            w.write(("%s %s HTTP/1.1\r\nHost: x\r\nContent-Length: %d\r\n\r\n" % (method, path, len(body))).encode() + body)
            await w.drain()
            data = await r.read()
            w.close()
            head, _, payload = data.partition(b"\r\n\r\n")
            return int(head.split()[1]), payload

        async def scenario():
            a = app.App()
            a.rig.winch.homed = True
            srv = web.Server()
            a.routes(srv)
            server = await srv.start(0)
            port = server.sockets[0].getsockname()[1]
            import json
            code, body = await http(port, "GET", "/")
            self.assertEqual(code, 200)
            self.assertIn(b"Firmware update", body)
            code, body = await http(port, "GET", "/api/season?s=christmas")
            info = json.loads(body)
            self.assertEqual(info["season"], "christmas")
            self.assertEqual(info["character"], "Rappelling Santa")
            code, body = await http(port, "GET", "/api/run?show=hoho")
            self.assertEqual(code, 200)
            self.assertEqual(json.loads(body)["show"], "hoho")
            code, body = await http(port, "GET", "/api/stop")
            self.assertEqual(json.loads(body)["show"], "")
            code, body = await http(port, "GET", "/api/wled?host=10.0.0.9")
            self.assertEqual(json.loads(body)["wled"], "10.0.0.9")
            # wireless update: wrong key, bad code, good code
            code, body = await http(port, "POST", "/api/ota?file=extra.py&key=nope", b"x = 1\n")
            self.assertEqual(code, 403)
            code, body = await http(port, "POST", "/api/ota?file=extra.py&key=%s" % config.OTA_KEY, b"def oops(:\n")
            self.assertEqual(code, 400)
            self.assertFalse(os.path.exists("extra.py"))
            code, body = await http(port, "POST", "/api/ota?file=extra.py&key=%s" % config.OTA_KEY, b"x = 1\n")
            self.assertEqual(code, 200, body)
            self.assertEqual(open("extra.py").read(), "x = 1\n")
            code, body = await http(port, "POST", "/api/ota?file=main.py&key=%s" % config.OTA_KEY, b"x = 1\n")
            self.assertEqual(code, 403)
            code, body = await http(port, "POST", "/api/ota?file=www/index.html&key=%s" % config.OTA_KEY, b"<p>new</p>")
            self.assertEqual(code, 200)
            code, body = await http(port, "GET", "/")
            self.assertEqual(body, b"<p>new</p>")
            server.close()

        asyncio.run(scenario())
        self.assertEqual(open("settings.json").read().count("christmas"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
