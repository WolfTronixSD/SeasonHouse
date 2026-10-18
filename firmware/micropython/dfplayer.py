# DFPlayer Mini over UART. Sound slot n of season k plays /<k+1>/<n>.mp3, that
# is /01/001.mp3 ... /05/008.mp3 on the SD card.
from machine import UART
import config


class DFPlayer:
    def __init__(self, volume):
        self.uart = UART(2, baudrate=9600, tx=config.PIN_MP3_TX, rx=config.PIN_MP3_RX)
        self.volume(volume)

    def _cmd(self, cmd, param=0):
        frame = bytearray([0x7E, 0xFF, 0x06, cmd, 0x00, (param >> 8) & 0xFF, param & 0xFF, 0, 0, 0xEF])
        csum = -sum(frame[1:7]) & 0xFFFF
        frame[7] = csum >> 8
        frame[8] = csum & 0xFF
        self.uart.write(frame)

    def play(self, folder, track):
        self._cmd(0x0F, (folder << 8) | track)

    def volume(self, v):
        self._cmd(0x06, max(0, min(30, v)))

    def stop(self):
        self._cmd(0x16)

    def loop(self, on=True):
        # repeat the track that is playing now (bubbling cauldron, rain...)
        self._cmd(0x19, 0 if on else 1)
