# SD card sounds

FAT32 micro-SD card with one numbered folder per season and files `001.mp3` to `008.mp3` in each. **A ready-made pack is in this folder:** copy `01` to `05` to the root of the card and you're done. They're the same files the simulator plays. Sources and licences are in [CREDITS.md](CREDITS.md); rebuild or tweak them with `tools/soundpack/build.py`.

```
01/  Halloween
02/  Christmas
03/  Easter
04/  Fall
05/  Winter
```

Slot 7 is the dance track (about 35 s). The rest are short effects and voice lines.

| Slot | Halloween | Christmas | Easter | Fall | Winter |
|---|---|---|---|---|---|
| 001.mp3 | Hiss | Grumble | Carrot crunch | Angry chatter | Shiver |
| 002.mp3 | Scream | HO HO HO! | Surprise honk | Squirrel shriek | YETI ROAR |
| 003.mp3 | Evil laugh | Jolly laugh | Bunny giggle | Cheeky giggle | Frosty laugh |
| 004.mp3 | Creaky rope | Chimney creak | Spring sproing | Branch creak | Ice crack |
| 005.mp3 | Heartbeat | Sleigh bells | Ticking clock | Wind gust | Howling wind |
| 006.mp3 | BOING | BOING | BOING | BOING | BOING |
| 007.mp3 | Spider Disco (Toccata in D minor, disco beat) | Jingle Bells, rock beat | Hop Hop Hooray | Nutty Shuffle (banjo) | Blizzard Boogie (boogie-woogie piano) |
| 008.mp3 | "Hiii!" | "Naughty or nice?" | "Happy Easter!" | "Mine! All mine!" | "Brrrr!" |

Tip: normalise everything to the same loudness, and put 0.1 s of silence at the start of each file so the DFPlayer does not clip the first syllable.

To swap in your own sound, just replace the file with the same name (keep the 3-digit number). Everything is mono MP3 at 44.1 kHz, levelled to the same loudness, with 0.1 s of silence at the start.

## The other props

Each of the other props has its own DFPlayer, so its own card with just a folder `01`. Copy `props/<prop>/01/` to the root of that card:

| Prop | Card contents |
|---|---|
| Lightning Window | `props/lightning/01/`: 001-003 close thunder cracks, 004-006 distant rolling thunder |
| Scream-o-Meter | `props/screamometer/01/`: 001 "3, 2, 1, SCREAM!", 002 new high score, 003-005 reactions, 006 "You woke something up..." |
| Cauldron of Doom | `props/cauldron/01/`: 001 bubbling loop, 002-005 the witch, 006 big gurgle |
| Rat Express | `props/rat/01/`: 001 squeak, 002 claws, 003 squeal, 004 hiss, 005 "Eek!", 006 swarm |
