import QtQuick
import QtQuick.Window

Window {
    id: overlay
    objectName: "overlay"
    readonly property var s: settingsStore.values
    flags: Qt.FramelessWindowHint | Qt.Tool | (s.always_on_top ? Qt.WindowStaysOnTopHint : 0)
    color: "transparent"
    visible: true
    width: Screen.width * s.width_percent / 100
    height: Math.min(panel.implicitHeight, Screen.height * 0.4)
    x: (Screen.width - width) / 2
    y: Screen.height * 0.85 - height / 2

    readonly property real lineHeight: metrics.height * 1.15

    FontMetrics {
        id: metrics
        font.family: overlay.s.font_family
        font.pixelSize: overlay.s.font_size
        font.weight: overlay.s.font_weight
    }

    Shortcut { sequences: ["Ctrl+Q", "Escape"]; onActivated: Qt.quit() }

    Rectangle {
        id: panel
        objectName: "panel"
        anchors.fill: parent
        implicitHeight: content.implicitHeight + 24
        radius: overlay.s.corner_radius
        color: Qt.alpha(overlay.s.background_color, overlay.s.background_opacity)

        DragHandler { target: null; onActiveChanged: if (active) overlay.startSystemMove() }

        Column {
            id: content
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
                             "lagging": "Catching up…" })[status.state] || status.state
                }
            }

            ListView {
                id: captionList
                objectName: "captionList"
                width: parent.width
                visible: overlay.s.caption_mode === "rolling"
                height: visible ? overlay.lineHeight * overlay.s.line_count : 0
                clip: true
                interactive: false
                model: captions
                spacing: 0

                onContentHeightChanged: scrollToEnd.restart()
                onCountChanged: scrollToEnd.restart()
                onHeightChanged: scrollToEnd.restart()
                Timer { id: scrollToEnd; interval: 0; onTriggered: captionList.positionViewAtEnd() }
                Behavior on contentY { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

                delegate: CaptionText {
                    required property var model
                    width: captionList.width
                    text: model.text
                    opacity: model.final ? 1.0 : 0.85
                    Behavior on opacity { NumberAnimation { duration: 120 } }
                }

                add: Transition {
                    NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 }
                    NumberAnimation { property: "y"; from: captionList.height; duration: 180; easing.type: Easing.OutCubic }
                }
                remove: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 160 } }
                displaced: Transition { NumberAnimation { property: "y"; duration: 180; easing.type: Easing.OutCubic } }
            }

            SubtitleView {
                width: parent.width
                height: visible ? implicitHeight : 0
                visible: overlay.s.caption_mode === "subtitle"
                s: overlay.s
                lineHeight: overlay.lineHeight
            }

            Text {
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
