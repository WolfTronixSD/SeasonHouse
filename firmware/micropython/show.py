# The show engine. A show is a list of steps such as ["MOVE", 1000, 0] that
# come from seasons.json (generated from the simulator, so both match). The
# engine runs one step at a time and never blocks: call tick() often.
from compat import ticks_ms, ticks_diff, ticks_add, randint, json

FAST, SLOW, MED = 0, 1, 2


def load_seasons(path="seasons.json"):
    with open(path) as f:
        return json.load(f)


class ShowEngine:
    def __init__(self, rig, seasons, clock=ticks_ms):
        self.rig = rig            # winch, sound, eyes, lights (see app.Rig)
        self.seasons = seasons    # list of season dicts
        self.clock = clock
        self.season = 0
        self.current = None       # id of the running show
        self.steps = None
        self.pc = 0
        self.wait_until = None
        self.wig = -1
        self.wig_base = 0
        self.wig_other = 0

    @property
    def S(self):
        return self.seasons[self.season]

    def set_season(self, sid):
        for i, s in enumerate(self.seasons):
            if s["id"] == sid:
                if i != self.season:
                    self.stop()
                    self.season = i
                return True
        return False

    def find(self, show_id):
        for sh in self.S["shows"]:
            if sh["id"] == show_id:
                return sh
        return None

    def start(self, show_id):
        sh = self.find(show_id)
        if sh is None or not self.rig.ready():
            return False
        self.current = show_id
        self.steps = sh["steps"]
        self.pc = 0
        self.wait_until = None
        self.wig = -1
        print("Show:", sh["label"])
        return True

    def stop(self):
        self.current = None
        self.steps = None
        self.rig.halt()

    def tick(self):
        if self.current is None:
            return
        rig = self.rig
        while True:
            if self.pc >= len(self.steps):
                self.current = None
                self.steps = None
                return
            st = self.steps[self.pc]
            op = st[0]
            a = st[1] if len(st) > 1 else 0
            b = st[2] if len(st) > 2 else 0
            if op == "MOVE":
                rig.move_to(rig.drop * a // 1000, b)
            elif op == "WAITMOVE":
                if rig.moving():
                    return
            elif op == "WAIT" or op == "RWAIT":
                now = self.clock()
                if self.wait_until is None:
                    self.wait_until = ticks_add(now, a if op == "WAIT" else randint(a, b))
                if ticks_diff(self.wait_until, now) > 0:
                    return
                self.wait_until = None
            elif op == "SND":
                rig.play(a)
            elif op == "SNDSTOP":
                rig.stop_sound()
            elif op == "EYES":
                rig.eyes(a)
            elif op == "WLED":
                rig.wled(a)
            elif op == "CHIT":
                rig.chitter(a)
            elif op == "WIGGLE":
                if rig.moving():
                    return
                if self.wig < 0:
                    # bounce between here and a bit lower (or higher at the bottom)
                    self.wig_base = rig.position()
                    lower = self.wig_base + b
                    self.wig_other = lower if lower <= rig.drop else self.wig_base - b
                    self.wig = a * 2
                if self.wig > 0:
                    rig.move_to(self.wig_other if self.wig % 2 == 0 else self.wig_base, FAST)
                    self.wig -= 1
                    return
                self.wig = -1
            self.pc += 1
