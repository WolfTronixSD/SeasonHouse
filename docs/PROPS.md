# More props: Lightning Window, Scream-o-Meter, Cauldron of Doom, Rat Express

Each prop is its own ESP32 with its own web page, MicroPython code, wireless updates and recovery page, just like the Corner Spider. They share the spider's modules (`firmware/micropython/`) plus a small folder of their own in `firmware/props/<prop>/`.

| Prop | Page | Folder | Brain |
|---|---|---|---|
| Lightning Window | `http://storm.local` | [`firmware/props/lightning`](../firmware/props/lightning) | ESP32 + DFPlayer, flashes a WLED strip live over Wi-Fi |
| Scream-o-Meter | `http://scream.local` | [`firmware/props/screamometer`](../firmware/props/screamometer) | ESP32 + I2S mic + dot matrix + DFPlayer, WLED VU bar |
| Cauldron of Doom | `http://cauldron.local` | [`firmware/props/cauldron`](../firmware/props/cauldron) | ESP32 + servo + mist maker + DFPlayer, WLED glow |
| Rat Express | `http://rat.local` | [`firmware/props/rat`](../firmware/props/rat) | ESP32 + stepper + DFPlayer (same board as the spider) |

## Installing any of them

1. Flash MicroPython on the ESP32 as in [WIRING.md](WIRING.md#first-run-one-time-with-a-usb-cable).
2. Edit the prop's `config.py` (Wi-Fi, `OTA_KEY`, WLED IP, pins if yours differ).
3. Put the files together and copy them over USB:
   ```
   python3 tools/stage_prop.py lightning        # or screamometer, cauldron, rat
   cd build/lightning && mpremote cp -r . : + reset
   ```
4. Later updates go over Wi-Fi: `python3 tools/ota_push.py storm.local --prop lightning --key YOUR_KEY`, or the upload box on the prop's page.
5. Each prop has its own DFPlayer and SD card. Copy `sd-card/props/<prop>/01/` to the card as folder `01`.

Power: every prop runs from a 5 V supply (12 V for the steppers, mist maker and outdoor light, with an LM2596 buck to 5 V). Tie all grounds together. The DFPlayer TX/RX, speaker and power wiring is the same as the spider's.

## Lightning Window ⚡

A WLED strip sits behind a sheer curtain. A strike flickers like a real bolt (a few dim leader flickers, the main stroke, then fading restrikes), brightest at a different spot each time. The thunder follows 1 to 3 seconds later: close strikes crack quickly and loudly, distant ones roll in later and quieter. Every 10th strike, a light **outside** behind the cardboard axe man flashes instead, so his shadow lands on the curtain.

| Part | Pin | Notes |
|---|---|---|
| WLED strip behind the curtain | Wi-Fi | Any WLED controller. Give it a dim blue "moonlight" preset as its default; it goes back to it 2 s after each strike |
| Outdoor light behind the cut-out | GPIO 25 → logic-level MOSFET (IRLZ44N) | A 12 V LED floodlight or strip pointing at the window. Gate through 220 Ω, 10 kΩ gate-to-GND |
| PIR | GPIO 34 | A guest walking in gets a close strike |
| DFPlayer | TX 17, RX 16 | 3 W speaker, ideally low by the window |

- No WLED? Set `LED_MODE = "local"` and wire a WS2812 strip's data to GPIO 4 (through 330 Ω).
- The cut-out goes on the **outside** of the glass, the light further out pointing in. Indoors you only see the shadow, and only when that light fires.
- The page shows the strike counter, when the axe man is due, and lets you change "every 10th" or call him now. Auto storm has three intensities: distant rumbles, proper storm and apocalypse.
- Sounds (`sd-card/props/lightning/01/`): 001-003 close cracks, 004-006 distant rolling thunder.

## Scream-o-Meter 😱

Press SCREAM on the page (or the big arcade button). The dot matrix counts down "3, 2, 1", the announcer yells "SCREAM!", and for 3 seconds it keeps the loudest moment. The WLED bar shoots up the wall live, the score shows on the matrix, and the page keeps the top 10 with names. A new record flashes the bar and plays a fanfare. A scream over 100 dB, even outside a round, sets off the other props (the spider drops by default, see `TRIGGER_URLS`).

| Part | Pin | Notes |
|---|---|---|
| INMP441 I2S microphone | SCK 14, WS 15, SD 32 | L/R to GND, VDD 3.3 V. Short wires |
| MAX7219 4-in-1 dot matrix | DIN 23, CLK 18, CS 5 | 5 V VCC. Mirrored text? Set `DM_FLIP_X` / `DM_FLIP_Y` |
| WLED strip up the wall | Wi-Fi | 60 LEDs is plenty; the bar is streamed live |
| Arcade button (optional) | GPIO 27 to GND | Starts a round |
| DFPlayer | TX 17, RX 16 | |

- Calibrate once: hold a phone sound-meter app next to the mic, talk loudly, and change "Mic calibration" on the page until both agree (default 120 for the INMP441).
- Sounds: 001 the "3, 2, 1, SCREAM!" countdown (timed to the matrix), 002 new high score, 003 weak scream heckle, 004 "Not bad", 005 "My ears!", 006 "You woke something up..." when a scream sets off the other props.

## Cauldron of Doom 🧪

An ultrasonic mister in a bowl of water inside the cauldron makes the fog, WLED glows green underneath, and the MP3 loops a bubbling sound. On motion, the light turns blood red, the witch asks who disturbs her stew, and a hand rises slowly out of the fog, grabs at the air, and sinks back. Then it all returns to green and bubbling.

| Part | Pin | Notes |
|---|---|---|
| MG996R servo + a rubber hand on a stick | GPIO 13 | Power the servo from its own 5-6 V 2 A supply, common GND |
| 12 V ultrasonic mist maker (with float) | GPIO 26 → MOSFET or relay | Never runs longer than 2 min without a 20 s rest |
| Float switch (optional) | GPIO 35 to GND | Set `HAS_WATER_SWITCH = True`; fog stops when the water is low |
| PIR | GPIO 34 | |
| WLED ring/strip under the bowl | Wi-Fi | Presets 61 green bubbling, 62 blood red, 63 white flicker, 64 off |
| DFPlayer | TX 17, RX 16 | |

- Fog modes: off, on-and-off (20 s on, 40 s off, saves water) or always on. Scares always add fog.
- Set the hand's down and up angles on the page, with "Test: raise" to check the hand clears the rim.
- Scares: The Hand, Peekaboo (fingers over the rim), Snatch (shoots out without warning), Toil and Trouble (chant and fog), Cackle.
- Sounds: 001 bubbling (made to loop seamlessly), 002 "Who disturbs my stew?", 003 cackle, 004 "You'll make a lovely soup!", 005 "Double, double, toil and trouble", 006 a big gurgle.
- Keep the electronics above the water line and the mist maker's cable strain-relieved. Use a plastic bowl inside the cauldron, not the cauldron itself.

## Rat Express 🐀

A stepper pulls a loop of black fishing line along the baseboard. A toy rat is clipped to the line and scurries across the floor, behind people's ankles, with squeaks and scratching claws.

| Part | Pin | Notes |
|---|---|---|
| NEMA17 + A4988 | STEP 26, DIR 27, EN 25 | Same driver wiring as the spider |
| 20 mm pulley on the motor + an idler at the far end | | The line runs motor → idler → back, as a closed loop |
| Reed switch at the rat's hole + magnet on the line | GPIO 33 to GND | Tells it the rat is home |
| PIR | GPIO 34 | Point it where people walk *past* the track |
| DFPlayer | TX 17, RX 16 | Speaker low, near the rat's hole |

- Build the loop tight, with a spring or rubber band in it to keep tension. Hide the line under the baseboard edge or a strip of black tape on the floor.
- On boot the rat runs home until the reed switch closes. In **Setup: track length**, jog it to the far end and press **Save this spot as the end of the track**.
- Runs: Ankle Dash, Fake-out (peeks, hides, then goes), Stalker (creeps, freezes, bolts), Nibbler (twitches at your feet), Rat Race.
- Sounds: 001 squeak, 002 scurrying claws, 003 angry squeal, 004 hiss, 005 "Eek!", 006 a whole swarm.
