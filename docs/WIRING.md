# Corner Spider: parts, wiring and setup

The spider lives in a ceiling corner on a fishing-line winch. A NEMA17 stepper winds the line on a spool, a microswitch tells it when it is fully up, a PIR sees guests coming, and an ESP32 runs the show, the web page and the WLED lights.

## Parts

| Part | Notes |
|---|---|
| ESP32 DevKit v1 | Any 30/38-pin dev board |
| NEMA17 stepper + A4988 (or DRV8825 / TMC2208) | The winch. A 28BYJ-48 is too slow for a real drop |
| Spool, 30 mm diameter | 3D-printed, a sewing bobbin, or a small fishing reel spool on a 5 mm coupler |
| 0.3 mm black fishing line (≈10 kg) | Invisible in the dark |
| Lever microswitch | Top "home" switch |
| HC-SR501 PIR | Or an LD2410 mmWave sensor (same OUT pin) |
| 2× red 5 mm LEDs + 2× 100 Ω | The eyes |
| Passive piezo + 100 Ω | Chittering clicks |
| DFPlayer Mini + micro-SD + 3 W 4-8 Ω speaker | Sound |
| 6-wire capsule slip ring (12.5 mm) | Gets power to the eyes through the turning spool (see below) |
| 12 V 2 A supply + LM2596 buck to 5 V | One supply for everything except WLED |
| Foam/plush spider under ~250 g | Lighter = faster, quieter drop |

## Wiring

```
12V PSU ──┬── A4988 VMOT (+100 µF cap across VMOT/GND)
          └── LM2596 IN ── 5V OUT ──┬── ESP32 VIN
                                    ├── DFPlayer VCC
                                    └── PIR VCC
All GNDs tied together.

ESP32            A4988 / parts
GPIO26  ───────  STEP
GPIO27  ───────  DIR
GPIO25  ───────  EN            (RESET and SLEEP jumpered together)
3V3     ───────  A4988 VDD
GPIO33  ───────  microswitch COM, NO ── GND   (internal pull-up)
GPIO34  ───────  PIR OUT
GPIO18  ── 100Ω ── LED eye L ── GND
GPIO19  ── 100Ω ── LED eye R ── GND
GPIO23  ── 100Ω ── piezo ── GND
GPIO16 (RX2) ──  DFPlayer TX
GPIO17 (TX2) ── 1kΩ ── DFPlayer RX
DFPlayer SPK1/SPK2 ── speaker
```

Set the A4988 current limit before the first run (Vref ≈ 0.6 V for a 1.5 A NEMA17 with 0.1 Ω sense resistors) and leave MS1-MS3 open for full steps, which is what the default speeds in `config.h` assume.

## Mechanics

1. Mount the motor and spool above a false ceiling corner or on a small shelf painted black, with the line running down through a screw eye.
2. Thread a bead on the line just above the spider. When the spider is fully up, the bead pushes the microswitch lever. That is "home".
3. **Eyes on a moving spider:** run a thin 2-core wire (30 AWG silicone) wound on the spool next to the fishing line, through the slip ring on the spool's free end. The fishing line carries the weight, the wire only carries 20 mA. If you skip the slip ring, use a CR2032 and two LEDs inside the spider that are always on, and set `Eyes` to *off* in the web page so the corner LEDs (if any) don't give the spider away.
4. Point the PIR at the doorway, not at the spider, or the spider will scare itself.

## Sound card

The card has one folder per season (`01` Halloween to `05` Winter) with `001.mp3` to `008.mp3` in each. The full list is in [`sd-card/README.md`](../sd-card/README.md).

## WLED

Each season uses four WLED presets, numbered season × 10 + slot: Halloween 1-4, Christmas 11-14, Easter 21-24, Fall 31-34, Winter 41-44. Slot 1 is the ambient look, 2 the flash, 3 the mood colour and 4 party. The looks for each season are in [`SEASONS.md`](SEASONS.md). You only need to save the presets for the seasons you use.

Type the WLED controller's IP on the control page (Eyes, sound, lights → WLED IP) and press Save.

## First run

1. Edit `firmware/corner-spider/include/config.h`: Wi-Fi name and password.
2. `pio run -d firmware/corner-spider -t upload`, then `pio device monitor` to see the IP.
3. Open `http://spider.local` (or the IP). If your router is not reachable the spider makes its own hotspot **SeasonHouse-Spider** (password `boo12345`), page at `http://192.168.4.1`. Join WLED to that hotspot too for an offline party.
4. On boot the spider winds up until the switch clicks. Then in **Setup: drop length**, jog down until it hangs at face height and press **Save current spot as full drop**.
5. Pick the season, press the first show, then arm the motion sensor and hide.
