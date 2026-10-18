# The rat's runs, in the same step language as the ceiling prop's shows.
# MOVE positions are 0 = in its hole ... 1000 = the far end of the track.
F, S, M = 0, 1, 2   # fast, slow, medium

SOUNDS = ["Squeak", "Scurrying claws", "Angry squeal", "Hiss", "Eek! (rat)", "Rat swarm"]

SHOWS = [
    {"id": "dash", "label": "Ankle Dash", "hint": "straight across, squeaking", "steps": [
        ["SND", 2], ["MOVE", 1000, F], ["WAITMOVE"], ["SND", 1], ["WAIT", 1200],
        ["MOVE", 0, M], ["WAITMOVE"]]},
    {"id": "fakeout", "label": "Fake-out", "hint": "peeks out, hides, then runs for it", "steps": [
        ["MOVE", 180, F], ["WAITMOVE"], ["SND", 1], ["WAIT", 700], ["MOVE", 0, F], ["WAITMOVE"],
        ["RWAIT", 1200, 2500], ["SND", 3], ["MOVE", 1000, F], ["WAITMOVE"], ["WAIT", 900], ["MOVE", 0, M], ["WAITMOVE"]]},
    {"id": "stalk", "label": "Stalker", "hint": "creeps closer, freezes, then bolts", "steps": [
        ["MOVE", 350, S], ["WAITMOVE"], ["SND", 4], ["RWAIT", 800, 2000], ["MOVE", 450, S], ["WAITMOVE"],
        ["WAIT", 600], ["SND", 2], ["MOVE", 1000, F], ["WAITMOVE"], ["WAIT", 700], ["MOVE", 0, F], ["WAITMOVE"]]},
    {"id": "nibble", "label": "Nibbler", "hint": "runs halfway and twitches at your feet", "steps": [
        ["SND", 2], ["MOVE", 550, F], ["WAITMOVE"], ["WIGGLE", 6, 60], ["SND", 5], ["WAIT", 500],
        ["MOVE", 1000, F], ["WAITMOVE"], ["WAIT", 800], ["MOVE", 0, M], ["WAITMOVE"]]},
    {"id": "laps", "label": "Rat Race", "hint": "back and forth like it's lost", "steps": [
        ["SND", 6], ["MOVE", 1000, F], ["WAITMOVE"], ["MOVE", 300, F], ["WAITMOVE"], ["MOVE", 850, F], ["WAITMOVE"],
        ["SND", 3], ["MOVE", 0, F], ["WAITMOVE"]]},
]
SCARY = ["dash", "fakeout", "nibble"]
