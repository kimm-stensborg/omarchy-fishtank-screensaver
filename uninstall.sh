#!/bin/bash
# Remove the fish tank symlinks and hand the screensaver back to stock Omarchy.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"

for name in fishtank omarchy-screensaver; do
  target="$BIN/$name"
  if [[ -L $target && $(readlink -f "$target") == "$SRC/bin/$name" ]]; then
    rm "$target"
    echo "removed $target"
  fi
done

echo "Stock screensaver restored: $(command -v omarchy-screensaver)"
