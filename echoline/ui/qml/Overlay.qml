import QtQuick
import QtQuick.Window

Window {
    id: overlay
    objectName: "overlay"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    color: "transparent"
    visible: true
    width: Screen.width * 0.35
    height: panel.implicitHeight
    x: (Screen.width - width) / 2
    y: Screen.height * 0.85 - height / 2

    readonly property int fontSize: 26
    readonly property real lineHeight: metrics.height * 1.15

    FontMetrics { id: metrics; font.pixelSize: overlay.fontSize; font.family: "Segoe UI" }

    Shortcut { sequences: ["Ctrl+Q", "Escape"]; onActivated: Qt.quit() }

    Rectangle {
        id: panel
        anchors.fill: parent
        implicitHeight: content.implicitHeight + 24
        radius: 14
        color: Qt.rgba(0, 0, 0, 0.72)

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
                color: status.state === "no-device" ? "#b3261e" : "#5a5a5a"
                width: statusText.implicitWidth + 20
                height: statusText.implicitHeight + 6
                anchors.horizontalCenter: parent.horizontalCenter
                Text {
                    id: statusText
                    anchors.centerIn: parent
                    color: "white"
                    font.pixelSize: 13
                    text: ({ "loading": "Loading speech model…", "no-device": "No audio device",
                             "lagging": "Catching up…" })[status.state] || status.state
                }
            }

            ListView {
                id: captionList
                objectName: "captionList"
                width: parent.width
                height: overlay.lineHeight * maxLines
                clip: true
                interactive: false
                model: captions
                spacing: 0

                onContentHeightChanged: scrollToEnd.restart()
                onCountChanged: scrollToEnd.restart()
                Timer { id: scrollToEnd; interval: 0; onTriggered: captionList.positionViewAtEnd() }
                Behavior on contentY { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

                delegate: Text {
                    required property var model
                    width: captionList.width
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignHCenter
                    color: "white"
                    opacity: model.final ? 1.0 : 0.85
                    font.pixelSize: overlay.fontSize
                    font.family: "Segoe UI"
                    lineHeight: 1.15
                    style: Text.Outline
                    styleColor: Qt.rgba(0, 0, 0, 0.6)
                    text: model.text
                    Behavior on opacity { NumberAnimation { duration: 120 } }
                }

                add: Transition {
                    NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 }
                    NumberAnimation { property: "y"; from: captionList.height; duration: 180; easing.type: Easing.OutCubic }
                }
                remove: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 160 } }
                displaced: Transition { NumberAnimation { property: "y"; duration: 180; easing.type: Easing.OutCubic } }
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
}
