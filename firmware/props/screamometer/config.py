# Scream-o-Meter - all the knobs you are likely to change live here.

# ---- Wi-Fi (same as the other props) -----------------------------------------
WIFI_SSID = "YourHomeWiFi"
WIFI_PASSWORD = "YourPassword"
AP_SSID = "SeasonHouse-Scream"
AP_PASSWORD = "boo12345"
HOSTNAME = "scream"               # control page at http://scream.local
OTA_KEY = "change-me"

# ---- VU bar up the wall -------------------------------------------------------
LED_MODE = "wled"                 # or "local" for a WS2812 strip on PIN_STRIP
WLED_HOST = "192.168.1.52"        # use the IP address, not a .local name
STRIP_LEDS = 60
PIN_STRIP = 4
VU_RANGE = (55, 115)              # dB at the bottom and the top of the bar

# ---- Pins (ESP32 DevKit v1) --------------------------------------------------
PIN_MIC_SCK = 14      # INMP441 SCK
PIN_MIC_WS = 15       # INMP441 WS
PIN_MIC_SD = 32       # INMP441 SD   (L/R to GND, VDD 3.3 V)
PIN_DM_DIN = 23       # MAX7219 dot matrix DIN
PIN_DM_CLK = 18       # MAX7219 CLK
PIN_DM_CS = 5         # MAX7219 CS
DM_MODULES = 4
DM_FLIP_X = False     # set True if the text is mirrored
DM_FLIP_Y = False     # set True if the text is upside down
PIN_BUTTON = 27       # big "SCREAM" arcade button to GND (optional)
PIN_MP3_TX = 17
PIN_MP3_RX = 16

# ---- The game ------------------------------------------------------------------
MIC_OFFSET_DB = 120   # INMP441: dBFS + 120 = dB SPL. Trim against a phone meter.
COUNTDOWN_MS = 3000   # "3, 2, 1" (matches sound 001)
LISTEN_MS = 3000      # how long the scream is measured
RESULT_MS = 8000
BOARD_SIZE = 10

# A scream this loud sets off the other props (any time, not only in a round).
TRIGGER_DB = 100
TRIGGER_COOLDOWN_MS = 20000
TRIGGER_URLS = [
    "http://spider.local/api/run?show=drop",
    # "http://storm.local/api/strike?kind=close",
    # "http://cauldron.local/api/run?show=rise",
]
DEFAULT_VOLUME = 26

DEFAULT_SETTINGS = {"vol": DEFAULT_VOLUME, "board": [], "trigger": True, "trigger_db": TRIGGER_DB,
                    "cal": MIC_OFFSET_DB, "wled": WLED_HOST}
