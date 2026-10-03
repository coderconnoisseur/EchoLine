import QtQuick
import QtQuick.Controls
import QtQuick.Window

Window {
    id: overlay
    objectName: "overlay"
    readonly property var s: settingsStore.values
    // Always on top until M3 adds a tray icon: a Tool window has no taskbar button,
    // so once covered by a full-screen video it could not be brought back.
    flags: Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
    color: "transparent"
    visible: true
    width: Screen.width * s.width_percent / 100
    height: Math.min(panel.implicitHeight, maxHeight)

    readonly property real lineHeight: metrics.height * 1.15
    readonly property real maxHeight: Screen.height * 0.4
    // Height left for captions once the status pill, latency line and padding are placed,
    // so a big font on a small screen shrinks the captions instead of spilling out.
    readonly property real captionRoom: maxHeight - 24
        - (statusPill.visible ? statusPill.height + content.spacing : 0)
        - (latencyText.visible ? latencyText.height + content.spacing : 0)
    readonly property real captionHeight: Math.min(lineHeight * s.line_count, captionRoom)

    FontMetrics {
        id: metrics
        font.family: overlay.s.font_family
        font.pixelSize: overlay.s.font_size
        font.weight: overlay.s.font_weight
    }

    Shortcut { sequences: ["Ctrl+Q", "Escape"]; onActivated: Qt.quit() }
    Shortcut { sequence: "Ctrl+,"; onActivated: controller.openSettings() }

    Rectangle {
        id: panel
        objectName: "panel"
        anchors.fill: parent
        implicitHeight: content.implicitHeight + 24
        radius: overlay.s.corner_radius
        color: Qt.alpha(overlay.s.background_color, overlay.s.background_opacity)

        DragHandler { target: null; onActiveChanged: if (active) overlay.startSystemMove() }

        TapHandler {
            acceptedButtons: Qt.RightButton
            onTapped: contextMenu.popup()
        }
        Menu {
            id: contextMenu
            MenuItem { text: "Settings…"; onTriggered: controller.openSettings() }
            MenuItem { text: "Quit"; onTriggered: controller.quit() }
        }

        Column {
            id: content
            objectName: "content"
            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 18 }
            spacing: 4

            Rectangle {
                id: statusPill
                objectName: "statusPill"
                visible: status.state !== "listening"
                radius: height / 2
                color: status.state === "no-device" || status.state === "model-error" ? "#b3261e" : "#5a5a5a"
                width: statusText.implicitWidth + 20
                height: statusText.implicitHeight + 6
                anchors.horizontalCenter: parent.horizontalCenter
                Text {
                    id: statusText
                    anchors.centerIn: parent
                    color: "white"
                    font.pixelSize: 13
                    text: ({ "loading": "Loading speech model…", "no-device": "No audio device",
                             "model-error": "Speech model unavailable — check your connection and restart",
                             "settings-reset": "Settings were damaged and have been reset",
                             "lagging": "Catching up…" })[status.state] || status.state
                }
            }

            // Lines stack in a column anchored to the bottom of a clipped area, so the
            // newest text always sits at the bottom edge whatever the fonts or wrapping.
            Item {
                id: captionArea
                objectName: "captionArea"
                width: parent.width
                visible: overlay.s.caption_mode === "rolling"
                height: visible ? overlay.captionHeight : 0
                clip: true

                Column {
                    id: captionColumn
                    anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                    move: Transition { NumberAnimation { property: "y"; duration: 180; easing.type: Easing.OutCubic } }

                    Repeater {
                        objectName: "captionLines"
                        model: captions
                        delegate: CaptionText {
                            required property var model
                            objectName: "captionLine"
                            property int utteranceId: model.utteranceId
                            width: captionColumn.width
                            text: model.text
                            opacity: 0
                            Component.onCompleted: opacity = Qt.binding(() => model.final ? 1.0 : 0.85)
                            Behavior on opacity { NumberAnimation { duration: 160 } }
                        }
                    }
                }
            }

            SubtitleView {
                width: parent.width
                height: visible ? overlay.captionHeight : 0
                visible: overlay.s.caption_mode === "subtitle"
                s: overlay.s
                lineHeight: overlay.lineHeight
            }

            Text {
                id: latencyText
                visible: status.showLatency
                anchors.horizontalCenter: parent.horizontalCenter
                color: "#bbbbbb"
                font.pixelSize: 11
                text: status.latency
            }
        }
    }

    component CaptionText: Text {
        wrapMode: Text.Wrap
        horizontalAlignment: Text.AlignHCenter
        color: overlay.s.text_color
        font.family: overlay.s.font_family
        font.pixelSize: overlay.s.font_size
        font.weight: overlay.s.font_weight
        lineHeight: 1.15
        style: ({ "outline": Text.Outline, "shadow": Text.Raised, "none": Text.Normal })[overlay.s.outline]
        styleColor: overlay.s.outline_color
    }
}
