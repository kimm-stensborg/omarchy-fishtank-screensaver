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
import time
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

# -- after dark, at every size -----------------------------------------------

for cols, rows in ((96, 30), (320, 81)):
    for level in (0.0, 0.5, 1.0):
        opts = Opts()
        opts.night = level
        try:
            tank, _ = run_tank(cols, rows, opts, frames=30, feed=True)
            check("draws %dx%d at night %.1f" % (cols, rows, level), True)
            check("night %.1f took" % level, abs(tank.night - level) < 0.001)
        except Exception as error:                  # noqa: BLE001
            check("draws %dx%d at night %.1f" % (cols, rows, level), False, repr(error))

# -- the cast, and that nothing swims through the castle --------------------

for cols, rows in ((160, 45), (320, 81)):
    tank, _ = run_tank(cols, rows, Opts(), frames=40)
    kinds = {type(a).__name__ for a in tank.actors}
    for wanted in ("Fish", "Seahorse", "BottomFeeder", "Crab", "Jelly"):
        check("%dx%d has a %s" % (cols, rows, wanted), wanted in kinds, str(sorted(kinds)))
    check("%dx%d has shoals" % (cols, rows), len(tank.schools) > 0)
    shoaling = [a for a in tank.actors if getattr(a, "school", None) is not None]
    check("%dx%d has fish in the shoals" % (cols, rows), len(shoaling) >= 3)
    inside = [a for a in tank.actors
              if isinstance(a, ft.Fish) and not isinstance(a, ft.BottomFeeder)
              and any(a.x + a.w > x0 and a.x < x1 and a.y + a.h > y0 and a.y < y1
                      for x0, y0, x1, y1 in tank.decor_boxes)]
    check("%dx%d: nothing swims through the scenery" % (cols, rows), not inside,
          "%d inside" % len(inside))
    check("%dx%d has scenery" % (cols, rows), len(tank.decor) > 0)
    check("%dx%d has a far layer" % (cols, rows), len(tank.backdrop) > 0)
    check("%dx%d has fronds up front" % (cols, rows), len(tank.front_weeds) > 0)

# -- one ocean across several monitors --------------------------------------

SCREENS = (("left", 0, 2560, 1440, 320, 81),
           ("middle", 2560, 2560, 1440, 320, 81),
           ("right", 5120, 1536, 960, 192, 60))
WORLD_W = 6656


def build_screen(offset, width, height, cols, rows):
    os.environ["FISHTANK_WORLD"] = "%d,%d,%d,%d" % (WORLD_W, offset, width, height)
    opts = Opts()
    opts.night = 0.0
    random.seed(5)
    return ft.Tank(cols, rows, opts)


try:
    screens = {name: build_screen(*rest) for name, *rest in
               ((s[0], s[1], s[2], s[3], s[4], s[5]) for s in SCREENS)}
    check("the ocean is picked up", all(t.world for t in screens.values()))
    check("every screen agrees how many fish are in the ocean",
          len({len(t.travellers) for t in screens.values()}) == 1)

    # The same fish, at the same moment, must be in one place in the world.
    clock = 1_000_000.0
    real_time = ft.time.time
    ft.time.time = lambda: clock
    try:
        for tank in screens.values():
            for passer in tank.travellers:
                passer.update(1 / 24.0, clock)
        places = []
        for name, tank in screens.items():
            passer = tank.travellers[0]
            offset = dict((s[0], s[1]) for s in SCREENS)[name]
            scale = dict((s[0], s[2]) for s in SCREENS)[name] / float(tank.w)
            places.append(offset + passer.x * scale)
        spread = max(places) - min(places)
        check("screens agree where a travelling fish is", spread < 40,
              "%.0f layout px apart" % spread)

        # With an ocean, the local fish turn back at the glass: anything
        # leaving the screen has genuinely gone to the next monitor.
        strays = []
        for name, tank in screens.items():
            for _ in range(200):
                tank.update(1 / 24.0, clock)
            strays += [a for a in tank.actors
                       if isinstance(a, ft.Fish) and (a.x < -1 or a.x > tank.w)]
        check("local fish stay on their own screen", not strays,
              "%d wandered off" % len(strays))

        # Feeding reaches the travelling fish, and every screen sends the
        # same ones after the same crumbs.
        feed_at = clock
        for tank in screens.values():
            tank.feed(1000.0, feed_at)
        lifts = {}
        for offset in (1.0, 2.5, 4.0):
            ft.time.time = lambda t=clock + offset: t
            for name, tank in screens.items():
                for passer in tank.travellers:
                    passer.update(1 / 24.0, clock + offset)
                lifts.setdefault(offset, {})[name] = {
                    p.index: round(p.snack(clock + offset)[0], 5)
                    for p in tank.travellers}
        ft.time.time = lambda: clock
        for offset, by_screen in lifts.items():
            values = list(by_screen.values())
            check("screens agree who is eating at +%.1fs" % offset,
                  all(v == values[0] for v in values))
            check("some travelling fish go for the food at +%.1fs" % offset,
                  any(v != 0 for v in values[0].values()))

        seen = [name for name, tank in screens.items()
                if -tank.travellers[0].w < tank.travellers[0].x < tank.w]
        check("a travelling fish is on some screen", len(seen) >= 1, str(seen))

        # Rebuilding a screen must not move the ocean. Both are read at the
        # same moment, since the checks above moved the clock on.
        again = build_screen(*SCREENS[0][1:])
        for passer in again.travellers + screens["left"].travellers:
            passer.update(1 / 24.0, clock)
        drift = abs(again.travellers[0].x - screens["left"].travellers[0].x)
        check("the ocean is the same after a rebuild", drift < 0.001,
              "moved %.2f" % drift)
    finally:
        ft.time.time = real_time
finally:
    os.environ.pop("FISHTANK_WORLD", None)

check("a single screen is its own ocean",
      (os.environ.update({"FISHTANK_WORLD": "2560,0,2560,1440"}) or
       ft.world_geometry()) is None)
os.environ.pop("FISHTANK_WORLD", None)

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

# -- scenery is different every time, and never stacked -------------------

layouts = set()
for seed in range(12):
    random.seed(seed)
    tank = ft.Tank(320, 81, Opts())
    spread = []
    for sprite, x, y in tank.decor:
        spread.append((x, x + sprite.w))
        check("scenery sits on the floor",
              y + sprite.h >= tank.floor and y >= 0)
    spread.sort()
    overlap = any(spread[i][1] > spread[i + 1][0] for i in range(len(spread) - 1))
    check("scenery does not stack up", not overlap, str(spread))
    layouts.add(tuple(sorted((x, s.w, s.h) for s, x, _ in tank.decor)))
check("scenery differs between tanks", len(layouts) >= 8,
      "%d different layouts in 12" % len(layouts))

for cols, rows in ((96, 30), (320, 81)):
    random.seed(2)
    tank = ft.Tank(cols, rows, Opts())
    check("%dx%d scenery fits the tank" % (cols, rows),
          all(x >= 0 and x + s.w <= tank.w for s, x, _ in tank.decor))

# -- the clock ---------------------------------------------------------------

for cols, rows in ((96, 30), (320, 81)):
    for hours in (12, 24):
        tank, buf = run_tank(cols, rows, Opts(), frames=2)
        before = list(buf)
        ft.draw_clock(tank, buf, hours)
        check("the %dh clock draws at %dx%d" % (hours, cols, rows), buf != before)
        # It belongs in the top corner, not over the sand.
        changed = [i for i, (a, b) in enumerate(zip(before, buf)) if a != b]
        check("the clock stays out of the way at %dx%d" % (cols, rows),
              all(i // tank.w < tank.h * 0.25 for i in changed))
        check("the clock keeps to the right at %dx%d" % (cols, rows),
              all(i % tank.w > tank.w * 0.5 for i in changed))

# -- keys --------------------------------------------------------------------

for code, want in ((b"\x1bOP", 1), (b"\x1b[11~", 1), (b"\x1bOQ", 2),
                   (b"\x1bOR", 3), (b"\x1bOS", 4), (b"\x1b[15~", 5),
                   (b"\x1b[17~", 6), (b"q", None), (b"\x1b", None)):
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
             ["--frames", "2", "--theme", "gruvbox"], ["--frames", "2", "--logo", "lockup"],
             ["--frames", "2", "--clock"], ["--frames", "2", "--clock", "12"],
             ["--frames", "2", "--no-clock"], ["--frames", "2", "--night", "1"],
             ["--frames", "2", "--no-ocean"]):
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

# -- feeding from outside, which is what the bar button does ----------------

with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, XDG_STATE_HOME=tmp)
    fishtank = os.path.join(ROOT, "bin", "fishtank")
    done = subprocess.run([fishtank, "--feed"], capture_output=True, text=True, env=env)
    check("--feed exits 0", done.returncode == 0, done.stderr.strip())
    state_path = os.path.join(tmp, "fishtank", "state.json")
    check("--feed leaves a request", os.path.exists(state_path))
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as fh:
            saved = json.load(fh)
        check("the request is recent", abs(saved.get("feed", 0) - time.time()) < 30)
        check("--feed keeps the rest of the state", "feed" in saved)

# -- the plugin contract -----------------------------------------------------

with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as fh:
    manifest = json.load(fh)
check("manifest is schema 1", manifest.get("schemaVersion") == 1)
check("manifest has an id", manifest.get("id", "").count(".") >= 2)
for kind in manifest.get("kinds", []):
    entry = {"bar-widget": "barWidget"}.get(kind, kind)
    target = manifest.get("entryPoints", {}).get(entry)
    check("kind %s has an entry point" % kind, bool(target))
    check("entry point %s exists" % target,
          target and os.path.exists(os.path.join(ROOT, target)))
check("the widget names the plugin id",
      manifest["id"] in open(os.path.join(ROOT, "BarWidget.qml"), encoding="utf-8").read())

if not QUICK:
    done = subprocess.run(["omarchy", "plugin", "validate", ROOT],
                          capture_output=True, text=True)
    if done.returncode == 127 or "not found" in done.stderr:
        pass                      # no Omarchy here; nothing to validate against
    else:
        check("omarchy accepts the plugin", done.returncode == 0,
              done.stdout + done.stderr)

# -- shell scripts parse -----------------------------------------------------

for script in ("install.sh", "uninstall.sh", "bin/omarchy-screensaver",
               "bin/omarchy-launch-screensaver",
               "packaging/omarchy-fishtank-screensaver"):
    done = subprocess.run(["bash", "-n", os.path.join(ROOT, script)],
                          capture_output=True, text=True)
    check("%s parses" % script, done.returncode == 0, done.stderr.strip())


# The package must not try to own a file the omarchy package already has.
with open(os.path.join(ROOT, "packaging", "PKGBUILD"), encoding="utf-8") as fh:
    pkgbuild = fh.read()
check("the package stays out of /usr/bin/omarchy-screensaver",
      '"$pkgdir/usr/bin/omarchy-screensaver"' not in pkgbuild)
check("the package ships the enable wrapper",
      "usr/bin/omarchy-fishtank-screensaver" in pkgbuild)

print("%d checks, %d failed" % (checks, len(failures)))
for line in failures:
    print("  FAIL  %s" % line)
sys.exit(1 if failures else 0)
