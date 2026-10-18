# The storm: lightning flicker on the strip, thunder from the MP3 1-3 s later
# (further away = later and quieter), and every Nth strike the outside light
# behind the cut-out flashes so a man with an axe appears on the curtain.
# Pure logic, driven by update() with a clock, so it can be tested on a PC.
from compat import ticks_ms, ticks_diff, ticks_add, randint
import config

# SD card folder 01: 001-003 close cracks, 004-006 distant rolling thunder
CLOSE_TRACKS = (1, 2, 3)
FAR_TRACKS = (4, 5, 6)


def flash_pattern(rnd=randint):
    """[(start_ms, length_ms, level 0..1)]: dim leader flickers, the main
    stroke, then a few fading restrikes - like a real bolt."""
    out = []
    t = 0
    for _ in range(rnd(1, 3)):
        on = rnd(20, 50)
        out.append((t, on, rnd(15, 45) / 100))
        t += on + rnd(30, 110)
    main = rnd(70, 130)
    out.append((t, main, 1.0))
    t += main
    level = 0.85
    for _ in range(rnd(1, 3)):
        t += rnd(40, 140)
        on = rnd(30, 80)
        out.append((t, on, level))
        t += on
        level *= 0.6
    return out


class Storm:
    def __init__(self, strip, mp3, silhouette, volume, clock=ticks_ms, rnd=randint):
        self.strip = strip
        self.mp3 = mp3
        self.sil = silhouette          # machine.Pin or anything with value()
        self.volume = volume
        self.clock = clock
        self.rnd = rnd
        self.count = 0
        self.every = config.SILHOUETTE_EVERY
        self.auto = False
        self.level = 2
        self.flash = None              # (t0, pattern, centre, silhouette)
        self.thunder = None            # (due, track, volume)
        self.next_auto = None
        self.lit = False
        self.last = None               # info about the last strike, for the page

    # ---------------------------------------------------------- control
    def strike(self, close=False, silhouette=None):
        """Start a strike now. Returns its details."""
        now = self.clock()
        self.count += 1
        if silhouette is None:
            silhouette = self.every > 0 and self.count % self.every == 0
        lo, hi = config.THUNDER_DELAY_MS
        delay = self.rnd(lo, lo + (hi - lo) // 4) if close or silhouette else self.rnd(lo, hi)
        near = delay < config.CLOSE_MS
        track = (CLOSE_TRACKS if near else FAR_TRACKS)[self.rnd(0, 2)]
        # further away = quieter, down to 8 steps below the set volume
        vol = max(0, self.volume - (delay - lo) * 8 // max(1, hi - lo))
        self.flash = (now, flash_pattern(self.rnd), self.rnd(0, 100) / 100, silhouette)
        self.thunder = (ticks_add(now, delay), track, vol)
        self.last = {"n": self.count, "delay": delay, "near": near, "silhouette": silhouette, "track": track}
        return self.last

    def set_auto(self, on, level=None):
        self.auto = on
        if level:
            self.level = max(1, min(3, level))
        self.next_auto = ticks_add(self.clock(), 2000) if on else None

    def stop(self):
        self.flash = None
        self.thunder = None
        self._dark()
        self.mp3.stop()

    def busy(self):
        return self.flash is not None or self.thunder is not None

    # ---------------------------------------------------------- every few ms
    def update(self):
        now = self.clock()
        if self.flash:
            self._render(now)
        if self.thunder and ticks_diff(now, self.thunder[0]) >= 0:
            _, track, vol = self.thunder
            self.thunder = None
            self.mp3.volume(vol)
            self.mp3.play(1, track)
        if self.auto and not self.busy() and self.next_auto is not None and ticks_diff(now, self.next_auto) >= 0:
            self.strike()
            lo, hi = config.STORM_GAPS[self.level]
            self.next_auto = ticks_add(now, self.rnd(lo, hi) * 1000)

    def _render(self, now):
        t0, pattern, centre, sil = self.flash
        t = ticks_diff(now, t0)
        level = 0.0
        for start, length, lv in pattern:
            if start <= t < start + length:
                level = lv
        end = pattern[-1][0] + pattern[-1][1]
        if t >= end + 150:
            self.flash = None
            self._dark()
            return
        if t >= end:                                   # afterglow
            level = 0.25 * (1 - (t - end) / 150)
        if sil:
            # the outside light makes the shadow; keep the strip low so it stays crisp
            self.sil.value(1 if level >= 0.5 else 0)
            level *= 0.25
        self._paint(level, centre)

    def _paint(self, level, centre):
        s = self.strip
        if level <= 0:
            if self.lit:
                self._dark()
            return
        n = s.n
        r, g, b = config.FLASH_COLOR
        for i in range(n):
            # brightest where the bolt "is", so each strike looks different
            d = (i / max(1, n - 1)) - centre
            k = level * (0.55 + 0.45 / (1 + 30 * d * d))
            s.set(i, (r * k, g * k, b * k))
        s.show()
        self.lit = True

    def _dark(self):
        self.sil.value(0)
        if self.lit:
            self.strip.fill((0, 0, 0))
            self.strip.show()
            self.strip.release()
        self.lit = False
