import QtQuick
import Quickshell
import Quickshell.Io

// The tank itself runs in a terminal, not in the shell, so there is nothing
// here to draw. What this gives the shell is a way in: start the screensaver
// now, or drop food into whatever tanks are already running, from a
// keybinding, the menu, or a script.
//
//   omarchy-shell io.github.kimm-stensborg.fishtank open
//   omarchy-shell io.github.kimm-stensborg.fishtank feed
//   omarchy-shell io.github.kimm-stensborg.fishtank stop
Item {
  id: root

  // Injected for third-party entry points that declare them.
  property var shell: null
  property var manifest: null

  readonly property string ipcTarget: "io.github.kimm-stensborg.fishtank"

  // One at a time is plenty: each of these is a fire-and-forget command that
  // finishes in milliseconds.
  function run(argv) {
    if (runner.running)
      runner.running = false
    runner.command = argv
    runner.running = true
  }

  Process {
    id: runner
  }

  IpcHandler {
    target: root.ipcTarget

    // Dive in now rather than waiting out the idle timeout.
    function open(): void {
      root.run(["omarchy-launch-screensaver", "force"])
    }

    // Food for every tank that is running, on every monitor.
    function feed(): void {
      root.run(["fishtank", "--feed"])
    }

    // The same as pressing a key at the screensaver.
    function stop(): void {
      root.run(["pkill", "-f", "org.omarchy.screensaver"])
    }
  }
}
