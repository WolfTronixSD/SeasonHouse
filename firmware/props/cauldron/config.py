# Cauldron of Doom - all the knobs you are likely to change live here.

# ---- Wi-Fi (same as the other props) -----------------------------------------
WIFI_SSID = "YourHomeWiFi"
WIFI_PASSWORD = "YourPassword"
AP_SSID = "SeasonHouse-Cauldron"
AP_PASSWORD = "boo12345"
HOSTNAME = "cauldron"             # control page at http://cauldron.local
OTA_KEY = "change-me"

# ---- WLED under the cauldron ---------------------------------------------------
# Presets WLED_BASE+1 .. +4: 1 green bubbling (idle), 2 blood red (scare),
# 3 white flicker (spell), 4 off. With WLED_BASE = 60 that is 61-64.
WLED_HOST = "192.168.1.53"
WLED_BASE = 60

# ---- Pins (ESP32 DevKit v1) --------------------------------------------------
PIN_SERVO = 13        # MG996R signal (servo on its own 5-6 V supply, common GND)
PIN_MIST = 26         # MOSFET / relay for the ultrasonic mist maker (high = on)
PIN_PIR = 34          # motion sensor OUT
PIN_WATER = 35        # float switch to GND when the water is OK (optional)
HAS_WATER_SWITCH = False
PIN_MP3_TX = 17
PIN_MP3_RX = 16

# ---- The hand -------------------------------------------------------------------
HAND_DOWN = 10        # servo angle with the hand hidden under the fog
HAND_UP = 150         # servo angle with the hand reaching out
HAND_SPEEDS = (240, 35, 90)   # degrees/s for fast, slow, medium moves

# ---- Fog ----------------------------------------------------------------------
FOG_CYCLE_ON_MS = 20000       # "on and off" mode: fog this long...
FOG_CYCLE_OFF_MS = 40000      # ...then rest this long
FOG_MAX_ON_MS = 120000        # never run longer than this without a break
FOG_REST_MS = 20000

# ---- Behaviour --------------------------------------------------------------
MOTION_COOLDOWN_MS = 20000
PARTY_MIN_MS = 60000
PARTY_MAX_MS = 180000
DEFAULT_VOLUME = 24

DEFAULT_SETTINGS = {"vol": DEFAULT_VOLUME, "armed": True, "fog": "cycle", "bubbling": True,
                    "wled": WLED_HOST, "hand_down": HAND_DOWN, "hand_up": HAND_UP}
