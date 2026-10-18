// Generates firmware/micropython/seasons.json from the SEASONS table in
// simulator/index.html, so the simulator and the real prop run the same shows.
//   node tools/gen_seasons.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(join(root, "simulator/index.html"), "utf8");
const m = html.match(/const SEASONS = (\{[\s\S]*?\n\});/);
if (!m) throw new Error("SEASONS table not found in simulator/index.html");
const SEASONS = Function(`return (${m[1]})`)();

const out = Object.entries(SEASONS).map(([id, s]) => ({
  id,
  label: s.label,
  char: s.char,
  scary: s.scary,
  sounds: s.sounds,
  wled: s.wled.map((w) => w.n),
  shows: Object.entries(s.shows).map(([sid, [label, hint, steps]]) => ({ id: sid, label, hint, steps })),
}));
const target = join(root, "firmware/micropython/seasons.json");
writeFileSync(target, JSON.stringify(out) + "\n");
console.log(`seasons.json: ${out.length} seasons, ${out.reduce((n, s) => n + s.shows.length, 0)} shows`);
