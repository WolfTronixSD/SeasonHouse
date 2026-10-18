# INMP441 I2S microphone. read_db() gives the loudness of the last ~30 ms as
# an approximate sound level in dB SPL (the INMP441 reads -26 dBFS at 94 dB SPL,
# so SPL = dBFS + 120; trim MIC_OFFSET_DB in config.py with a phone sound meter).
import math
from compat import asyncio

try:
    from micropython import const
except ImportError:
    def const(x):
        return x

FULL = const(2147483648)


def level_db(samples, offset=120, step=2):
    """samples: 32-bit signed ints, 24-bit audio in the top bits."""
    n = 0
    total = 0
    for i in range(0, len(samples), step):
        total += samples[i]
        n += 1
    if not n:
        return 0
    mean = total / n
    sq = 0.0
    for i in range(0, len(samples), step):
        v = (samples[i] - mean) / FULL
        sq += v * v
    rms = math.sqrt(sq / n)
    if rms < 1e-7:
        return 0
    return max(0, 20 * math.log10(rms) + offset)


class Mic:
    def __init__(self, sck, ws, sd, offset=120, rate=16000):
        from machine import I2S, Pin
        self.i2s = I2S(0, sck=Pin(sck), ws=Pin(ws), sd=Pin(sd), mode=I2S.RX,
                       bits=32, format=I2S.MONO, rate=rate, ibuf=8192)
        self.buf = bytearray(2048)                 # 512 samples = 32 ms
        self.reader = asyncio.StreamReader(self.i2s)
        self.offset = offset

    async def read_db(self):
        import array
        n = await self.reader.readinto(self.buf)
        return level_db(array.array("i", self.buf[:n - n % 4]), self.offset)
