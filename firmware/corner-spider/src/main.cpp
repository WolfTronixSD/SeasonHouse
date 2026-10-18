// ============================================================================
//  Corner Spider - SeasonHouse haunted house prop
//
//  A spider hides in the corner of the ceiling. When someone walks in (PIR) or
//  you press a button on the web page, it drops on a string, glares with red
//  LED eyes, chitters, screams through a DFPlayer Mini and flips the WLED room
//  lights to lightning - then slowly winds itself back up laughing.
//
//  Hardware: ESP32 DevKit, NEMA17 + A4988/DRV8825/TMC2208 winch, top limit
//  switch, HC-SR501 PIR, 2 red LEDs, passive piezo, DFPlayer Mini + speaker.
//  See docs/WIRING.md.
// ============================================================================
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <FastAccelStepper.h>
#include <DFRobotDFPlayerMini.h>
#include "config.h"
#include "web_ui.h"

// ---------------------------------------------------------------- globals ---
static WebServer server(80);
static Preferences prefs;
static FastAccelStepperEngine engine;
static FastAccelStepper *stepper = nullptr;
static DFRobotDFPlayerMini mp3;
static bool mp3Ok = false;

static long dropSteps = DROP_STEPS;
static int volume = DEFAULT_VOLUME;
static bool armed = true;        // motion sensor triggers scares
static bool partyMode = false;   // random scares on a timer
static bool homed = false;
static char wledHost[64] = WLED_HOST;
static QueueHandle_t wledQueue;
static uint32_t lastScareMs = 0;
static uint32_t nextPartyMs = 0;

// -------------------------------------------------------------- LED eyes ---
enum EyeMode { EYE_OFF, EYE_GLOW, EYE_FULL, EYE_PULSE, EYE_FLICKER, EYE_BLINK, EYE_DISCO };
static const char *eyeNames[] = {"off", "glow", "full", "pulse", "flicker", "blink", "disco"};
static EyeMode eyeMode = EYE_GLOW;

#if ESP_ARDUINO_VERSION_MAJOR >= 3
static void eyesBegin() { ledcAttach(PIN_EYE_L, 5000, 8); ledcAttach(PIN_EYE_R, 5000, 8); }
static void eyesWrite(uint8_t l, uint8_t r) { ledcWrite(PIN_EYE_L, l); ledcWrite(PIN_EYE_R, r); }
#else
// Channels 2/3 share a timer that tone() (channel 0) does not touch.
static void eyesBegin() {
  ledcSetup(2, 5000, 8); ledcAttachPin(PIN_EYE_L, 2);
  ledcSetup(3, 5000, 8); ledcAttachPin(PIN_EYE_R, 3);
}
static void eyesWrite(uint8_t l, uint8_t r) { ledcWrite(2, l); ledcWrite(3, r); }
#endif

static void eyesTick() {
  static uint32_t nextBlink = 0, blinkEnd = 0, nextFlicker = 0;
  static uint8_t flick = 255;
  uint32_t now = millis();
  switch (eyeMode) {
    case EYE_OFF:   eyesWrite(0, 0); break;
    case EYE_GLOW:  eyesWrite(25, 25); break;
    case EYE_FULL:  eyesWrite(255, 255); break;
    case EYE_PULSE: {
      float s = (sinf(now / 1500.0f * TWO_PI) + 1.0f) * 0.5f;
      uint8_t v = 10 + s * 245;
      eyesWrite(v, v);
      break;
    }
    case EYE_FLICKER:
      if (now >= nextFlicker) { flick = random(40, 256); nextFlicker = now + random(20, 90); }
      eyesWrite(flick, flick);
      break;
    case EYE_BLINK:
      if (now >= nextBlink) { blinkEnd = now + 140; nextBlink = now + random(1500, 4000); }
      if (now < blinkEnd) eyesWrite(0, 0); else eyesWrite(200, 200);
      break;
    case EYE_DISCO:
      if ((now / 220) % 2) eyesWrite(255, 0); else eyesWrite(0, 255);
      break;
  }
}

// --------------------------------------------------- buzzer "chittering" ---
static uint32_t chitterUntil = 0, nextChirp = 0;
static void chitter(uint32_t ms) { chitterUntil = millis() + ms; }
static void chitterTick() {
  uint32_t now = millis();
  if (now >= chitterUntil || now < nextChirp) return;
  tone(PIN_BUZZER, random(2200, 4800), random(4, 12));
  nextChirp = now + random(25, 70);
}

// ------------------------------------------------------------------ sound ---
static int season = 0;   // index into SEASONS, saved in flash

// Sound slot 1-8 of the current season: plays /01/001.mp3 ... /05/008.mp3.
static void playTrack(int slot) {
  if (!mp3Ok) return;
  mp3.playFolder(season + 1, slot);
}
static void stopSound() { if (mp3Ok) mp3.stop(); }

// ------------------------------------------------------------------- WLED ---
// HTTP calls can take a few hundred ms, so they run in their own task and the
// show never stutters waiting for the lights.
static void wledPreset(int ps) { xQueueSend(wledQueue, &ps, 0); }
// WLED slot 1-4 of the current season: Halloween uses presets 1-4, Christmas 11-14, and so on.
static void wledSlot(int slot) { wledPreset(season * 10 + slot); }

static void wledTask(void *) {
  int ps;
  for (;;) {
    if (xQueueReceive(wledQueue, &ps, portMAX_DELAY) != pdTRUE) continue;
    if (WiFi.getMode() == WIFI_STA && WiFi.status() != WL_CONNECTED) continue;
    HTTPClient http;
    String url = String("http://") + wledHost + "/json/state";
    http.setTimeout(800);
    if (http.begin(url)) {
      http.addHeader("Content-Type", "application/json");
      char body[48];
      snprintf(body, sizeof(body), "{\"on\":true,\"ps\":%d}", ps);
      int code = http.POST(body);
      Serial.printf("WLED preset %d -> %d\n", ps, code);
      http.end();
    }
  }
}

// ---------------------------------------------------------------- stepper ---
// Position 0 = home (top, tucked in the corner). Positive = further down.
enum Speed { SP_FAST, SP_SLOW, SP_MED };

static bool homeSwitchPressed() {
#if HAS_HOME_SWITCH
  return digitalRead(PIN_HOME_SW) == LOW;
#else
  return false;
#endif
}

static void setSpeed(Speed s) {
  switch (s) {
    case SP_FAST: stepper->setSpeedInHz(FAST_SPEED); stepper->setAcceleration(FAST_ACCEL); break;
    case SP_SLOW: stepper->setSpeedInHz(SLOW_SPEED); stepper->setAcceleration(SLOW_ACCEL); break;
    case SP_MED:  stepper->setSpeedInHz(FAST_SPEED / 3); stepper->setAcceleration(FAST_ACCEL / 3); break;
  }
}

static void moveToSteps(long target, Speed s) {
  target = constrain(target, 0L, dropSteps);
  setSpeed(s);
  stepper->moveTo(target);
}

static void moveToPermille(long pm, Speed s) { moveToSteps(dropSteps * pm / 1000, s); }

// Homing is a small state machine so the web page stays responsive.
static bool homing = false;
static void startHoming() {
#if HAS_HOME_SWITCH
  homing = true;
  homed = false;
  if (homeSwitchPressed()) { stepper->forceStopAndNewPosition(0); homing = false; homed = true; return; }
  stepper->setSpeedInHz(HOME_SPEED);
  stepper->setAcceleration(SLOW_ACCEL * 4);
  stepper->setCurrentPosition(dropSteps + HOME_EXTRA_STEPS);
  stepper->moveTo(0);   // wind up until the switch clicks
#else
  stepper->setCurrentPosition(0);   // no switch: whatever position we boot in is "home"
  homed = true;
#endif
}

static void stepperTick() {
  // Hitting the top switch always wins: stop and call it zero.
  if (homeSwitchPressed() && stepper->isRunning() && stepper->targetPos() <= stepper->getCurrentPosition()) {
    stepper->forceStopAndNewPosition(0);
  }
  if (homing && !stepper->isRunning()) {
    homing = false;
    homed = homeSwitchPressed();
    if (!homed) Serial.println("Homing failed: switch never pressed. Check string/switch.");
    else stepper->setCurrentPosition(0);
  }
}

// -------------------------------------------------------- show sequences ---
// Each show is a tiny script. The engine runs one step at a time without
// blocking, so the web page, PIR and eyes keep working during the show.
enum Op : uint8_t { OP_MOVE, OP_WAITMOVE, OP_WAIT, OP_RWAIT, OP_SND, OP_EYES, OP_WLED, OP_CHIT, OP_WIGGLE, OP_SNDSTOP, OP_END };
struct Step { Op op; long a; long b; };

#define S_MOVE(pm, sp)   {OP_MOVE, pm, sp}
#define S_WAITMOVE       {OP_WAITMOVE, 0, 0}
#define S_WAIT(ms)       {OP_WAIT, ms, 0}
#define S_RWAIT(lo, hi)  {OP_RWAIT, lo, hi}
#define S_SNDSTOP        {OP_SNDSTOP, 0, 0}
#define S_SND(t)         {OP_SND, t, 0}
#define S_EYES(m)        {OP_EYES, m, 0}
#define S_WLED(ps)       {OP_WLED, ps, 0}
#define S_CHIT(ms)       {OP_CHIT, ms, 0}
#define S_WIGGLE(n, st)  {OP_WIGGLE, n, st}
#define S_END            {OP_END, 0, 0}

struct Show { const char *id; const char *label; const char *hint; const Step *steps; };
struct Season {
  const char *id, *label, *character;
  const Show *shows; int numShows;
  const char *const *scary; int numScary;     // shows the motion sensor picks from
  const char *const *sounds;                  // labels of sound slots 1-8
  const char *const *wleds;                   // labels of WLED slots 1-4
};

// All shows for all seasons. Generated from the simulator so both stay identical.
#include "seasons.h"

static const Season &S() { return SEASONS[season]; }

static const Show *current = nullptr;
static int pc = 0;
static bool waitArmed = false;
static uint32_t waitUntil = 0;
static int wiggleLeft = -1;
static long wiggleBase = 0, wiggleOther = 0;

static bool startShow(const char *id) {
  if (!homed || homing) return false;
  for (int i = 0; i < S().numShows; i++) {
    if (strcmp(S().shows[i].id, id) == 0) {
      current = &S().shows[i];
      pc = 0; waitArmed = false; wiggleLeft = -1;
      lastScareMs = millis();
      Serial.printf("Show: %s\n", current->label);
      return true;
    }
  }
  return false;
}

static void stopAll() {
  current = nullptr;
  homing = false;
  stepper->stopMove();
  stopSound();
  chitterUntil = 0;
  eyeMode = EYE_GLOW;
}

static void showTick() {
  if (!current) return;
  for (;;) {
    const Step &s = current->steps[pc];
    switch (s.op) {
      case OP_END:
        current = nullptr;
        return;
      case OP_MOVE: moveToPermille(s.a, (Speed)s.b); pc++; break;
      case OP_WAITMOVE:
        if (stepper->isRunning()) return;
        pc++; break;
      case OP_WAIT:
      case OP_RWAIT:
        if (!waitArmed) {
          waitUntil = millis() + (s.op == OP_WAIT ? s.a : random(s.a, s.b));
          waitArmed = true;
        }
        if ((int32_t)(millis() - waitUntil) < 0) return;
        waitArmed = false; pc++; break;
      case OP_SND: playTrack(s.a); pc++; break;
      case OP_SNDSTOP: stopSound(); pc++; break;
      case OP_EYES: eyeMode = (EyeMode)s.a; pc++; break;
      case OP_WLED: wledSlot(s.a); pc++; break;
      case OP_CHIT: chitter(s.a); pc++; break;
      case OP_WIGGLE:
        if (stepper->isRunning()) return;
        if (wiggleLeft < 0) {
          // Bounce between where we are and a bit lower (or higher if already at the bottom).
          wiggleBase = stepper->getCurrentPosition();
          wiggleOther = wiggleBase + s.b <= dropSteps ? wiggleBase + s.b : wiggleBase - s.b;
          wiggleLeft = s.a * 2;
        }
        if (wiggleLeft == 0) { wiggleLeft = -1; pc++; break; }
        moveToSteps((wiggleLeft % 2 == 0) ? wiggleOther : wiggleBase, SP_FAST);
        wiggleLeft--;
        return;
    }
  }
}

// ---------------------------------------------- motion + party triggers ---
static const char *pickScare() { return S().scary[random(0, S().numScary)]; }

static void triggersTick() {
  uint32_t now = millis();
  if (current || homing || !homed) return;
  if (armed && digitalRead(PIN_PIR) == HIGH && now - lastScareMs > MOTION_COOLDOWN_MS) {
    Serial.println("Motion!");
    startShow(pickScare());
    return;
  }
  if (partyMode && (int32_t)(now - nextPartyMs) >= 0) {
    startShow(S().shows[random(0, S().numShows)].id);
    nextPartyMs = now + random(60000, 240000);
  }
}

// ------------------------------------------------------------- web server ---
static void sendJson(const String &s) { server.send(200, "application/json", s); }

static String statusJson() {
  char buf[640];
  snprintf(buf, sizeof(buf),
           "{\"season\":\"%s\",\"show\":\"%s\",\"pos\":%ld,\"drop\":%ld,\"moving\":%s,\"homed\":%s,\"homing\":%s,"
           "\"armed\":%s,\"party\":%s,\"vol\":%d,\"eyes\":\"%s\",\"mp3\":%s,\"wled\":\"%s\","
           "\"ip\":\"%s\",\"pir\":%s,\"top\":%s}",
           S().id, current ? current->id : "", (long)stepper->getCurrentPosition(), dropSteps,
           stepper->isRunning() ? "true" : "false", homed ? "true" : "false", homing ? "true" : "false",
           armed ? "true" : "false", partyMode ? "true" : "false", volume, eyeNames[eyeMode],
           mp3Ok ? "true" : "false", wledHost,
           (WiFi.getMode() == WIFI_AP ? WiFi.softAPIP() : WiFi.localIP()).toString().c_str(),
           digitalRead(PIN_PIR) ? "true" : "false", homeSwitchPressed() ? "true" : "false");
  return String(buf);
}

static void setupWeb() {
  server.on("/", HTTP_GET, [] { server.send_P(200, "text/html", INDEX_HTML); });
  server.on("/api/status", HTTP_GET, [] { sendJson(statusJson()); });

  // Everything the page needs to draw the current season's buttons.
  server.on("/api/season", HTTP_GET, [] {
    if (server.hasArg("s")) {
      for (int i = 0; i < NUM_SEASONS; i++) {
        if (server.arg("s") == SEASONS[i].id && i != season) {
          stopAll();
          season = i;
          prefs.putInt("season", season);
          wledSlot(1);
        }
      }
    }
    auto list = [](const char *const *items, int n) {
      String s = "[";
      for (int i = 0; i < n; i++) { if (i) s += ","; s += String("\"") + items[i] + "\""; }
      return s + "]";
    };
    String s = String("{\"season\":\"") + S().id + "\",\"character\":\"" + S().character + "\",\"seasons\":[";
    for (int i = 0; i < NUM_SEASONS; i++) {
      if (i) s += ",";
      s += String("{\"id\":\"") + SEASONS[i].id + "\",\"label\":\"" + SEASONS[i].label + "\"}";
    }
    s += "],\"shows\":[";
    for (int i = 0; i < S().numShows; i++) {
      if (i) s += ",";
      s += String("{\"id\":\"") + S().shows[i].id + "\",\"label\":\"" + S().shows[i].label + "\",\"hint\":\"" + S().shows[i].hint + "\"}";
    }
    s += "],\"sounds\":" + list(S().sounds, 8) + ",\"wled\":" + list(S().wleds, 4) + "}";
    sendJson(s);
  });

  server.on("/api/run", [] {
    bool ok = startShow(server.arg("show").c_str());
    server.send(ok ? 200 : 409, "application/json", statusJson());
  });
  server.on("/api/stop", [] { stopAll(); sendJson(statusJson()); });
  server.on("/api/home", [] { stopAll(); startHoming(); sendJson(statusJson()); });

  // Manual jog (for measuring the drop length). Not limited to dropSteps on purpose.
  server.on("/api/jog", [] {
    if (!current && !homing) {
      setSpeed(SP_SLOW);
      long target = stepper->getCurrentPosition() + server.arg("steps").toInt();
      stepper->moveTo(max(0L, target));
    }
    sendJson(statusJson());
  });
  server.on("/api/setdrop", [] {
    long d = server.hasArg("steps") ? server.arg("steps").toInt() : (long)stepper->getCurrentPosition();
    if (d > 100) { dropSteps = d; prefs.putLong("drop", dropSteps); }
    sendJson(statusJson());
  });

  server.on("/api/arm", [] {
    armed = server.arg("on") == "1";
    prefs.putBool("armed", armed);
    sendJson(statusJson());
  });
  server.on("/api/party", [] {
    partyMode = server.arg("on") == "1";
    nextPartyMs = millis() + 15000;
    sendJson(statusJson());
  });
  server.on("/api/vol", [] {
    volume = constrain(server.arg("v").toInt(), 0, 30);
    if (mp3Ok) mp3.volume(volume);
    prefs.putInt("vol", volume);
    sendJson(statusJson());
  });
  server.on("/api/eyes", [] {
    String m = server.arg("mode");
    for (int i = 0; i < 7; i++) if (m == eyeNames[i]) eyeMode = (EyeMode)i;
    sendJson(statusJson());
  });
  server.on("/api/sound", [] { playTrack(server.arg("t").toInt()); sendJson(statusJson()); });
  server.on("/api/chitter", [] { chitter(800); sendJson(statusJson()); });
  server.on("/api/wled", [] {
    if (server.hasArg("host")) {
      strlcpy(wledHost, server.arg("host").c_str(), sizeof(wledHost));
      prefs.putString("wled", wledHost);
    }
    if (server.hasArg("slot")) wledSlot(server.arg("slot").toInt());
    sendJson(statusJson());
  });

  server.onNotFound([] { server.send(404, "text/plain", "Nothing here but cobwebs."); });
  server.begin();
}

// ----------------------------------------------------------------- Wi-Fi ---
static void setupWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(MDNS_NAME);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("Joining %s", WIFI_SSID);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 10000) { delay(250); Serial.print('.'); }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nOnline: http://%s  (or http://%s.local)\n", WiFi.localIP().toString().c_str(), MDNS_NAME);
  } else {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASSWORD);
    Serial.printf("\nNo router. Hotspot \"%s\" -> http://%s\n", AP_SSID, WiFi.softAPIP().toString().c_str());
  }
  MDNS.begin(MDNS_NAME);
  MDNS.addService("http", "tcp", 80);
}

// ------------------------------------------------------------------ setup ---
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n== SeasonHouse Corner Spider ==");
  randomSeed(esp_random());

  pinMode(PIN_PIR, INPUT);
#if HAS_HOME_SWITCH
  pinMode(PIN_HOME_SW, INPUT_PULLUP);
#endif
  pinMode(PIN_BUZZER, OUTPUT);
  eyesBegin();

  prefs.begin("spider", false);
  dropSteps = prefs.getLong("drop", DROP_STEPS);
  volume = prefs.getInt("vol", DEFAULT_VOLUME);
  armed = prefs.getBool("armed", true);
  season = constrain(prefs.getInt("season", 0), 0, NUM_SEASONS - 1);
  prefs.getString("wled", WLED_HOST).toCharArray(wledHost, sizeof(wledHost));

  engine.init();
  stepper = engine.stepperConnectToPin(PIN_STEP);
  if (!stepper) { Serial.println("Stepper init failed - check PIN_STEP"); for (;;) delay(1000); }
  stepper->setDirectionPin(PIN_DIR, DIR_DOWN == 1);
  stepper->setEnablePin(PIN_EN);       // active LOW
  stepper->setAutoEnable(true);        // coil current only while moving...
  stepper->setDelayToDisable(HOLD_MS); // ...plus a short hold so it does not slip

  Serial2.begin(9600, SERIAL_8N1, PIN_MP3_RX, PIN_MP3_TX);
  mp3Ok = mp3.begin(Serial2, false, true);
  if (mp3Ok) { delay(300); mp3.volume(volume); }
  Serial.printf("DFPlayer: %s\n", mp3Ok ? "ok" : "not found (check wiring + SD card)");

  wledQueue = xQueueCreate(8, sizeof(int));
  xTaskCreatePinnedToCore(wledTask, "wled", 4096, nullptr, 1, nullptr, 0);

  setupWifi();
  setupWeb();
  startHoming();
  wledSlot(1);

  // Give the PIR its warm-up time before it is allowed to scare anyone.
  lastScareMs = millis();
}

void loop() {
  server.handleClient();
  stepperTick();
  showTick();
  triggersTick();
  eyesTick();
  chitterTick();
  delay(1);
}
