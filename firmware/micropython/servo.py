# Hobby servo (MG996R, SG90...) on a 50 Hz PWM pin, with a speed limit so it
# moves smoothly instead of snapping. Call update() every few milliseconds.
from machine import Pin, PWM


class Servo:
    def __init__(self, pin, min_us=500, max_us=2500, max_deg=180, start=0):
        self.pwm = PWM(Pin(pin), freq=50, duty_u16=0)
        self.min_us, self.max_us, self.max_deg = min_us, max_us, max_deg
        self.pos = float(start)
        self.target = float(start)
        self.speed = 90.0          # degrees per second
        self.relaxed = True
        self._write()

    def move(self, deg, speed=90):
        self.target = float(max(0, min(self.max_deg, deg)))
        self.speed = float(speed)
        self.relaxed = False

    def moving(self):
        return abs(self.target - self.pos) > 0.5

    def relax(self):
        """Stop driving the servo (it goes quiet and can be pushed by hand)."""
        self.relaxed = True
        self.pwm.duty_u16(0)

    def update(self, dt_ms):
        if self.relaxed:
            return
        step = self.speed * dt_ms / 1000
        d = self.target - self.pos
        self.pos = self.target if abs(d) <= step else self.pos + (step if d > 0 else -step)
        self._write()

    def _write(self):
        if self.relaxed:
            return
        us = self.min_us + (self.max_us - self.min_us) * self.pos / self.max_deg
        self.pwm.duty_u16(int(us * 65535 // 20000))
