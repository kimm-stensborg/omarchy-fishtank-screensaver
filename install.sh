#!/bin/bash
# Install the fish tank as the Omarchy screensaver by symlinking it into
# ~/.local/bin, which sits ahead of /usr/share/omarchy/bin on PATH.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"

mkdir -p "$BIN"

case ":$PATH:" in
*":$BIN:"*) ;;
*)
  echo "Warning: $BIN is not on your PATH -- the screensaver override will not take effect." >&2
  ;;
esac

for name in fishtank omarchy-screensaver omarchy-launch-screensaver; do
  target="$BIN/$name"
  if [[ -e $target && ! -L $target ]]; then
    echo "Refusing to replace $target: it exists and is not a symlink." >&2
    exit 1
  fi
  ln -sfn "$SRC/bin/$name" "$target"
  echo "linked $target -> $SRC/bin/$name"
done

echo
echo "Done. Try it with:  omarchy-launch-screensaver force"
echo "Standalone:         fishtank        (Ctrl-C to quit)"
