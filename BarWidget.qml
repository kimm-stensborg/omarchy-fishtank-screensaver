import QtQuick
import Quickshell
import qs.Ui

// A fish in the bar. Click it to dive into the tank now instead of waiting
// for the idle timeout; middle-click to drop food into whatever tanks are
// already running -- the request goes through the same state file the tanks
// watch for theme changes, so every monitor feeds at once.
BarWidget {
  id: root
  moduleName: "io.github.kimm-stensborg.fishtank"

  // Injected for third-party entry points that declare them.
  property var shell: null
  property var manifest: null

  // Fed a moment ago: the button lights up so the middle-click is not silent.
  property bool justFed: false

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function dive() {
    root.bar.run("omarchy-launch-screensaver force")
  }

  function feed() {
    root.bar.run("fishtank --feed")
    root.justFed = true
    fedTimer.restart()
  }

  Timer {
    id: fedTimer
    interval: 1600
    onTriggered: root.justFed = false
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰈺"
    active: root.justFed
    tooltipText: root.justFed
      ? "Food is in the water"
      : "Fish tank — click to dive in, middle-click to feed"
    onPressed: function (b) {
      if (b === Qt.MiddleButton)
        root.feed()
      else
        root.dive()
    }
  }
}
