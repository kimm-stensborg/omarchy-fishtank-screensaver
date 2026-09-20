#!/bin/bash
# Point Omarchy's screensaver at the fish tank, by shadowing the two commands
# it runs on a directory that comes earlier on PATH.
#
# Which directory that is depends on the machine. Omarchy ships its commands
# as /usr/bin/omarchy-* and only APPENDS ~/.local/bin to PATH, so on a stock
# install a symlink in ~/.local/bin is never reached and /usr/local/bin is the
# place to shadow from. Plenty of people prepend ~/.local/bin themselves,
# though, and then no root is needed. This works out which applies.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_BIN="$HOME/.local/bin"
SYSTEM_BIN="/usr/local/bin"
NAMES=(fishtank omarchy-screensaver omarchy-launch-screensaver)

mode=auto
for arg in "$@"; do
  case "$arg" in
  --user) mode=user ;;
  --system) mode=system ;;
  -h | --help)
    echo "Usage: ./install.sh [--user | --system]"
    echo
    echo "  --user     symlink into ~/.local/bin (no root; only works if that"
    echo "             directory comes before /usr/bin on PATH)"
    echo "  --system   symlink into /usr/local/bin (needs sudo; always works)"
    echo
    echo "With neither, the right one is worked out and used."
    exit 0
    ;;
  *)
    echo "unknown option: $arg" >&2
    exit 1
    ;;
  esac
done

command -v python3 >/dev/null || {
  echo "python3 is required but not on PATH." >&2
  exit 1
}

# Where a given PATH would find the command today, ignoring our own symlinks.
stock_dir() {
  local dir
  IFS=: read -ra dirs <<<"$1"
  for dir in "${dirs[@]}"; do
    [[ -x $dir/omarchy-launch-screensaver ]] || continue
    [[ $(readlink -f "$dir/omarchy-launch-screensaver" 2>/dev/null) == "$SRC"/* ]] && continue
    echo "$dir"
    return
  done
}

# True when `candidate` comes before the stock command on this PATH.
beats_stock() {
  local candidate="$1" path="$2" stock dir
  stock="$(stock_dir "$path")"
  [[ -n $stock ]] || return 0
  IFS=: read -ra dirs <<<"$path"
  for dir in "${dirs[@]}"; do
    [[ $dir == "$candidate" ]] && return 0
    [[ $dir == "$stock" ]] && return 1
  done
  return 1
}

# The screensaver is started from two places, and they do not share a PATH:
# the Omarchy menu runs it from a login shell, and the shell's idle service
# runs it with the Wayland session's environment. A user install has to win in
# both, so both are checked.
login_path="$(bash -lc 'printf %s "$PATH"' 2>/dev/null || printf %s "$PATH")"
session_path="$login_path"
session_pid="$(pgrep -u "$(id -u)" -f quickshell 2>/dev/null | head -1 || true)"
if [[ -n $session_pid && -r /proc/$session_pid/environ ]]; then
  found="$(tr '\0' '\n' </proc/"$session_pid"/environ | sed -n 's/^PATH=//p' | head -1)"
  [[ -n $found ]] && session_path="$found"
fi

if [[ $mode == auto ]]; then
  if beats_stock "$USER_BIN" "$login_path" && beats_stock "$USER_BIN" "$session_path"; then
    mode=user
  else
    mode=system
    echo "~/.local/bin does not come before Omarchy's own commands on PATH here,"
    echo "so installing into $SYSTEM_BIN instead (sudo)."
    echo
  fi
fi

if [[ $mode == user ]]; then
  BIN="$USER_BIN"
  SUDO=()
  mkdir -p "$BIN"
else
  BIN="$SYSTEM_BIN"
  SUDO=(sudo)
  ((EUID == 0)) && SUDO=()
fi

for name in "${NAMES[@]}"; do
  target="$BIN/$name"
  if [[ -e $target && ! -L $target ]]; then
    echo "Refusing to replace $target: it exists and is not a symlink." >&2
    exit 1
  fi
  "${SUDO[@]}" ln -sfn "$SRC/bin/$name" "$target"
  echo "linked $target -> $SRC/bin/$name"
done

# Say what will actually run, rather than assuming the symlinks took effect.
echo
ok=1
for context in login session; do
  path="$login_path"
  [[ $context == session ]] && path="$session_path"
  resolved="$(PATH="$path" command -v omarchy-launch-screensaver || true)"
  if [[ $(readlink -f "$resolved" 2>/dev/null) == "$SRC"/* ]]; then
    echo "  $context: $resolved  (the fish tank)"
  else
    echo "  $context: ${resolved:-not found}  (NOT the fish tank)"
    ok=0
  fi
done

echo
if ((ok)); then
  echo "Done. Try it with:  omarchy-launch-screensaver force"
  echo "Standalone:         fishtank        (Ctrl-C to quit)"
else
  echo "The screensaver will still be Omarchy's. Try:  sudo ./install.sh --system" >&2
  exit 1
fi
