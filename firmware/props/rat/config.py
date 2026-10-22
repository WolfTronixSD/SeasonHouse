# Rat Express - all the knobs you are likely to change live here.

# ---- Wi-Fi (same as the other props) -----------------------------------------
WIFI_SSID = "YourHomeWiFi"
WIFI_PASSWORD = "YourPassword"
AP_SSID = "SeasonHouse-Rat"
AP_PASSWORD = "boo12345"
HOSTNAME = "rat"                  # control page at http://rat.local
OTA_KEY = "change-me"

# ---- Pins (ESP32 DevKit v1), same wiring as the ceiling prop ------------------
PIN_STEP = 26
PIN_DIR = 27
PIN_EN = 25
PIN_HOME_SW = 33    # reed switch at the rat's hole; a magnet on the line closes it
PIN_PIR = 34
PIN_MP3_TX = 17
PIN_MP3_RX = 16
HAS_HOME_SWITCH = True   # False: park the rat at its hole by hand before power-on

# ---- Motion -------------------------------------------------------------------
# A 20 mm pulley moves the line ~63 mm per 200 steps, so 6000 steps = ~1.9 m.
DROP_STEPS = 6000   # track length: from the hole to the far end
FAST_SPEED = 2600   # steps/s, ~0.8 m/s: a rat in a hurry
FAST_ACCEL = 30000  # rats don't ease in
SLOW_SPEED = 300
SLOW_ACCEL = 1500
HOME_SPEED = 500
DIR_DOWN = 1        # flip to 0 if the rat runs the wrong way
HOLD_MS = 800

# ---- Behaviour --------------------------------------------------------------
MOTION_COOLDOWN_MS = 12000
PARTY_MIN_MS = 45000
PARTY_MAX_MS = 150000
DEFAULT_VOLUME = 26

DEFAULT_SETTINGS = {"len": DROP_STEPS, "vol": DEFAULT_VOLUME, "armed": True}
