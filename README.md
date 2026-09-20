# omarchy-fishtank-screensaver

An 8-bit fish tank that runs as the Omarchy screensaver.

![preview](preview.png)

Everything is drawn with half-block characters (`▀`) and truecolor, so one
terminal cell holds two square pixels and the whole thing is pixel art rather
than ASCII art. No dependencies beyond Python 3.

The Omarchy wordmark is etched into the back wall of the tank, read straight
from `$OMARCHY_PATH/logo.txt`. It is block art, so one character cell maps
onto two pixels and it lands on the pixel grid exactly. Thick strokes catch a
highlight on top and drop a shadow underneath, which makes it read as carved
glass rather than a sticker pasted on the water.

`--logo lockup` stacks the mark from `icon.txt` above the wordmark instead.
The mark is built on a 4x4 pixel grid, so it is only ever shrunk by a whole
number -- a fractional resize smears those strokes into grey mush. A tall tank
gets it at full size; a short one halves it so the lockup still fits above the
sand.

Sprites are sized from the tank, not in fixed pixels. The screensaver runs
foot at font size 18, which on a scaled laptop panel is about a hundred
columns -- half the grid of an everyday terminal -- so a fish measured in
pixels swells to a third of the screen there. Everything scales instead: fish
are a fraction of the canvas height, and the logo shrinks to fit a narrow
tank. The composition comes out the same whether it is a 106x60 canvas or a
240x120 one.

Swimming in the tank: generated fish species (each with a forked tail
that flaps, a dorsal fin, a gill line and a proper eye), a pufferfish, drifting
jellyfish, a crab that patrols the sand, bubbles from fish mouths and sand
vents, swaying seaweed, a sandcastle, a treasure chest, god rays from the
surface, drifting plankton and a rippling waterline.

## Keys

Four keys do things while the tank is running; every other key exits, so the
screensaver still behaves itself. They work the same when you run `fishtank`
in a terminal by hand.

| Key | Does |
| --- | --- |
| F1 | Next installed theme -- walks every theme in `~/.config/omarchy/themes` and `$OMARCHY_PATH/themes` |
| F2 | Back to the theme the desktop is wearing |
| F3 | Cycle the back wall: wordmark, lockup, mark, nothing |
| F4 | Feed the fish |

F1, F2 and F3 name what they just picked in the top-left corner, in the tank's
own pixels, and the text fades out after two seconds. **What you pick is what
the tank opens with next time** -- it is written to
`$XDG_STATE_HOME/fishtank/state.json` and read at startup, so you can leave
the screensaver on the theme you liked. A flag on the command line still wins
over the saved choice.

Switching theme repaints the tank you were already watching rather than
generating a new one: the layout seed is held across the rebuild, so the same
castle, the same weeds, in new colours.

### Feeding

F4 sprinkles food across the surface. Flakes sink and wobble; every fish has
its own eyesight, between roughly 24 and 68 pixels, so the shoal notices in
dribs rather than turning as one -- the near ones dart up first, the rest
drift over as the food falls into their range. A fish that reaches a flake
eats it and lets out a bubble. Whatever makes it to the sand is the crab's:
it drops its patrol, hurries over and cleans up. Anything still uneaten after
25 seconds dissolves.

## Following your Omarchy theme

The tank paints itself from the Omarchy theme you are running, by default.

```bash
fishtank                    # the theme in use (or the last one you picked with F1)
fishtank --theme gruvbox    # try one on without switching to it
fishtank --no-theme         # the built-in aquarium palette instead
```

The palette comes from `omarchy-theme-color`, the same resolver every other
Omarchy consumer uses, so a third-party theme that only defines `color0..15`
still works. Colours are chosen by hue rather than by name -- matte-black
calls a red "yellow" and rose-pine calls a blue "green" -- so the water takes
the coolest colour in the theme, the sand the warmest, the plants the
greenest, and the fish whatever is left that is loud. A theme with no cool
hue at all gets an inky tank rather than a mis-tinted one, and in a light
theme the logo is cut into the water darker instead of lighter.

`omarchy-launch-screensaver` takes no arguments of its own, so anything you
want the screensaver to run with goes in `~/.config/fishtank.conf`, one flag
per line:

```bash
printf -- '--logo lockup\n' > ~/.config/fishtank.conf
```

## Install

```bash
git clone https://github.com/kimm-stensborg/omarchy-fishtank-screensaver.git
cd omarchy-fishtank-screensaver
./install.sh
```

That symlinks `bin/fishtank` and `bin/omarchy-screensaver` into `~/.local/bin`,
which sits ahead of `/usr/share/omarchy/bin` on `PATH`. Omarchy's own
`omarchy-launch-screensaver` keeps doing the work — one terminal per monitor,
right font, right window class — it just finds this `omarchy-screensaver`
first. Nothing under `/usr/share/omarchy` is touched, so an `omarchy update`
will not fight with it, and `./uninstall.sh` hands the screensaver straight
back to stock.

Omarchy has no channel of its own for sharing screensavers: officially you
swap the ASCII art (`omarchy branding screensaver`), and the shell's plugin
system is for Quickshell components, which this is not. So this follows what
other third-party screensavers do -- a git repo and an install script that
points the screensaver at another program. Shadowing the binary on `PATH` is
the lightest version of that: no shell plugin is cloned, no launcher is
rewritten, and idle timing, "stay awake" and the lock screen keep working
exactly as they were.

Try it:

```bash
omarchy-launch-screensaver force   # the real thing, any key exits
fishtank                           # just the tank, Ctrl-C exits
```

### Requirements

Omarchy 4, Python 3 (no third-party modules), and a terminal the stock
screensaver already supports: Alacritty, Foot, Ghostty or Kitty. Truecolor is
assumed, which all four do.

## Uninstall

```bash
./uninstall.sh            # back to the stock Omarchy screensaver
./uninstall.sh --purge    # and delete ~/.config/fishtank.conf too
```

It removes the two symlinks and the saved F-key state, then checks what
`omarchy-launch-screensaver` will find from now on and prints it, exiting
non-zero if anything is still shadowing the stock binary. Since nothing else
was ever touched -- no files under `/usr/share/omarchy`, no plugin clone, no
edited launcher, no Hyprland config -- that is the whole of it: the next idle
timeout gives you Omarchy's own screensaver back.

It only deletes symlinks that point at a checkout of this project, so a
`fishtank` or `omarchy-screensaver` of your own in `~/.local/bin` is reported
and left alone. It is safe to run twice, and it works from any clone -- you do
not need the one you installed from.

## Options

```
fishtank [--theme [NAME] | --no-theme]
         [--fps N] [--fish N] [--seed N] [--frames N]
         [--logo wordmark|lockup|mark|PATH|none] [--logo-opacity F]
         [--exit-on-key] [--exit-on-unfocus CLASS]
```

| Flag | Meaning |
| --- | --- |
| `--theme` | Omarchy theme to paint the tank from; the one in use by default, or name one to preview it. |
| `--no-theme` | Use the built-in aquarium palette instead. |
| `--fps` | Frame rate, default 24. |
| `--fish` | How many fish; by default it scales with the size of the terminal. |
| `--seed` | Fixed layout, handy for screenshots. |
| `--frames` | Render N frames and quit (testing). |
| `--logo` | What to etch on the back wall: `wordmark` (the default), `lockup` for the mark above the wordmark, `mark`, a path to your own text art, or `none`. |
| `--logo-opacity` | How strongly it shows through, default `0.26`. |
| `--exit-on-key` | Quit on any keypress — screensaver mode. |
| `--exit-on-unfocus` | Quit when the given Hyprland window class loses focus. |

A full-screen tank costs a couple of milliseconds per frame, so at 24 fps it
idles at a few percent of one core.

## Development

```bash
tools/preview.py out.png [cols] [rows] [seconds] [scale]   # one frame as a PNG
tools/sheet.py sheet.png [scale] [fish-width]              # every sprite, big

PREVIEW_THEME=gruvbox tools/preview.py out.png                # themed preview
PREVIEW_LOGO=lockup tools/preview.py out.png                  # pick the logo
PREVIEW_FEED=0.5 tools/preview.py out.png                     # mid-feed
PREVIEW_LABEL="tokyo night" tools/preview.py out.png          # with the corner label
```

The fish are generated rather than hand-drawn: `fish_art()` in `bin/fishtank`
paints a tail fan, a teardrop body over its root, fins, a pattern (`bands`,
`stripe`, `spots` or `plain`), a face, and then a dark outline around the lot.
A species is one row in `SPECIES` — body, belly, accent and pattern — so adding
a new fish is a one-line change. The hand-drawn sprites (puffer, jellyfish,
crab, castle, chest) are plain string art with a palette dict next to them.
