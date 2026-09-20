#!/bin/bash
# Put the stock Omarchy screensaver back.
#
# The install only ever adds two symlinks in ~/.local/bin and, once you press
# a function key, a state file. Removing them is the whole job: nothing under
# /usr/share/omarchy was touched, no plugin was cloned, no config was edited.

set -euo pipefail

BIN="$HOME/.local/bin"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/fishtank"
CONFIG="$HOME/.config/fishtank.conf"

PURGE=0
for arg in "$@"; do
  case "$arg" in
  --purge) PURGE=1 ;;
  -h | --help)
    echo "Usage: ./uninstall.sh [--purge]"
    echo
    echo "  --purge   also delete ~/.config/fishtank.conf"
    exit 0
    ;;
  *)
    echo "unknown option: $arg" >&2
    exit 1
    ;;
  esac
done

removed=0
left_alone=()

for name in fishtank omarchy-screensaver; do
  target="$BIN/$name"
  [[ -e $target || -L $target ]] || continue

  if [[ ! -L $target ]]; then
    # Never delete a file someone else put there.
    left_alone+=("$target (not a symlink)")
    continue
  fi

  # Ours points at a checkout of this project -- any checkout, since the one
  # you installed from may have been moved or deleted since.
  dest="$(readlink "$target")"
  case "$dest" in
  */bin/fishtank | */bin/omarchy-screensaver)
    rm "$target"
    echo "removed $target"
    removed=$((removed + 1))
    ;;
  *)
    left_alone+=("$target -> $dest")
    ;;
  esac
done

if [[ -d $STATE ]]; then
  rm -rf "$STATE"
  echo "removed $STATE"
fi

if ((PURGE)) && [[ -f $CONFIG ]]; then
  rm "$CONFIG"
  echo "removed $CONFIG"
elif [[ -f $CONFIG ]]; then
  echo "kept $CONFIG (pass --purge to remove it)"
fi

if ((${#left_alone[@]})); then
  echo
  echo "Left alone, not installed by this project:"
  printf '  %s\n' "${left_alone[@]}"
fi

echo
if ((removed == 0)); then
  echo "Nothing to remove -- the fish tank was not installed."
fi

# Whatever `omarchy-launch-screensaver` will find from now on.
current="$(command -v omarchy-screensaver || true)"
case "$current" in
"$BIN/"*)
  echo "Warning: $current is still ahead on PATH." >&2
  exit 1
  ;;
"")
  echo "Warning: no omarchy-screensaver on PATH. Is Omarchy installed?" >&2
  exit 1
  ;;
*)
  echo "Stock screensaver restored: $current"
  ;;
esac
