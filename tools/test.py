#!/usr/bin/env python3
"""Checks that have caught real bugs in this project, run in one go.

    tools/test.py [--quick]

Every case here stands for something that actually broke once: a theme whose
colours are named for other colours, a canvas too small for the logo, a state
file from a previous run, symlinks that PATH never reaches.
"""

import importlib.util
import json
import os
import random
import subprocess
import sys
import tempfile
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
loader = SourceFileLoader("fishtank", os.path.join(ROOT, "bin", "fishtank"))
spec = importlib.util.spec_from_loader("fishtank", loader)
ft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ft)

QUICK = "--quick" in sys.argv
DEVNULL = open(os.devnull, "w")

# Canvases that matter: a degenerate terminal, the screensaver on a scaled
# laptop panel, on 1440p at font 12 and at font 10, and an everyday terminal.
SIZES = [(20, 8), (96, 30), (160, 45), (266, 68), (320, 81), (240, 60)]
if QUICK:
    SIZES = [(20, 8), (160, 45), (320, 81)]

failures = []
checks = 0


def check(name, condition, detail=""):
    global checks
    checks += 1
    if not condition:
        failures.append("%s%s" % (name, (": " + detail) if detail else ""))


def run_tank(cols, rows, opts, frames=25, feed=False):
    """Build a tank, run it, draw it, render it. Returns the tank."""
    random.seed(7)
    tank = ft.Tank(cols, rows, opts)
    buf = [0] * (cols * rows * 2)
    now = 1000.0
    if feed:
        tank.feed(now)
    for _ in range(frames):
        now += 1 / 24.0
        tank.update(1 / 24.0, now)
        tank.draw(buf)
    ft.draw_label(tank, buf, "checking one two", 1.0)
    ft.render(buf, cols, rows, DEVNULL)
    return tank, buf


class Opts:
    fish = None
    logo = "wordmark"
    logo_opacity = 0.26


# -- the scene, at every size that matters ----------------------------------

for cols, rows in SIZES:
    try:
        tank, buf = run_tank(cols, rows, Opts(), feed=True)
        check("draws %dx%d" % (cols, rows), True)
        check("buffer %dx%d stays in range" % (cols, rows),
              all(0 <= v <= 0xFFFFFF for v in buf))
        fish = [a for a in tank.actors if isinstance(a, ft.Fish)]
        check("%dx%d has fish" % (cols, rows), len(fish) > 0)
        widest = max(f.w for f in fish)
        check("%dx%d fish fit the tank" % (cols, rows), widest <= max(9, tank.w // 2),
              "widest %d of %d" % (widest, tank.w))
        if tank.w >= 96:
            heights = {f.h for f in fish}
            check("%dx%d fish vary in size" % (cols, rows), len(heights) >= 3,
                  "only %s" % sorted(heights))
    except Exception as error:                      # noqa: BLE001
        check("draws %dx%d" % (cols, rows), False, repr(error))

# -- every installed theme ---------------------------------------------------

themes = ft.installed_themes()
check("themes are found", len(themes) > 0)
for name in themes:
    colours = ft.theme_colors(name)
    if not colours:
        check("theme %s has colours" % name, False)
        continue
    check("theme %s applies" % name, ft.apply_theme(colours))
    # A theme must not leave the scene unreadable: water and sand have to
    # differ, whatever the theme calls its colours.
    gap = sum(abs(a - b) for a, b in zip(ft.WATER_TOP, ft.SAND))
    check("theme %s separates water from sand" % name, gap > 60, "gap %d" % gap)
    if not QUICK:
        try:
            run_tank(160, 45, Opts(), frames=8)
        except Exception as error:                  # noqa: BLE001
            check("theme %s draws" % name, False, repr(error))
ft.restore_palette()

# -- logos, including the narrow tank that used to overflow ------------------

for mode in ("wordmark", "lockup", "mark", "none"):
    opts = Opts()
    opts.logo = mode
    for cols, rows in ((96, 30), (266, 68)):
        tank, _ = run_tank(cols, rows, opts, frames=3)
        width = len({i % tank.w for i, _, _ in tank.logo}) if tank.logo else 0
        check("logo %s fits %dx%d" % (mode, cols, rows), width <= tank.w,
              "%d wide in %d" % (width, tank.w))
        if mode != "none" and cols >= 96:
            check("logo %s appears at %dx%d" % (mode, cols, rows), width > 0)

check("a missing logo file is survivable", ft.find_logo("/nope/missing.txt") is None)

# -- generated art at a range of sizes --------------------------------------

for size in (4, 5, 7, 11, 19):
    rows_art, palette = ft.fish_art(max(9, int(size / 0.44)), size, ft.SPECIES[0], 0)
    sprite = ft.Sprite.from_art(rows_art, palette)
    check("fish art at h=%d has pixels" % size, len(sprite.pixels) > 0)
for h in (7, 14, 30):
    art = ft.make_castle(int(h * 1.55), h)
    check("castle at h=%d is solid" % h, sum(row.count("s") for row in art) > h)
for size in (5, 9, 17):
    check("puffer at %d is round" % size,
          len(ft.Sprite.from_art(ft.make_puffer(size), ft.PUFFER_PALETTE).pixels) > size)
for w in (5, 9, 17):
    check("jelly at %d has tentacles" % w,
          any("t" in row for row in ft.make_jelly(w, int(w * 1.6))))

# -- keys --------------------------------------------------------------------

for code, want in ((b"\x1bOP", 1), (b"\x1b[11~", 1), (b"\x1bOQ", 2),
                   (b"\x1bOR", 3), (b"\x1bOS", 4), (b"q", None), (b"\x1b", None)):
    check("key %r reads as %s" % (code, want), ft.function_key(code) == want)

# -- state round-trip --------------------------------------------------------

with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, XDG_STATE_HOME=tmp)
    script = ("import importlib.util,os,json;"
              "from importlib.machinery import SourceFileLoader;"
              "l=SourceFileLoader('ft',%r);"
              "sp=importlib.util.spec_from_loader('ft',l);"
              "ft=importlib.util.module_from_spec(sp);sp.loader.exec_module(ft);"
              "ft.save_state(theme='gruvbox');"
              "print(json.dumps(ft.load_state()));"
              "print(ft.state_mtime() > 0)" % os.path.join(ROOT, "bin", "fishtank"))
    out = subprocess.run([sys.executable, "-c", script], capture_output=True,
                         text=True, env=env).stdout.splitlines()
    check("state round-trips", out and json.loads(out[0]).get("theme") == "gruvbox",
          str(out))
    check("state has an mtime", len(out) > 1 and out[1] == "True")

# -- the program itself ------------------------------------------------------

for args in (["--frames", "2"], ["--frames", "2", "--no-theme"],
             ["--frames", "2", "--theme", "gruvbox"], ["--frames", "2", "--logo", "lockup"]):
    done = subprocess.run([os.path.join(ROOT, "bin", "fishtank")] + args,
                          capture_output=True, text=True)
    check("fishtank %s exits 0" % " ".join(args), done.returncode == 0, done.stderr.strip())

done = subprocess.run([os.path.join(ROOT, "bin", "fishtank"), "--frames", "1",
                       "--theme", "definitely-not-a-theme"], capture_output=True, text=True)
check("a named theme that does not exist fails loudly", done.returncode == 1)

# -- install and uninstall, in a home of their own ---------------------------

if not QUICK:
    with tempfile.TemporaryDirectory() as home:
        env = dict(os.environ, HOME=home, XDG_STATE_HOME=os.path.join(home, "state"))
        env["PATH"] = os.path.join(home, ".local", "bin") + ":" + env["PATH"]
        done = subprocess.run(["./install.sh", "--user"], cwd=ROOT, env=env,
                              capture_output=True, text=True)
        links = os.path.join(home, ".local", "bin")
        for name in ("fishtank", "omarchy-screensaver", "omarchy-launch-screensaver"):
            check("install links %s" % name, os.path.islink(os.path.join(links, name)),
                  done.stdout + done.stderr)

        # A file someone else put there must survive.
        with open(os.path.join(links, "keep-me"), "w") as fh:
            fh.write("#!/bin/sh\n")
        done = subprocess.run(["./uninstall.sh"], cwd=ROOT, env=env,
                              capture_output=True, text=True)
        for name in ("fishtank", "omarchy-screensaver", "omarchy-launch-screensaver"):
            check("uninstall removes %s" % name,
                  not os.path.exists(os.path.join(links, name)))
        check("uninstall leaves other files alone",
              os.path.exists(os.path.join(links, "keep-me")))
        check("uninstall removes saved state",
              not os.path.exists(os.path.join(home, "state", "fishtank")))

# -- shell scripts parse -----------------------------------------------------

for script in ("install.sh", "uninstall.sh", "bin/omarchy-screensaver",
               "bin/omarchy-launch-screensaver"):
    done = subprocess.run(["bash", "-n", os.path.join(ROOT, script)],
                          capture_output=True, text=True)
    check("%s parses" % script, done.returncode == 0, done.stderr.strip())


print("%d checks, %d failed" % (checks, len(failures)))
for line in failures:
    print("  FAIL  %s" % line)
sys.exit(1 if failures else 0)
