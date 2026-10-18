# SeasonHouse

DIY haunted-house electronics: ESP32 props with web control, WLED lighting, steppers, sound and sensors.

| Prop | Folder | Status |
|---|---|---|
| Corner Spider: drops from the ceiling with red eyes, scream and lightning. Changes character by season: Santa, Bungee Bunny, Acorn Squirrel, Yeti | [`firmware/corner-spider`](firmware/corner-spider) | Built |
| Simulator: try every show in the browser before wiring anything | [`simulator/index.html`](simulator/index.html) | Built |
| More props | [`docs/IDEAS.md`](docs/IDEAS.md) | Ideas + $100 shopping list |

- Seasons, characters and shows: [`docs/SEASONS.md`](docs/SEASONS.md)
- Wiring and setup: [`docs/WIRING.md`](docs/WIRING.md)
- Sounds for the SD card: [`sd-card/README.md`](sd-card/README.md)

Build: `pio run -d firmware/corner-spider -t upload`

Shows are defined once in `simulator/index.html`. After changing them, run `node tools/gen_seasons.mjs` to regenerate the firmware's `seasons.h`.
