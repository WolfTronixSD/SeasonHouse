# The Scream-o-Meter game. feed() gets a sound level every ~30 ms; the meter
# drives the VU bar, the dot matrix and the MP3, runs the "3, 2, 1, SCREAM!"
# rounds and keeps the leaderboard. Pure logic with a clock, tested on a PC.
from compat import ticks_ms, ticks_diff
import config

# SD card folder 01
SND_COUNTDOWN, SND_RECORD, SND_WEAK, SND_GOOD, SND_HUGE, SND_TRIGGER = 1, 2, 3, 4, 5, 6


class Meter:
    def __init__(self, strip, matrix, mp3, board, clock=ticks_ms):
        self.strip = strip
        self.dm = matrix
        self.mp3 = mp3
        self.board = board            # list of {"name", "db"}, best first
        self.clock = clock
        self.phase = "idle"
        self.t0 = clock()
        self.db = 0.0                 # smoothed level now
        self.peak = 0.0               # peak hold (idle) / best this round
        self.peak_t = self.t0
        self.score = 0
        self.who = ""
        self.record = False
        self.guests = 0
        self.lo, self.hi = config.VU_RANGE
        self.on_trigger = None        # called with the level when someone screams loud enough
        self.trigger_db = config.TRIGGER_DB
        self.trigger_on = True
        self.last_trigger = self.t0 - config.TRIGGER_COOLDOWN_MS
        self.changed = False          # leaderboard needs saving

    # --------------------------------------------------------------- input
    def feed(self, db):
        now = self.clock()
        # fast attack, slower release, like a real VU meter
        self.db = db if db > self.db else self.db * 0.8 + db * 0.2
        if self.phase == "listen":
            self.peak = max(self.peak, db)
        elif db >= self.peak or ticks_diff(now, self.peak_t) > 1500:
            self.peak, self.peak_t = db, now
        if (self.trigger_on and self.on_trigger and db >= self.trigger_db
                and ticks_diff(now, self.last_trigger) > config.TRIGGER_COOLDOWN_MS):
            self.last_trigger = now
            self.on_trigger(db)

    # --------------------------------------------------------------- rounds
    def start(self, name=""):
        if self.phase in ("countdown", "listen"):
            return False
        self.guests += 1
        self.who = (name or "Guest %d" % self.guests)[:12]
        self.phase = "countdown"
        self.t0 = self.clock()
        self.peak = 0.0
        self.record = False
        self.mp3.play(1, SND_COUNTDOWN)
        return True

    def stop(self):
        self.phase = "idle"
        self.mp3.stop()

    def clear(self):
        del self.board[:]
        self.changed = True

    def count(self):
        left = config.COUNTDOWN_MS - ticks_diff(self.clock(), self.t0)
        return max(1, (left + 999) // 1000)

    def update(self):
        now = self.clock()
        t = ticks_diff(now, self.t0)
        if self.phase == "countdown":
            self.dm.show(str(self.count()))
            if t >= config.COUNTDOWN_MS:
                self.phase, self.t0, self.peak = "listen", now, 0.0
                self.dm.show("SCREAM!")
        elif self.phase == "listen":
            if t >= config.LISTEN_MS:
                self._finish(now)
        elif self.phase == "result":
            self.dm.show("%d DB" % self.score)
            if t >= config.RESULT_MS:
                self.phase = "idle"
        else:
            best = self.board[0]["db"] if self.board else 0
            self.dm.show("%d" % self.db if self.db >= self.lo else ("BEST %d" % best if best else "SCREAM?"))
        self.dm.tick()
        self._vu()

    def _finish(self, now):
        self.score = int(round(self.peak))
        self.phase, self.t0 = "result", now
        self.dm.show("%d DB" % self.score)
        best = self.board[0]["db"] if self.board else 0
        self.record = self.score > best
        self.board.append({"name": self.who, "db": self.score})
        self.board.sort(key=lambda e: -e["db"])
        del self.board[config.BOARD_SIZE:]
        self.changed = True
        if self.record:
            self.mp3.play(1, SND_RECORD)
        elif self.score < 85:
            self.mp3.play(1, SND_WEAK)
        elif self.score < 100:
            self.mp3.play(1, SND_GOOD)
        else:
            self.mp3.play(1, SND_HUGE)

    def frac(self, db):
        return max(0.0, min(1.0, (db - self.lo) / (self.hi - self.lo)))

    def _vu(self):
        s = self.strip
        n = s.n
        lit = self.frac(self.db) * n
        peak_i = int(self.frac(self.peak) * (n - 1))
        flash = self.phase == "result" and self.record and (ticks_diff(self.clock(), self.t0) // 150) % 2
        for i in range(n):
            k = i / max(1, n - 1)
            # green at the bottom, yellow in the middle, red at the top
            col = (int(510 * k) if k < 0.5 else 255, 255 if k < 0.5 else int(510 * (1 - k)), 0)
            if flash:
                s.set(i, (255, 255, 255))
            elif i < lit:
                s.set(i, col)
            elif i == peak_i and self.peak >= self.lo:
                s.set(i, (255, 255, 255))
            else:
                s.set(i, (col[0] // 40, col[1] // 40, 0))
        s.show()
