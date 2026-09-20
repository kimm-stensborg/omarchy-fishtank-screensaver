#!/usr/bin/env python3
"""Render one fish tank frame to a PNG, so the art can be eyeballed.

    tools/preview.py out.png [cols] [rows] [seconds] [scale]

Each pixel of the tank becomes a `scale`x`scale` block in the image.
"""

import importlib.util
import os
import random
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
from importlib.machinery import SourceFileLoader

loader = SourceFileLoader("fishtank", os.path.join(HERE, "..", "bin", "fishtank"))
spec = importlib.util.spec_from_loader("fishtank", loader)
ft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ft)


class Opts:
    fish = None
    logo = os.environ.get("PREVIEW_LOGO", "auto")
    logo_opacity = float(os.environ.get("PREVIEW_LOGO_OPACITY", "0.16"))


def write_png(path, width, height, rows_rgb):
    raw = b"".join(b"\x00" + row for row in rows_rgb)

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "preview.png"
    cols = int(sys.argv[2]) if len(sys.argv) > 2 else 160
    rows = int(sys.argv[3]) if len(sys.argv) > 3 else 44
    seconds = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0
    scale = int(sys.argv[5]) if len(sys.argv) > 5 else 6

    theme = os.environ.get("PREVIEW_THEME")
    if theme:
        name = None if theme == "current" else theme
        if not ft.apply_theme(ft.theme_colors(name)):
            raise SystemExit("could not read theme %s" % theme)

    random.seed(7)
    tank = ft.Tank(cols, rows, Opts())
    buf = [0] * (cols * rows * 2)

    dt = 1 / 24.0
    now = 1000.0
    steps = max(1, int(seconds / dt))
    feed_at = float(os.environ.get("PREVIEW_FEED", "-1"))
    for i in range(steps):
        now += dt
        if feed_at >= 0 and i == int(feed_at / dt):
            tank.feed(now)
        tank.update(dt, now)
    tank.draw(buf)

    label = os.environ.get("PREVIEW_LABEL")
    if label:
        ft.draw_label(tank, buf, label, 1.0)

    w, h = tank.w, tank.h
    out = []
    for y in range(h):
        line = bytearray()
        for x in range(w):
            c = buf[y * w + x]
            px = bytes(((c >> 16) & 255, (c >> 8) & 255, c & 255))
            line += px * scale
        for _ in range(scale):
            out.append(bytes(line))
    write_png(path, w * scale, h * scale, out)
    print("wrote %s (%dx%d)" % (path, w * scale, h * scale))


if __name__ == "__main__":
    main()
