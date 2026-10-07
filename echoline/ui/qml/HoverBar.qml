import QtQuick
import QtQuick.Controls

Row {
    id: bar
    objectName: "hoverBar"
    spacing: 2

    component BarButton: ToolButton {
        id: button
        property string iconName
        property string tip
        contentItem: Item {
            Icon { anchors.centerIn: parent; name: button.iconName; size: 16; color: button.palette.buttonText }
        }
        implicitWidth: 30; implicitHeight: 30
        ToolTip.visible: hovered
        ToolTip.delay: 400
        ToolTip.text: tip
    }

    BarButton {
        objectName: "pauseButton"
        readonly property bool paused: controller ? controller.paused : false
        iconName: paused ? "play" : "pause"
        tip: paused ? "Resume" : "Pause"
        onClicked: if (controller) controller.togglePause()
    }
    BarButton {
        objectName: "sourceButton"
        readonly property string source: controller ? controller.sourceName : "System audio"
        iconName: source === "Microphone" ? "mic" : "speaker"
        tip: "Listening to: " + source + " — switch to " + (source === "Microphone" ? "System audio" : "Microphone")
        onClicked: if (controller) controller.toggleSource()
    }
    BarButton {
        objectName: "settingsButton"
        iconName: "settings"; tip: "Settings"
        onClicked: if (controller) controller.openSettings()
    }
    BarButton {
        objectName: "hideButton"
        iconName: "hide"; tip: "Hide captions (EchoLine keeps running in the tray)"
        onClicked: if (controller) controller.hide()
    }
}
