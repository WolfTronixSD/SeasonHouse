# MAX7219 dot-matrix modules (the common 4-in-1 "FC-16" boards), 8 rows x
# 8 columns per module. Draws text in a 5x7 font, scrolling it when it is too
# wide. If text comes out mirrored or upside down, flip FLIP_X / FLIP_Y.
from machine import Pin, SPI

# 5x7 font, one byte per column, bit 0 = top row
FONT = {
    " ": b"\x00\x00\x00", "!": b"\x5f", "?": b"\x02\x01\x51\x09\x06", "-": b"\x08\x08\x08",
    ".": b"\x60\x60", ":": b"\x36\x36", "'": b"\x05\x03", "#": b"\x14\x7f\x14\x7f\x14",
    "0": b"\x3e\x51\x49\x45\x3e", "1": b"\x00\x42\x7f\x40\x00", "2": b"\x42\x61\x51\x49\x46",
    "3": b"\x21\x41\x45\x4b\x31", "4": b"\x18\x14\x12\x7f\x10", "5": b"\x27\x45\x45\x45\x39",
    "6": b"\x3c\x4a\x49\x49\x30", "7": b"\x01\x71\x09\x05\x03", "8": b"\x36\x49\x49\x49\x36",
    "9": b"\x06\x49\x49\x29\x1e",
    "A": b"\x7e\x11\x11\x11\x7e", "B": b"\x7f\x49\x49\x49\x36", "C": b"\x3e\x41\x41\x41\x22",
    "D": b"\x7f\x41\x41\x22\x1c", "E": b"\x7f\x49\x49\x49\x41", "F": b"\x7f\x09\x09\x01\x01",
    "G": b"\x3e\x41\x41\x51\x32", "H": b"\x7f\x08\x08\x08\x7f", "I": b"\x41\x7f\x41",
    "J": b"\x20\x40\x41\x3f\x01", "K": b"\x7f\x08\x14\x22\x41", "L": b"\x7f\x40\x40\x40\x40",
    "M": b"\x7f\x02\x04\x02\x7f", "N": b"\x7f\x04\x08\x10\x7f", "O": b"\x3e\x41\x41\x41\x3e",
    "P": b"\x7f\x09\x09\x09\x06", "Q": b"\x3e\x41\x51\x21\x5e", "R": b"\x7f\x09\x19\x29\x46",
    "S": b"\x46\x49\x49\x49\x31", "T": b"\x01\x01\x7f\x01\x01", "U": b"\x3f\x40\x40\x40\x3f",
    "V": b"\x1f\x20\x40\x20\x1f", "W": b"\x7f\x20\x18\x20\x7f", "X": b"\x63\x14\x08\x14\x63",
    "Y": b"\x03\x04\x78\x04\x03", "Z": b"\x61\x51\x49\x45\x43",
}


def render(text):
    """Text -> list of column bytes, one blank column between letters."""
    cols = bytearray()
    for ch in text.upper():
        cols += FONT.get(ch, FONT["?"]) + b"\x00"
    return cols[:-1] if cols else cols


class Matrix:
    def __init__(self, din, clk, cs, modules=4, intensity=4, flip_x=False, flip_y=False):
        self.spi = SPI(2, baudrate=10_000_000, polarity=0, phase=0, sck=Pin(clk), mosi=Pin(din))
        self.cs = Pin(cs, Pin.OUT, value=1)
        self.m = modules
        self.w = modules * 8
        self.flip_x, self.flip_y = flip_x, flip_y
        self.cols = bytearray(self.w)
        self.text = ""
        self.strip = b""
        self.offset = 0
        for reg, val in ((0x0F, 0), (0x09, 0), (0x0B, 7), (0x0A, intensity), (0x0C, 1)):
            self._all(reg, val)
        self.show("")

    def _all(self, reg, val):
        self.cs(0)
        for _ in range(self.m):
            self.spi.write(bytes((reg, val)))
        self.cs(1)

    def show(self, text):
        """Centre short text; longer text scrolls (call tick() to move it)."""
        if text == self.text:
            return
        self.text = text
        self.strip = render(text)
        self.offset = -self.w if len(self.strip) > self.w else 0
        self._draw()

    def tick(self):
        if len(self.strip) > self.w:
            self.offset += 1
            if self.offset > len(self.strip):
                self.offset = -self.w
            self._draw()

    def _draw(self):
        s = self.strip
        if len(s) <= self.w:
            pad = (self.w - len(s)) // 2
            for x in range(self.w):
                self.cols[x] = s[x - pad] if 0 <= x - pad < len(s) else 0
        else:
            for x in range(self.w):
                i = x + self.offset
                self.cols[x] = s[i] if 0 <= i < len(s) else 0
        self._flush()

    def _flush(self):
        for row in range(8):
            r = 7 - row if self.flip_y else row
            self.cs(0)
            for mod in range(self.m - 1, -1, -1):      # last module first in the chain
                byte = 0
                for bit in range(8):
                    x = mod * 8 + (7 - bit if not self.flip_x else bit)
                    if self.cols[x] >> r & 1:
                        byte |= 1 << bit
                self.spi.write(bytes((row + 1, byte)))
            self.cs(1)
