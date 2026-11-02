# 3D-printed parts for the Corner Spider

Five STLs, already lying in the right orientation for the bed. Step-by-step 3D assembly guide: https://claude.ai/artifact/EgQjmvF7dXVjvdr2J8T1cT

| File | What | Size | Print |
|---|---|---|---|
| [`winch_bracket.stl`](winch_bracket.stl) | Holds the NEMA17, screws to the ceiling or the underside of a shelf, guides the line and holds the home microswitch | 90 × 86 × 68 mm | PETG or PLA, 0.2 mm, 4 walls, 30 % gyroid, no supports |
| [`winch_spool.stl`](winch_spool.stl) | 30 mm spool for the fishing line (the size the firmware's step maths expects) | 44 × 44 × 25 mm | PLA, 0.16 mm, 4 walls, 40 % infill, no supports |
| [`slipring_cup.stl`](slipring_cup.stl) | Holds a 12.5 mm capsule slip ring on the spool so eye wires can turn with it (only for eye effects) | 30 × 30 × 14 mm | PLA, 0.16 mm, 4 walls, 40 % infill, no supports |
| [`spider_body.stl`](spider_body.stl) | Spider with 3 mm LED eyes, a hollow head, wire channel and a CR2032 pocket underneath | 138 × 139 × 31 mm | PLA (black or dark purple), 0.2 mm, 2 walls, 15 % infill, no supports, brim on |
| [`spider_battery_lid.stl`](spider_battery_lid.stl) | Lid for the coin-cell pocket | 26 × 26 × 2 mm | Same as the spider |

The spider weighs about 20 g, plus 3 g for the CR2032 (change `SPIDER_SCALE` in `make_parts.py` for another size). It hangs level, because its line hole sits right over the balance point with the cell fitted.

Two ways to power the eyes:

- **Coin cell** (simplest): a CR2032 in the spider lights the eyes all the time. No wires go up the line, and you can skip the slip ring and its cup.
- **Slip ring + magnet wire**: the ESP32 drives the eyes, so the glow, pulse, flicker and disco effects work. Three strands of 0.1 mm magnet wire run down beside the fishing line from the slip ring on the spool.

**Quickest:** open [`seasonhouse_spider.3mf`](seasonhouse_spider.3mf) in Bambu Studio (File → Open Project). It has all five parts laid out on one plate at 0.2 mm, with each part's walls, infill and brim already set, so you only pick the printer and filament. Rebuild it with `python3 hardware/print/make_3mf.py` after changing the STLs.

## Extra hardware

- 4× M3 × 8 mm screws: motor to bracket (the heads sink in so they clear the spool)
- 1× M3 × 6 mm set screw or a short M3 screw, plus 1 M3 nut: spool to the motor shaft (the nut drops into the slot in the collar)
- 4× 4 mm wood screws, countersunk: bracket to the ceiling or shelf
- 2× M2 × 12 mm screws and nuts: the microswitch to the tab under the arm (a standard 20 × 10 mm lever switch with holes 9.5 mm apart)
- 2× 3 mm red LEDs and a 6 mm bead for the line
- Coin cell: 1× CR2032, copper tape, 2× M2 × 6 mm screws for the lid
- Slip ring: 12.5 mm 6-wire capsule slip ring, 3× M2 × 8 mm screws (cup to spool), 0.1 mm magnet wire, 1 small zip tie, a drop of glue

## Putting it together

The [3D guide](https://claude.ai/artifact/EgQjmvF7dXVjvdr2J8T1cT) shows each step being put together.

1. Screw the motor to the back of the bracket so the shaft comes through the big hole and the cable points up (4× M3 × 8, heads sink into the front).
2. Drop the M3 nut into the slot in the spool's collar. Push the spool on the shaft with the collar towards the bracket and the set screw on the shaft's flat, leaving a 1-2 mm gap to the bracket. Tighten the set screw.
3. Slip ring only: push the slip ring into the cup, spinning end first, with a drop of glue, and lead its wires out of the slot in the cup's bottom. Screw the cup to the spool's outer face with 3× M2 × 8 into the three small holes. Thread the spinning wires through the hole in the flange (opposite the tie hole) and solder each to a strand of magnet wire.
4. Screw the microswitch to the side of the slotted tab under the arm that faces the line hole (nuts on the other side), with the lever pointing forward. Bend the lever tip so it sits just under the line hole. Wire it to GPIO 33 and GND.
5. Tie the fishing line through the small hole in the spool's outer flange, wind a few turns on, then feed it down through the funnel hole in the arm. The line has to leave the spool on the side over that hole. Thread the bead on about 5 cm above where the spider will hang.
6. Screw the top plate to the ceiling or under a shelf with 4 countersunk wood screws. Slip ring only: zip-tie its fixed wires through the two slots above it so that end can't spin, and run them to the ESP32 (GPIO18 → 100 Ω → ring 1, GPIO19 → 100 Ω → ring 2, GND → ring 3, see [WIRING.md](../../docs/WIRING.md)).
7. Eyes on a coin cell: solder the two LEDs in parallel (long legs to one wire, short legs to another), feed the wires in through the eye holes, through the head and the channel to the cell pocket, and glue the LEDs in. Tape the + wire under copper tape on the pocket ceiling, and the − wire (from the small hole at the pocket's edge) under copper tape on the inside of the lid. Put the CR2032 in with + up and screw the lid on with 2× M2 × 6. A strip of paper between the cell and the tape switches the eyes off.
8. Eyes on the slip ring: solder the magnet wires to the LEDs instead (one per eye's + leg, one to both − legs) and run them down beside the line. Leave the cell out.
9. Tie the line through the hole in the fin. Power up and set the drop length on the web page. If the spider goes the wrong way, flip `DIR_DOWN` in `config.py`.

## Changing the parts

The STLs are generated by [`make_parts.py`](make_parts.py), where every measurement (motor, shaft, spool, eye position, leg layout) is a named value near the top or inside each part. To regenerate them:

```
pip install manifold3d trimesh numpy
python3 hardware/print/make_parts.py
```
