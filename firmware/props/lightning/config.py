# Lightning Window - all the knobs you are likely to change live here.

# ---- Wi-Fi (same as the other props) -----------------------------------------
WIFI_SSID = "YourHomeWiFi"
WIFI_PASSWORD = "YourPassword"
AP_SSID = "SeasonHouse-Storm"
AP_PASSWORD = "boo12345"
HOSTNAME = "storm"                # control page at http://storm.local
OTA_KEY = "change-me"

# ---- The strip behind the curtain --------------------------------------------
# "wled":  the strip runs WLED; flashes are streamed to it live (give WLED a dim
#          blue "moonlight" preset as its default look between strikes).
# "local": WS2812 strip on PIN_STRIP of this ESP32, no WLED needed.
LED_MODE = "wled"
WLED_HOST = "192.168.1.51"        # use the IP address, not a .local name
STRIP_LEDS = 60
PIN_STRIP = 4
MOONLIGHT = (0, 2, 10)            # local mode: colour between strikes
FLASH_COLOR = (200, 215, 255)     # bluish white

# ---- Pins (ESP32 DevKit v1) --------------------------------------------------
PIN_PIR = 34          # motion sensor OUT
PIN_SILHOUETTE = 25   # MOSFET for the light OUTSIDE behind the cut-out (high = on)
PIN_MP3_TX = 17       # ESP32 TX -> DFPlayer RX (through 1k)
PIN_MP3_RX = 16

# ---- The storm ----------------------------------------------------------------
SILHOUETTE_EVERY = 10             # every 10th strike shows the man with the axe
THUNDER_DELAY_MS = (1000, 3000)   # flash first, thunder 1-3 s later
CLOSE_MS = 1600                   # thunder sooner than this = close crack
# seconds between strikes in auto-storm mode, per intensity
STORM_GAPS = {1: (25, 60), 2: (8, 25), 3: (3, 9)}
MOTION_COOLDOWN_MS = 15000
DEFAULT_VOLUME = 26

DEFAULT_SETTINGS = {"vol": DEFAULT_VOLUME, "armed": True, "auto": True, "level": 2,
                    "every": SILHOUETTE_EVERY, "wled": WLED_HOST, "strikes": 0}
