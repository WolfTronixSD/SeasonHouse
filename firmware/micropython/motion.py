# The winch: a stepper on a STEP/DIR driver, driven by a hardware PWM signal on
# the STEP pin so the drop stays smooth whatever else the ESP32 is doing.
# A 10 ms timer ramps the PWM frequency (= steps per second) up and down.
#
# Position is counted from the speed over time, which can drift a few steps.
# That never adds up: every time the prop goes home it keeps winding slowly
# until the top switch clicks, and that resets the count to exactly 0.
import config


class Profile:
    """Trapezoid motion maths, no hardware. Position 0 = home, positive = down."""

    def __init__(self):
        self.pos = 0.0
        self.vel = 0.0
        self.target = 0
        self.vmax = config.FAST_SPEED
        self.acc = config.FAST_ACCEL

    def set(self, target, vmax, acc):
        self.target = target
        self.vmax = vmax
        self.acc = acc

    def moving(self):
        return abs(self.target - self.pos) > 0.5 or abs(self.vel) > 1

    def step(self, dt):
        d = self.target - self.pos
        if abs(d) <= 0.5 and abs(self.vel) <= self.acc * dt * 2:
            self.pos = float(self.target)
            self.vel = 0.0
            return
        direction = 1 if d > 0 else -1
        stop_dist = self.vel * self.vel / (2 * self.acc)
        if (self.vel > 0) == (direction > 0) and self.vel != 0 and stop_dist >= abs(d):
            self.vel -= (1 if self.vel > 0 else -1) * self.acc * dt
        else:
            self.vel += direction * self.acc * dt
        self.vel = max(-self.vmax, min(self.vmax, self.vel))
        new = self.pos + self.vel * dt
        if (self.target - new) * direction <= 0:
            self.pos = float(self.target)
            self.vel = 0.0
        else:
            self.pos = new


SPEEDS = (
    (config.FAST_SPEED, config.FAST_ACCEL),
    (config.SLOW_SPEED, config.SLOW_ACCEL),
    (config.FAST_SPEED // 3, config.FAST_ACCEL // 3),
)
MIN_HZ = 20          # below this the PWM is switched off
TICK_MS = 10
SETTLE_STEPS = 400   # how far past "0" it may creep looking for the switch


class Winch:
    def __init__(self, drop):
        from machine import Pin, PWM, Timer

        self.drop = drop
        self.p = Profile()
        self.dir = Pin(config.PIN_DIR, Pin.OUT)
        self.en = Pin(config.PIN_EN, Pin.OUT, value=1)   # off
        self.sw = Pin(config.PIN_HOME_SW, Pin.IN, Pin.PULL_UP)
        self.pwm = PWM(Pin(config.PIN_STEP), freq=1000, duty_u16=0)
        self.hz = 0
        self.idle_ticks = 0
        self.homing = False
        self.homed = not config.HAS_HOME_SWITCH
        self.settle = 0      # steps still allowed while creeping up to the switch
        self.timer = Timer(0)
        self.timer.init(period=TICK_MS, mode=Timer.PERIODIC, callback=self._tick)

    # -- public ------------------------------------------------------------
    def top(self):
        return config.HAS_HOME_SWITCH and self.sw.value() == 0

    def position(self):
        return int(self.p.pos)

    def moving(self):
        return self.homing or self.settle > 0 or self.p.moving()

    def move_to(self, steps, speed=0, clamp=True):
        if clamp:
            steps = max(0, min(self.drop, int(steps)))
        vmax, acc = SPEEDS[speed]
        self.p.set(int(steps), vmax, acc)

    def jog(self, delta):
        self.move_to(max(0, self.position() + delta), 1, clamp=False)

    def stop(self):
        self.homing = False
        self.settle = 0
        self.p.set(int(self.p.pos), self.p.vmax, self.p.acc)

    def home(self):
        if not config.HAS_HOME_SWITCH:
            self.p.pos = 0.0
            self.homed = True
            return
        self.homed = False
        self.homing = True
        # wind up as far as a full drop plus margin, until the switch clicks
        self.p.pos = float(self.drop + 2000)
        self.p.set(0, config.HOME_SPEED, config.SLOW_ACCEL * 4)

    # -- 10 ms timer -------------------------------------------------------
    def _tick(self, _t):
        p = self.p
        going_up = p.target < p.pos or self.settle > 0
        if self.top() and going_up:
            self._at_top()
        elif self.settle > 0:
            # reached "0" by counting but the switch is not pressed yet: creep up
            p.vel = -config.HOME_SPEED
            self.settle -= config.HOME_SPEED * TICK_MS // 1000
            if self.settle <= 0:
                self.settle = 0
                p.vel = 0.0
                print("Top switch not found; check the line and switch")
        else:
            was = p.moving()
            p.step(TICK_MS / 1000)
            if was and not p.moving():
                if self.homing:
                    self.homing = False
                    print("Homing failed: switch never pressed")
                elif p.target == 0 and config.HAS_HOME_SWITCH and not self.top():
                    self.settle = SETTLE_STEPS
        self._output(p.vel)

    def _at_top(self):
        self.p.pos = 0.0
        self.p.vel = 0.0
        self.p.target = 0
        self.settle = 0
        if self.homing:
            self.homing = False
        self.homed = True

    def _output(self, vel):
        hz = int(abs(vel))
        if hz < MIN_HZ:
            if self.hz:
                self.pwm.duty_u16(0)
                self.hz = 0
            self.idle_ticks += 1
            if self.idle_ticks * TICK_MS > config.HOLD_MS:
                self.en.value(1)
            return
        self.idle_ticks = 0
        self.en.value(0)
        self.dir.value(config.DIR_DOWN if vel > 0 else 1 - config.DIR_DOWN)
        if not self.hz or abs(hz - self.hz) * 50 > self.hz:   # change >2%
            self.pwm.freq(hz)
            if not self.hz:
                self.pwm.duty_u16(32768)
            self.hz = hz
