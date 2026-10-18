# Settings changed from the web page, kept in settings.json across reboots.
from compat import json
import config

DEFAULTS = {"season": "halloween", "drop": config.DROP_STEPS, "vol": config.DEFAULT_VOLUME,
            "armed": True, "wled": config.WLED_HOST}


def load():
    s = dict(DEFAULTS)
    try:
        with open("settings.json") as f:
            s.update(json.load(f))
    except (OSError, ValueError):
        pass
    return s


def save(s):
    with open("settings.json", "w") as f:
        json.dump(s, f)
