# The cauldron's scares, in the same step language as the ceiling prop's
# shows. MOVE positions are 0 = hand hidden ... 1000 = hand fully up.
F, S, M = 0, 1, 2   # fast, slow, medium

SOUNDS = ["Bubbling (loops)", "Who disturbs my stew?", "Witch cackle", "Lovely soup!", "Double, double", "Big gurgle"]

SHOWS = [
    {"id": "rise", "label": "The Hand", "hint": "fog, red glow, a hand rises and grabs", "steps": [
        ["WLED", 2], ["FOG", 1], ["SND", 2], ["WAIT", 900],
        ["MOVE", 1000, S], ["WAITMOVE"], ["SND", 3], ["WIGGLE", 4, 160], ["WAIT", 1500],
        ["MOVE", 0, M], ["WAITMOVE"], ["FOG", 0], ["WLED", 1]]},
    {"id": "peek", "label": "Peekaboo", "hint": "fingers creep over the rim", "steps": [
        ["WLED", 2], ["MOVE", 450, S], ["WAITMOVE"], ["WIGGLE", 3, 90], ["SND", 4], ["WAIT", 1800],
        ["MOVE", 0, F], ["WAITMOVE"], ["WLED", 1]]},
    {"id": "grab", "label": "Snatch", "hint": "the hand shoots out, no warning", "steps": [
        ["SND", 6], ["WLED", 2], ["MOVE", 1000, F], ["WAITMOVE"], ["WIGGLE", 2, 200], ["SND", 3], ["WAIT", 1200],
        ["MOVE", 0, M], ["WAITMOVE"], ["WLED", 1]]},
    {"id": "spell", "label": "Toil and Trouble", "hint": "the witch chants, fog pours out", "steps": [
        ["WLED", 3], ["FOG", 1], ["SND", 5], ["WAIT", 2500], ["MOVE", 700, M], ["WAITMOVE"],
        ["WIGGLE", 6, 90], ["MOVE", 0, S], ["WAITMOVE"], ["WAIT", 1500], ["FOG", 0], ["WLED", 1]]},
    {"id": "cackle", "label": "Cackle", "hint": "red flash and a witch's laugh", "steps": [
        ["WLED", 2], ["SND", 3], ["FOG", 1], ["WAIT", 4000], ["FOG", 0], ["WLED", 1]]},
]
SCARY = ["rise", "grab", "spell"]
