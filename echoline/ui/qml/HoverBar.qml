import QtQuick
import QtQuick.Controls

Row {
    id: bar
    objectName: "hoverBar"
    spacing: 2
    readonly property string glyphFont: "Segoe Fluent Icons, Segoe MDL2 Assets"

    component BarButton: ToolButton {
        property string glyph
        property string tip
        font.family: bar.glyphFont
        font.pixelSize: 14
        text: glyph
        implicitWidth: 30; implicitHeight: 30
        ToolTip.visible: hovered
        ToolTip.delay: 400
        ToolTip.text: tip
    }

    BarButton {
        objectName: "pauseButton"
        readonly property bool paused: controller ? controller.paused : false
        glyph: paused ? "" : ""
        tip: paused ? "Resume" : "Pause"
        onClicked: if (controller) controller.togglePause()
    }
    BarButton {
        objectName: "sourceButton"
        readonly property string source: controller ? controller.sourceName : "System audio"
        glyph: source === "Microphone" ? "" : ""
        tip: "Listening to: " + source + " — switch to " + (source === "Microphone" ? "System audio" : "Microphone")
        onClicked: if (controller) controller.toggleSource()
    }
    BarButton {
        objectName: "settingsButton"
        glyph: ""; tip: "Settings"
        onClicked: if (controller) controller.openSettings()
    }
    BarButton {
        objectName: "hideButton"
        glyph: ""; tip: "Hide captions (restore from the tray)"
        onClicked: if (controller) controller.hide()
    }
}
