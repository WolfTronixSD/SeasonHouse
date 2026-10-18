# SeasonHouse

DIY haunted-house electronics: ESP32 props with web control, WLED lighting, steppers, sound and sensors.

| Prop | Folder | Status |
|---|---|---|
| Corner Spider: drops from the ceiling with red eyes, scream and lightning. Changes character by season: Santa, Bungee Bunny, Acorn Squirrel, Yeti | [`firmware/micropython`](firmware/micropython) | Built (MicroPython, updates over Wi-Fi) |
| Lightning Window: flash behind the curtain, thunder 1-3 s later, an axe man's shadow every 10th strike | [`firmware/props/lightning`](firmware/props/lightning) | Built |
| Scream-o-Meter: scream into a mic, WLED bar up the wall, score on a dot matrix, leaderboard on the page | [`firmware/props/screamometer`](firmware/props/screamometer) | Built |
| Cauldron of Doom: fog, green glow, bubbling, and a hand that rises out of the fog | [`firmware/props/cauldron`](firmware/props/cauldron) | Built |
| Rat Express: a toy rat on a fishing-line loop scurries along the baseboard | [`firmware/props/rat`](firmware/props/rat) | Built |
| Simulator: try every show in the browser before wiring anything | [`simulator/index.html`](simulator/index.html) | Built |
| More props | [`docs/IDEAS.md`](docs/IDEAS.md) | Ideas + $100 shopping list |

- Seasons, characters and shows: [`docs/SEASONS.md`](docs/SEASONS.md)
- Wiring and setup: [`docs/WIRING.md`](docs/WIRING.md) (spider), [`docs/PROPS.md`](docs/PROPS.md) (the other four)
- Sounds for the SD card: a ready-made pack of 40 MP3s (real recordings, voices and music) in [`sd-card/`](sd-card/README.md), credits in [`sd-card/CREDITS.md`](sd-card/CREDITS.md)

First install and wireless updates: see [`docs/WIRING.md`](docs/WIRING.md#first-run-one-time-with-a-usb-cable). Tests: `python3 tests/test_firmware.py && python3 tests/test_props.py`.

Shows are defined once in `simulator/index.html`. After changing them, run `node tools/gen_seasons.mjs` to regenerate the firmware's `seasons.json`.
