# Small shims so the same code runs on MicroPython and, for tests, on a PC.
try:
    from time import ticks_ms, ticks_diff, ticks_add
except ImportError:
    import time

    def ticks_ms():
        return int(time.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b

    def ticks_add(a, b):
        return a + b

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

if hasattr(asyncio, "sleep_ms"):
    sleep_ms = asyncio.sleep_ms
else:
    async def sleep_ms(ms):
        await asyncio.sleep(ms / 1000)

try:
    import ujson as json
except ImportError:
    import json

try:
    from os import urandom

    def randint(lo, hi):
        # inclusive, like random.randint
        span = hi - lo + 1
        return lo + int.from_bytes(urandom(4), "little") % span
except ImportError:
    from random import randint
