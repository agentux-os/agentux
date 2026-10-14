"""Trace the penguin artwork (penguin.png) into penguin.svg, the mark's geometry.

penguin.png is the original art: a lime penguin swimming on Ink, its wake drawn
as three water lines and a few bubbles. This script vectorises it once; build.py
only reads penguin.svg, so it runs without these requirements:
  pip install potracer numpy pillow

Each traced shape gets an id so build.py can colour the parts separately:
  body      back, wing, head and beak, and the middle water line that runs
            into the back (one shape in the art)
  belly, flipper, eye
  water-1, water-2   the upper and lower water lines
  bubble-*  the bubbles
Coordinates are the art's pixels (1254 x 1254).

Usage: python brand/src/trace.py
"""

from pathlib import Path

import numpy as np
import potrace
from PIL import Image

SRC = Path(__file__).resolve().parent
UP = 2  # trace at 2x for smoother curves


def main():
    im = Image.open(SRC / "penguin.png").convert("RGB")
    w, h = im.size
    im = im.resize((w * UP, h * UP), Image.LANCZOS)
    a = np.asarray(im).astype(int)
    lime = (a[:, :, 1] > 140) & (a[:, :, 0] > 100) & (a[:, :, 2] < 160)
    # potracer fills the zero pixels, so trace the inverse of the lime mask.
    curves = potrace.Bitmap(~lime).trace(
        turdsize=20, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
        alphamax=1.0, opticurve=True, opttolerance=0.2)

    def pt(p):
        return f"{p.x / UP:.2f} {p.y / UP:.2f}"

    parts = []
    for c in curves:
        d = ["M" + pt(c.start_point)]
        xs, ys = [c.start_point.x], [c.start_point.y]
        for s in c.segments:
            if s.is_corner:
                d.append(f"L{pt(s.c)} L{pt(s.end_point)}")
                xs += [s.c.x, s.end_point.x]
                ys += [s.c.y, s.end_point.y]
            else:
                d.append(f"C{pt(s.c1)} {pt(s.c2)} {pt(s.end_point)}")
                xs += [s.c1.x, s.c2.x, s.end_point.x]
                ys += [s.c1.y, s.c2.y, s.end_point.y]
        box = [min(xs) / UP, min(ys) / UP, max(xs) / UP, max(ys) / UP]
        parts.append({"d": " ".join(d) + "Z", "box": box})

    # Name the parts by size and place (see the docstring).
    def width(p):
        return p["box"][2] - p["box"][0]

    named = {}
    body = max(parts, key=width)
    named["body"] = body
    small = [p for p in parts if width(p) < 40]
    eye = max(small, key=lambda p: p["box"][0])
    named["eye"] = eye
    bubbles = sorted((p for p in small if p is not eye), key=lambda p: (p["box"][1], p["box"][0]))
    for i, p in enumerate(bubbles, 1):
        named[f"bubble-{i}"] = p
    rest = [p for p in parts if p is not body and width(p) >= 40]
    belly = max(rest, key=lambda p: p["box"][0])
    named["belly"] = belly
    rest.remove(belly)
    flipper = max(rest, key=lambda p: p["box"][0])
    named["flipper"] = flipper
    rest.remove(flipper)
    for i, p in enumerate(sorted(rest, key=lambda p: p["box"][1]), 1):
        named[f"water-{i}"] = p

    paths = "\n".join(
        f'  <path id="{k}" data-box="{" ".join(f"{v:.1f}" for v in p["box"])}" d="{p["d"]}"/>'
        for k, p in named.items())
    (SRC / "penguin.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">\n'
        f'  <rect width="{w}" height="{h}" fill="#0b0d10"/>\n'
        f'  <g fill="#c6f36b">\n{paths}\n  </g>\n</svg>\n',
        encoding="utf-8", newline="\n")
    print("penguin.svg:", ", ".join(named))


if __name__ == "__main__":
    main()
