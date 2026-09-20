#!/usr/bin/env python3
"""Render every species (and the hand-drawn sprites) onto one PNG sheet."""
import os, sys
from importlib.machinery import SourceFileLoader
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
loader = SourceFileLoader("fishtank", os.path.join(HERE, "..", "bin", "fishtank"))
spec = importlib.util.spec_from_loader("fishtank", loader)
ft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ft)
sys.path.insert(0, HERE)
from preview import write_png

path = sys.argv[1] if len(sys.argv) > 1 else "sheet.png"
scale = int(sys.argv[2]) if len(sys.argv) > 2 else 10
bw = int(sys.argv[3]) if len(sys.argv) > 3 else 17

sprites = []
for sp in ft.SPECIES:
    bh = max(5, int(bw * 0.44) | 1)
    sprites.append(ft.build_fish_frames(bw, bh, sp)[0])
sprites.append(ft.Sprite.from_art(ft.PUFFER_ART, ft.PUFFER_PALETTE))
sprites.append(ft.Sprite.from_art(ft.JELLY_ART, ft.JELLY_PALETTE))
sprites.append(ft.Sprite.from_art(ft.CRAB_ART, ft.CRAB_PALETTE))

cell_w = max(s.w for s in sprites) + 2
cell_h = max(s.h for s in sprites) + 2
cols = 4
rows = (len(sprites) + cols - 1) // cols
W, H = cell_w * cols, cell_h * rows
buf = [ft.pack((8, 24, 52))] * (W * H)
for i, s in enumerate(sprites):
    ox = (i % cols) * cell_w + 1
    oy = (i // cols) * cell_h + 1
    for x, y, c in s.pixels:
        buf[(oy + y) * W + ox + x] = c

out = []
for y in range(H):
    line = bytearray()
    for x in range(W):
        c = buf[y * W + x]
        line += bytes(((c >> 16) & 255, (c >> 8) & 255, c & 255)) * scale
    for _ in range(scale):
        out.append(bytes(line))
write_png(path, W * scale, H * scale, out)
print("wrote", path, W * scale, H * scale)
