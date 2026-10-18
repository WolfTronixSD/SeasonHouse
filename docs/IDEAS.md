# SeasonHouse prop ideas

Every prop below runs on an ESP32 with its own little web page, like the Corner Spider, and can fire WLED presets. The plan for later is one "Haunt Master" page that triggers every prop from a phone (see the last idea).

Legend: 😱 scary, 😂 funny, 🧰 parts you already have, 🛒 needs something from the $100 list.

## Stepper props (cousins of the Corner Spider)

1. **Corner Spider** 😱😂 🧰 *(built, `firmware/corner-spider`)*. Drops from the ceiling with lightning and a scream, twitches, laughs and winds back up. Has a Fake-Out Boing and a Spider Disco mode.
2. **Rat Express** 😱 🧰. A stepper drives a loop of fishing line along the baseboard, and a toy rat clipped to it scurries across the floor with squeaks when the PIR fires. Run it right behind people's ankles.
3. **Zipline Ghost** 😱 🧰. Same loop idea at ceiling height across the room: a cheesecloth ghost with white LEDs flies over the guests' heads while WLED flickers and the MP3 wails. Add a "boo" stop exactly above the sofa.
4. **Haunted Toilet Paper** 😂 🧰. A stepper hidden behind the roll slowly unrolls the toilet paper when someone sits down (PIR under the sink), then plays "...I'm watching you" and rolls it back up. Tested by nobody, guaranteed reaction.
5. **Ouija Board That Spells Your Name** 😱 🛒 GT2 belts. Two steppers make a hidden XY plotter under a table; a magnet drags the planchette. Type a guest's name on the web page and the board spells it letter by letter, then slides to "GOODBYE" while the lights die.
6. **The Shaking Crate** 😱 🛒 solenoid. A wooden crate stencilled "DO NOT FEED". A solenoid bangs on the lid from inside and a stepper with an off-centre weight makes it rattle, with growls on the MP3. A dot matrix on the side reads "FEEDING TIME IN 00:10" counting down.

## Light and display props

7. **Possessed Welcome Sign** 😱😂 🧰 dot matrix. MAX7219 matrices scroll "WELCOME FRIENDS". When someone walks past it glitches, flashes "BEHIND YOU", then goes back to "WELCOME FRIENDS" as if nothing happened. Message list editable from the web page.
8. **Wall of Eyes** 😱 🧰 WS2812. Cut a strip into pairs of LEDs and poke them through black fabric. Pairs blink lazily at random in the dark. On motion they all snap open at once and turn red, then fade out one by one.
9. **Lightning Window** 😱 🧰 WLED. A WLED strip behind a sheer curtain with thunder on the MP3, timed so the flash comes first and the thunder rolls 1-3 seconds later like a real storm. Every 10th strike shows a silhouette (cardboard cut-out of a man with an axe) taped to the outside.
10. **Scream-o-Meter** 😂 🛒 microphone. An I2S microphone measures how loud guests scream. WLED shows it as a VU bar up the wall, the dot matrix shows the score, and the web page keeps a leaderboard. Best party game of the night, and it doubles as a trigger: a loud scream sets off the spider.
11. **Chasing Shadow Hallway** 😱 🛒 mmWave. Three mmWave sensors along the hall. A single dim WLED pixel follows the guest one step behind them, then everything goes black and a whisper plays right where they stand.

## Sound and motion jump-scares

12. **Skully the Terrible Comedian** 😂 🛒 servo. A skull on a servo jaw that moves with the MP3 audio. Tells awful dad jokes ("Why didn't the skeleton go to the party? He had no BODY to go with!"), waits for laughter with the mic, and if nobody laughs: screams, eyes go red, lights go out.
13. **The Candy Bowl Grabber** 😱😂 🛒 servo. A rubber hand under fake moss in the candy bowl. An IR/ultrasonic sensor sees a hand reaching in, the hand grabs, and a gravelly voice says "Only ONE piece." Second reach in a minute: scream.
14. **The Phone That Knows** 😱 🧰 beeper + MP3. An old phone rings (beeper) when someone walks by. If they pick it up (switch in the cradle), they hear "I can see you... nice costume." Record custom lines for specific guests.
15. **Cauldron of Doom** 😱 🛒 mist maker. An ultrasonic mister in a bowl of water inside a cauldron, WLED green underneath, bubbling sound. On motion a hand (servo) rises out of the fog.

## The glue

16. **Haunt Master** 🧰. Every prop talks ESP-NOW to one master ESP32 that serves a single control page: big buttons per prop, "Run full scare sequence" that chains them (lights die, spider drops, crate bangs, wall of eyes opens), and a party-mode scheduler. The Corner Spider already has a plain HTTP API (`/api/run?show=drop`), so the master can trigger it over Wi-Fi from day one.

## $100 shopping list

Prices are typical AliExpress/Amazon multi-pack prices and will vary.

| Item | For | ≈ Price |
|---|---|---|
| 6-wire capsule slip ring | Corner Spider eyes | $8 |
| 3× LD2410C mmWave presence sensors | Chasing Shadow, better triggers everywhere | $12 |
| 2× INMP441 I2S microphones | Scream-o-Meter, Skully's laugh detector | $6 |
| 2× MG996R metal-gear servos | Skully's jaw, Candy Grabber | $10 |
| 12 V push-pull solenoid + MOSFET module | Shaking Crate | $10 |
| GT2 belt (2 m) + 2 pulleys + 4 idlers | Ouija plotter | $14 |
| 12 V ultrasonic mist maker | Cauldron of Doom | $12 |
| 2× extra DFPlayer Mini + 2× 3 W speakers | So every prop has its own voice | $10 |
| Dollar-store skull, rubber hand, toy rats, cheesecloth | Bodies for the props | $12 |
| Black fishing line, black fabric, magnets | Everywhere | $6 |
| **Total** | | **≈ $100** |

## Suggested build order

1. Corner Spider (code done; wire it and measure the drop).
2. Possessed Welcome Sign and Wall of Eyes (parts you already have, quick wins).
3. Scream-o-Meter (the party favourite).
4. Haunt Master, so the next props plug straight in.
