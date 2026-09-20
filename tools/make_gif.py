#!/usr/bin/env python3
"""Render the tank to an animated GIF, or to a video.

    tools/make_gif.py out.gif [cols] [rows] [seconds] [scale] [fps]
    tools/make_gif.py out.mp4 …          # needs ffmpeg; anything ffmpeg writes

GIF89a is written by hand -- no Pillow, same as everything else here -- with
a palette built from the colours the frames actually use. A video is the raw
frames piped to ffmpeg, which keeps every colour instead of the 256 a GIF
allows.

    GIF_THEME=gruvbox GIF_NIGHT=0.85 GIF_FEED=2.5 GIF_PREDATOR=6 GIF_SEED=12
    GIF_COLORS=128
"""

import importlib.util
import os
import random
import struct
import sys
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.abspath(__file__))
loader = SourceFileLoader("fishtank", os.path.join(HERE, "..", "bin", "fishtank"))
spec = importlib.util.spec_from_loader("fishtank", loader)
ft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ft)


class Opts:
    fish = None
    logo = os.environ.get("GIF_LOGO", "wordmark")
    logo_opacity = 0.26
    night = float(os.environ["GIF_NIGHT"]) if os.environ.get("GIF_NIGHT") else 0.0
    ocean = False


def build_palette(counts, limit=256):
    """Keep the colours the tank actually leans on, then map the rest to the
    nearest of those. A fixed colour cube bands the water gradient badly;
    this keeps it smooth because the gradient's own colours are the common
    ones."""
    common = sorted(counts, key=counts.get, reverse=True)[:limit]
    palette = [((c >> 16) & 255, (c >> 8) & 255, c & 255) for c in common]
    index_of = {c: i for i, c in enumerate(common)}

    def lookup(colour):
        found = index_of.get(colour)
        if found is not None:
            return found
        r, g, b = (colour >> 16) & 255, (colour >> 8) & 255, colour & 255
        best, best_d = 0, None
        for i, (pr, pg, pb) in enumerate(palette):
            d = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
            if best_d is None or d < best_d:
                best, best_d = i, d
        index_of[colour] = best        # cached, so this runs once per colour
        return best

    return palette, lookup


def lzw(indices, bits):
    """Minimal LZW for GIF image data."""
    clear, end = 1 << bits, (1 << bits) + 1
    size = bits + 1
    table = {bytes([i]): i for i in range(1 << bits)}
    nxt = end + 1
    out, acc, nacc = bytearray(), 0, 0

    def emit(code):
        nonlocal acc, nacc
        acc |= code << nacc
        nacc += size
        while nacc >= 8:
            out.append(acc & 255)
            acc >>= 8
            nacc -= 8

    emit(clear)
    prefix = b""
    for value in indices:
        nextp = prefix + bytes([value])
        if nextp in table:
            prefix = nextp
            continue
        emit(table[prefix])
        table[nextp] = nxt
        nxt += 1
        if nxt > (1 << size) and size < 12:
            size += 1
        elif nxt > 4095:
            emit(clear)
            table = {bytes([i]): i for i in range(1 << bits)}
            nxt, size = end + 1, bits + 1
        prefix = bytes([value])
    if prefix:
        emit(table[prefix])
    emit(end)
    if nacc:
        out.append(acc & 255)
    return bytes(out)


def write_video(path, width, height, frames, fps):
    """Hand the frames to ffmpeg as raw RGB."""
    import shutil
    import subprocess
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is needed for %s" % path)
    done = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", "%dx%d" % (width, height), "-r", str(fps), "-i", "-",
         # Even dimensions and yuv420p, or half the players will not open it.
         "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", path],
        input=b"".join(frames))
    if done.returncode != 0:
        raise SystemExit("ffmpeg failed for %s" % path)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "preview.gif"
    cols = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    rows = int(sys.argv[3]) if len(sys.argv) > 3 else 38
    seconds = float(sys.argv[4]) if len(sys.argv) > 4 else 6.0
    scale = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    fps = int(sys.argv[6]) if len(sys.argv) > 6 else 12

    theme = os.environ.get("GIF_THEME")
    if theme:
        ft.apply_theme(ft.theme_colors(None if theme == "current" else theme))

    random.seed(int(os.environ.get("GIF_SEED", "12")))
    tank = ft.Tank(cols, rows, Opts())
    buf = [0] * (cols * rows * 2)
    width, height = tank.w * scale, tank.h * scale

    video = os.path.splitext(path)[1].lower() not in (".gif", "")

    # Render first, so the palette can be chosen from what is really there.
    raw, counts = [], {}
    now, dt = 1000.0, 1.0 / fps
    feed_at = float(os.environ.get("GIF_FEED", "-1"))
    hunter_at = float(os.environ.get("GIF_PREDATOR", "-1"))
    for step in range(int(seconds * fps)):
        now += dt
        if feed_at >= 0 and step == int(feed_at * fps):
            tank.feed(now)
        if hunter_at >= 0 and step == int(hunter_at * fps) and tank.predator:
            tank.predator.next_at = now        # stage it for the clip
        tank.update(dt, now)
        tank.draw(buf)
        frame = list(buf)
        raw.append(frame)
        for colour in frame:
            counts[colour] = counts.get(colour, 0) + 1

    if video:
        rows_out = []
        for frame in raw:
            line_cache = {}
            for y in range(tank.h):
                line = bytearray()
                for x in range(tank.w):
                    c = frame[y * tank.w + x]
                    line += bytes(((c >> 16) & 255, (c >> 8) & 255, c & 255)) * scale
                rows_out.append(bytes(line) * scale)
        stride = tank.h
        frames_bytes = [b"".join(rows_out[i * stride:(i + 1) * stride])
                        for i in range(len(raw))]
        write_video(path, width, height, frames_bytes, fps)
        print("wrote %s (%dx%d, %d frames, %.1fs)"
              % (path, width, height, len(raw), len(raw) / fps))
        return

    # One palette slot is kept back to mean "same as the frame before", which
    # is what makes a large GIF affordable: most of a tank holds still from
    # one frame to the next, and a run of "unchanged" compresses to nothing.
    # Fewer colours compress better, and a tank's gradient has more shades
    # than anyone can see. GIF_COLORS trades one against the other.
    palette, lookup = build_palette(counts, limit=int(os.environ.get("GIF_COLORS", "255")))
    transparent = len(palette)

    frames = []
    for frame in raw:
        indices = bytearray()
        for y in range(tank.h):
            row = bytearray()
            for x in range(tank.w):
                row += bytes([lookup(frame[y * tank.w + x])]) * scale
            for _ in range(scale):
                indices += row
        frames.append(bytes(indices))

    while len(palette) < 256:
        palette.append((0, 0, 0))

    def difference(previous, current):
        """The changed rectangle, with everything inside it that did not
        change marked transparent. Returns (left, top, w, h, pixels)."""
        left, right, top, bottom = width, -1, height, -1
        for y in range(height):
            base = y * width
            if previous[base:base + width] == current[base:base + width]:
                continue
            top = min(top, y)
            bottom = max(bottom, y)
            for x in range(width):
                if previous[base + x] != current[base + x]:
                    left = min(left, x)
                    right = max(right, x)
        if right < 0:
            return None
        box_w, box_h = right - left + 1, bottom - top + 1
        out = bytearray()
        for y in range(top, bottom + 1):
            base = y * width
            for x in range(left, right + 1):
                value = current[base + x]
                out.append(value if value != previous[base + x] else transparent)
        return left, top, box_w, box_h, bytes(out)

    with open(path, "wb") as fh:
        fh.write(b"GIF89a")
        fh.write(struct.pack("<HHBBB", width, height, 0xF7, 0, 0))
        for colour in palette:
            fh.write(bytes(colour))
        fh.write(b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00")   # loop forever
        delay = max(2, round(100 / fps))

        def put(left, top, box_w, box_h, data, transparent_flag):
            # Disposal 1: leave the frame in place for the next one to
            # paint over. Without it the transparent pixels show the page.
            flags = 0x04 | (0x01 if transparent_flag else 0x00)
            fh.write(b"\x21\xF9\x04" + bytes([flags])
                     + struct.pack("<H", delay)
                     + bytes([transparent if transparent_flag else 0]) + b"\x00")
            fh.write(b"\x2C" + struct.pack("<HHHHB", left, top, box_w, box_h, 0))
            fh.write(bytes([8]))
            packed = lzw(data, 8)
            for i in range(0, len(packed), 255):
                chunk = packed[i:i + 255]
                fh.write(bytes([len(chunk)]) + chunk)
            fh.write(b"\x00")

        put(0, 0, width, height, frames[0], False)
        for index in range(1, len(frames)):
            patch = difference(frames[index - 1], frames[index])
            if patch is None:                      # nothing moved
                put(0, 0, 1, 1, bytes([transparent]), True)
                continue
            put(patch[0], patch[1], patch[2], patch[3], patch[4], True)
        fh.write(b"\x3B")

    print("wrote %s (%dx%d, %d frames, %.1fs, %.1f KB)" %
          (path, width, height, len(frames), len(frames) / fps,
           os.path.getsize(path) / 1024))


if __name__ == "__main__":
    main()
