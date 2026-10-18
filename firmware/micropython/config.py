# SeasonHouse ceiling prop - all the knobs you are likely to change live here.

# ---- Wi-Fi ------------------------------------------------------------------
# The prop first tries to join your home Wi-Fi. If that fails it starts its own
# hotspot and the control page is at http://192.168.4.1 . Join WLED to the same
# hotspot so the prop can still drive the lights at an offline party.
WIFI_SSID = "YourHomeWiFi"
WIFI_PASSWORD = "YourPassword"
AP_SSID = "SeasonHouse-Prop"
AP_PASSWORD = "boo12345"          # min 8 characters
HOSTNAME = "spider"               # control page at http://spider.local

# ---- Wireless updates -------------------------------------------------------
# Needed to upload new code from the web page or tools/ota_push.py. Change it.
OTA_KEY = "change-me"

# ---- WLED -------------------------------------------------------------------
# Each season uses 4 WLED presets numbered season*10 + slot: Halloween 1-4,
# Christmas 11-14, Easter 21-24, Fall 31-34, Winter 41-44. See docs/SEASONS.md.
WLED_HOST = "192.168.1.50"

# ---- Pins (ESP32 DevKit v1) -------------------------------------------------
PIN_STEP = 26       # stepper driver STEP (A4988 / DRV8825 / TMC2208)
PIN_DIR = 27        # stepper driver DIR
PIN_EN = 25         # stepper driver ENABLE, active low
PIN_HOME_SW = 33    # microswitch at the top, to GND (internal pull-up)
PIN_PIR = 34        # HC-SR501 or LD2410 OUT
PIN_EYE_L = 18      # LED eyes, each through 100 ohm to GND
PIN_EYE_R = 19
PIN_BUZZER = 23     # passive piezo for "chitter" clicks
PIN_MP3_TX = 17     # ESP32 TX -> DFPlayer RX (through 1k)
PIN_MP3_RX = 16     # ESP32 RX <- DFPlayer TX
HAS_HOME_SWITCH = True   # False: wind the prop fully up by hand before power-on

# ---- Motion -----------------------------------------------------------------
# Full steps. With a 30 mm spool one turn = ~94 mm = 200 steps, so 3200 = ~1.5 m.
DROP_STEPS = 3200
FAST_SPEED = 2000   # steps/s for the drop (~600 rpm)
FAST_ACCEL = 20000  # steps/s^2
SLOW_SPEED = 250
SLOW_ACCEL = 600
HOME_SPEED = 400
DIR_DOWN = 1        # flip to 0 if the prop winds up when it should go down
HOLD_MS = 1500      # keep the motor powered this long after a move

# ---- Behaviour --------------------------------------------------------------
MOTION_COOLDOWN_MS = 20000
PARTY_MIN_MS = 60000
PARTY_MAX_MS = 240000
DEFAULT_VOLUME = 25   # 0..30
