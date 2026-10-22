# One LED strip for effects that need exact timing (lightning, the VU bar).
#
# mode "wled":  frames go to a WLED controller over Wi-Fi with WLED's realtime
#               UDP protocol (DNRGB, port 21324). WLED shows each frame at once
#               and goes back to its own preset a few seconds after the frames
#               stop, so the preset is the "between effects" look.
# mode "local": a WS2812 strip wired straight to a pin of this ESP32.
import socket

PORT = 21324
PER_PACKET = 489          # LEDs per DNRGB packet


class Strip:
    def __init__(self, n, mode="wled", host="", pin=None, timeout_s=2, idle=(0, 0, 0)):
        self.n = n
        self.mode = mode
        self.timeout = timeout_s
        self.idle = idle          # local mode: colour between effects
        self.buf = bytearray(n * 3)
        self.addr = None
        self.host = ""
        if mode == "local":
            import neopixel
            from machine import Pin
            self.np = neopixel.NeoPixel(Pin(pin), n)
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.set_host(host)

    def set_host(self, host):
        self.host = host
        self.addr = None

    def _resolve(self):
        if self.addr is None and self.host:
            try:
                self.addr = socket.getaddrinfo(self.host, PORT)[0][-1]
            except Exception as e:
                print("WLED host not found:", self.host, e)
        return self.addr

    def set(self, i, rgb):
        j = i * 3
        self.buf[j] = min(255, max(0, int(rgb[0])))
        self.buf[j + 1] = min(255, max(0, int(rgb[1])))
        self.buf[j + 2] = min(255, max(0, int(rgb[2])))

    def fill(self, rgb):
        for i in range(self.n):
            self.set(i, rgb)

    def show(self):
        if self.mode == "local":
            b = self.buf
            for i in range(self.n):
                self.np[i] = (b[i * 3], b[i * 3 + 1], b[i * 3 + 2])
            self.np.write()
            return
        addr = self._resolve()
        if not addr:
            return
        for start in range(0, self.n, PER_PACKET):
            end = min(self.n, start + PER_PACKET)
            head = bytes((4, self.timeout, start >> 8, start & 0xFF))
            try:
                self.sock.sendto(head + self.buf[start * 3:end * 3], addr)
            except OSError as e:
                print("WLED send failed:", e)

    def release(self):
        """Effect over: WLED falls back to its preset by itself; a local strip shows the idle colour."""
        if self.mode == "local":
            self.fill(self.idle)
            self.show()
