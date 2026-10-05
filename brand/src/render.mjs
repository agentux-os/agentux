// usage: node render.mjs in.svg out.png [width] [height]
import { Resvg } from '@resvg/resvg-js';
import fs from 'fs';
const [,, inp, out, w, h] = process.argv;
const svg = fs.readFileSync(inp, 'utf8');
const opts = { font: { loadSystemFonts: false } };
if (w) opts.fitTo = { mode: 'width', value: +w };
const png = new Resvg(svg, opts).render().asPng();
fs.writeFileSync(out, png);
console.log(out);
