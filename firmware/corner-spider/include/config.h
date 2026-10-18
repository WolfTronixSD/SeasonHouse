#pragma once
// ============================================================================
//  Corner Spider - all the knobs you are likely to change live here.
// ============================================================================

// ---- Wi-Fi ------------------------------------------------------------------
// The spider first tries to join your home Wi-Fi. If that fails (party at a
// friend's garage, no router...) it starts its own hotspot instead, and the
// control page is at http://192.168.4.1 . Point WLED at the same hotspot so
// the spider can still trigger the lights.
#define WIFI_SSID        "YourHomeWiFi"
#define WIFI_PASSWORD    "YourPassword"
#define AP_SSID          "SeasonHouse-Spider"
#define AP_PASSWORD      "boo12345"        // min 8 chars
#define MDNS_NAME        "spider"          // http://spider.local

// ---- WLED -------------------------------------------------------------------
// IP of your WLED controller. Save these presets in WLED (Presets tab):
//   1 = ambient (dim purple/orange breathe)   2 = lightning / strobe
//   3 = blood red solid                       4 = party / rainbow
#define WLED_HOST        "192.168.1.50"
#define WLED_PS_AMBIENT  1
#define WLED_PS_LIGHTNING 2
#define WLED_PS_RED      3
#define WLED_PS_PARTY    4

// ---- Pins (ESP32 DevKit v1) -------------------------------------------------
// Stepper driver: A4988 / DRV8825 / TMC2208 in STEP/DIR mode (NEMA17).
#define PIN_STEP         26
#define PIN_DIR          27
#define PIN_EN           25    // driver ENABLE (active LOW). Released when idle so it runs cool.
#define PIN_HOME_SW      33    // microswitch at the top, to GND (internal pull-up). Pressed = spider home.
#define PIN_PIR          34    // HC-SR501 OUT (input-only pin is fine)
#define PIN_EYE_L        18    // red LED eyes via NPN/MOSFET or direct with 220R
#define PIN_EYE_R        19
#define PIN_BUZZER       23    // passive piezo for "chitter" clicks
#define PIN_MP3_RX       16    // ESP32 RX2  <- DFPlayer TX
#define PIN_MP3_TX       17    // ESP32 TX2  -> DFPlayer RX (through 1k resistor)

// Set to 0 if you have no top limit switch. The spider must then be wound
// fully up by hand before power-on, because boot position = home.
#define HAS_HOME_SWITCH  1

// A 28BYJ-48 is too slow for a real "drop" (about 15 rpm). Use a NEMA17 with a
// STEP/DIR driver for the winch; save the 28BYJ-48s for slow props.

// ---- Motion -----------------------------------------------------------------
// Steps from "home" (top) to fully dropped. Measure once: use the web page's
// "Jog down" until the spider is at face height, read the position, put it here.
// Full steps (A4988 MS pins open). With a 30 mm spool one turn = ~94 mm of
// line = 200 steps, so 3200 steps = 16 turns = ~1.5 m.
#define DROP_STEPS       3200L
#define HOME_SPEED       500      // steps/s while homing
#define FAST_SPEED       2000     // drop speed (~600 rpm, ~0.9 m/s on a 30 mm spool)
#define FAST_ACCEL       20000
#define SLOW_SPEED       250      // creeping speed
#define SLOW_ACCEL       600
#define DIR_DOWN         1        // flip to -1 if the spider winds up instead of down
#define HOLD_MS          1500     // keep coils energised this long after a move
#define HOME_EXTRA_STEPS 2000L   // homing winds up at most (drop length + this) before giving up

// ---- Behaviour --------------------------------------------------------------
#define MOTION_COOLDOWN_MS   20000UL   // min time between motion-triggered scares
#define DEFAULT_VOLUME       25        // 0..30

// ---- Sound tracks on the SD card (folder /mp3, files 0001.mp3 ...) ---------
#define TRK_HISS         1   // angry hiss
#define TRK_SCREAM       2   // scream / sting
#define TRK_LAUGH        3   // evil laugh
#define TRK_CREAK        4   // creaky rope
#define TRK_HEARTBEAT    5   // heartbeat loop
#define TRK_BOING        6   // cartoon boing (funny fake-out)
#define TRK_DISCO        7   // "Spider Disco" music
#define TRK_HELLO        8   // squeaky "hiii!" (funny)
