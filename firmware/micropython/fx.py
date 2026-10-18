# LED eyes and the piezo "chitter". Both are updated every few ms by app.py.
from machine import Pin, PWM
from compat import ticks_ms, ticks_diff, ticks_add, randint
import math
import config

EYE_MODES = ("off", "glow", "full", "pulse", "flicker", "blink", "disco")


class Eyes:
    def __init__(self):
        self.l = PWM(Pin(config.PIN_EYE_L), freq=5000, duty_u16=0)
        self.r = PWM(Pin(config.PIN_EYE_R), freq=5000, duty_u16=0)
        self.mode = "glow"
        self.flick = 65535
        self.next_flick = 0
        self.next_blink = 0
        self.blink_end = 0

    def set(self, mode):
        if mode in EYE_MODES:
            self.mode = mode

    def _write(self, l, r):
        # levels 0..1, squared so the fade looks even to the eye
        self.l.duty_u16(int(l * l * 65535))
        self.r.duty_u16(int(r * r * 65535))

    def update(self):
        now = ticks_ms()
        m = self.mode
        if m == "off":
            self._write(0, 0)
        elif m == "glow":
            self._write(0.3, 0.3)
        elif m == "full":
            self._write(1, 1)
        elif m == "pulse":
            v = 0.1 + 0.9 * (math.sin(now / 1500 * 2 * math.pi) + 1) / 2
            self._write(v, v)
        elif m == "flicker":
            if ticks_diff(now, self.next_flick) >= 0:
                self.flick = randint(25, 100) / 100
                self.next_flick = ticks_add(now, randint(20, 90))
            self._write(self.flick, self.flick)
        elif m == "blink":
            if ticks_diff(now, self.next_blink) >= 0:
                self.blink_end = ticks_add(now, 140)
                self.next_blink = ticks_add(now, randint(1500, 4000))
            v = 0 if ticks_diff(self.blink_end, now) > 0 else 0.9
            self._write(v, v)
        elif m == "disco":
            left = (now // 220) % 2
            self._write(1 if left else 0, 0 if left else 1)


class Chitter:
    def __init__(self):
        self.pwm = PWM(Pin(config.PIN_BUZZER), freq=3000, duty_u16=0)
        self.until = 0
        self.next = 0
        self.off_at = 0
        self.on = False

    def start(self, ms):
        self.until = ticks_add(ticks_ms(), ms)

    def stop(self):
        self.until = ticks_ms()

    def update(self):
        now = ticks_ms()
        if self.on and ticks_diff(now, self.off_at) >= 0:
            self.pwm.duty_u16(0)
            self.on = False
        if ticks_diff(self.until, now) > 0 and ticks_diff(now, self.next) >= 0:
            self.pwm.freq(randint(2200, 4800))
            self.pwm.duty_u16(32768)
            self.on = True
            self.off_at = ticks_add(now, randint(4, 12))
            self.next = ticks_add(now, randint(25, 70))
