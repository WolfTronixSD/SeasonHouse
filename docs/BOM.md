# Bill of materials

Everything needed for the five built props: the Corner Spider plus the Lightning Window, Scream-o-Meter, Cauldron of Doom and Rat Express. "Have" marks parts you already own (ESP32, WLED, steppers, LEDs, piezo, DFPlayer + speaker, dot matrix, PIR); "Buy" marks the ones from the $100 list in [IDEAS.md](IDEAS.md#100-shopping-list). Prices are rough AliExpress/Amazon prices.

## Totals across all five props

| Qty | Part | Used by | Status | ≈ Price |
|---|---|---|---|---|
| 5 | ESP32 DevKit v1 | one per prop | Have | |
| 5 | DFPlayer Mini + micro-SD card (any size) | one per prop | Have some, buy the rest | $2.50 each |
| 5 | 3 W 4-8 Ω speaker | one per prop | Have some, buy the rest | $2.50 each |
| 2 | NEMA17 stepper + A4988 driver (+100 µF cap each) | Spider, Rat | Have | |
| 4 | HC-SR501 PIR (or LD2410C mmWave) | Spider, Lightning, Cauldron, Rat | Have | |
| 4 | WLED controller + WS2812 strip (≈60 LEDs) | Spider room light, Lightning curtain, Scream VU bar, Cauldron glow | Have | |
| 1 | MAX7219 4-in-1 dot matrix | Scream-o-Meter | Have | |
| 1 | INMP441 I2S microphone | Scream-o-Meter | Buy | $3 |
| 1 | Big arcade button (optional) | Scream-o-Meter | Buy | $2 |
| 1 | MG996R metal-gear servo | Cauldron hand | Buy | $5 |
| 1 | 12 V ultrasonic mist maker with float | Cauldron | Buy | $12 |
| 1 | Float switch (optional) | Cauldron water level | Buy | $2 |
| 1 | 12 V LED floodlight or short 12 V strip | Lightning, outside behind the axe man | Buy | $5 |
| 2 | IRLZ44N logic-level MOSFET (or a MOSFET module) + 220 Ω + 10 kΩ | Lightning outdoor light, Cauldron mist maker | Buy | $3 |
| 1 | 6-wire capsule slip ring, 12.5 mm | Spider eyes | Buy | $8 |
| 1 | Lever microswitch | Spider home switch | Have/buy | $1 |
| 1 | Reed switch + small magnet | Rat home switch | Buy | $2 |
| 1 | 30 mm spool (3D-printed or bobbin) on a 5 mm coupler | Spider winch | Make | |
| 1 | 20 mm pulley (5 mm bore) + 1 idler pulley | Rat line loop | Buy | $4 |
| 4 | 12 V 2 A supply + LM2596 buck to 5 V | Spider, Rat, Cauldron, Lightning (12 V parts) | Have/buy | $8 each |
| 1 | 5 V 2 A USB supply | Scream-o-Meter (no 12 V parts) | Have | |
| 1 | 5-6 V 2 A supply for the servo | Cauldron | Buy | $5 |
| 2 | Red 5 mm LED + 100 Ω | Spider eyes | Have | |
| 1 | Passive piezo + 100 Ω | Spider chitter | Have | |
| 5 | 1 kΩ resistor | DFPlayer RX line, one per prop | Have | |
| | 0.3 mm black fishing line (≈10 kg) | Spider, Rat | Buy | $3 |
| | 30 AWG silicone 2-core wire | Spider eyes through the slip ring | Buy | $3 |
| | Dupont wires, perfboard, screw terminals | everywhere | Have | |

## Props and bodies

| Qty | Part | Used by | ≈ Price |
|---|---|---|---|
| 1 | Foam/plush spider under 250 g (or seasonal character) | Spider | $5 |
| 1 | Cardboard axe-man cut-out | Lightning, taped outside the window | free |
| 1 | Sheer white curtain | Lightning | $5 |
| 1 | Plastic cauldron + plastic bowl that fits inside | Cauldron | $8 |
| 1 | Rubber hand on a stick | Cauldron | $3 |
| 1 | Toy rat (light, ~10 cm) | Rat | $2 |
| | Black tape or cable cover for the rat's line | Rat | $2 |

## Per prop

- **Corner Spider:** ESP32, NEMA17 + A4988, spool, microswitch, PIR, 2 red LEDs, piezo, slip ring + 30 AWG wire, DFPlayer + speaker, 12 V supply + LM2596, WLED strip, fishing line, spider body.
- **Lightning Window:** ESP32, WLED strip behind the curtain, PIR, MOSFET + 12 V outdoor light, DFPlayer + speaker, 12 V supply + LM2596, curtain, axe-man cut-out.
- **Scream-o-Meter:** ESP32, INMP441 mic, MAX7219 4-in-1 matrix, WLED strip up the wall, arcade button, DFPlayer + speaker, 5 V supply.
- **Cauldron of Doom:** ESP32, MG996R servo + its own 5-6 V supply, mist maker + MOSFET, float switch, PIR, WLED ring under the bowl, DFPlayer + speaker, 12 V supply + LM2596, cauldron, bowl, rubber hand.
- **Rat Express:** ESP32, NEMA17 + A4988, 20 mm pulley + idler, reed switch + magnet, PIR, DFPlayer + speaker, 12 V supply + LM2596, fishing line, toy rat.

## Still to buy, roughly

INMP441, MG996R, mist maker, float switch, outdoor 12 V light, 2 MOSFETs, slip ring, reed switch, pulleys, servo supply, the DFPlayers and speakers you're short of, fishing line, wire and the bodies come to about **$85-95**, inside the $100 budget. Add about $8 for each extra 12 V supply you don't already have.

Wiring for each prop: [WIRING.md](WIRING.md) (spider) and [PROPS.md](PROPS.md) (the other four).
