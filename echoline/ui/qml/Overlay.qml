import QtQuick
import QtQuick.Controls
import QtQuick.Window

Window {
    id: overlay
    objectName: "overlay"
    readonly property var s: settingsStore.values
    // All flags live in this one binding; setting any of them from Python would be
    // undone the next time a setting changes and this re-evaluates.
    flags: Qt.FramelessWindowHint | Qt.Tool | (s.always_on_top ? Qt.WindowStaysOnTopHint : 0)
           | (s.click_through ? Qt.WindowTransparentForInput : 0)
    color: "transparent"
    visible: true
    // Width is set imperatively so a drag-resize from the edge does not fight a binding.
    // Only when width_percent itself changes, or other setting changes would undo a resize.
    property int appliedPercent: -1
    function applyWidth() {
        if (s.width_percent !== appliedPercent) {
            appliedPercent = s.width_percent
            width = Screen.width * s.width_percent / 100
        }
    }
    Component.onCompleted: applyWidth()
    Connections { target: settingsStore; function onValuesChanged() { overlay.applyWidth() } }
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

    property int autoHideDelay: 5000
    property bool quiet: false
    readonly property bool attention: status.state !== "listening" || status.notice !== ""
    Timer {
        id: quietTimer
        interval: overlay.autoHideDelay
        running: overlay.s.auto_hide
        onTriggered: overlay.quiet = true
    }
    Connections {
        target: captions
        function onLatestChanged() { overlay.quiet = false; quietTimer.restart() }
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
        // Auto-hide: fade out after silence, but never over a status message or while hovered.
        readonly property bool faded: overlay.s.auto_hide && overlay.quiet && !overlay.attention && !overlayHover.active
        opacity: faded ? 0 : 1
        Behavior on opacity { NumberAnimation { duration: panel.faded ? 400 : 150 } }

        DragHandler {
            target: null
            onActiveChanged: if (active) {
                if (controller)
                    controller.dragStarted()
                overlay.startSystemMove()
            }
        }

        HoverHandler {
            id: overlayHover
            objectName: "overlayHover"
            property bool forceHovered: false        // for tests
            readonly property bool active: hovered || forceHovered
            onActiveChanged: if (!active) hoverGrace.restart()
        }
        Timer { id: hoverGrace; interval: 600 }

        HoverBar {
            anchors { top: parent.top; right: parent.right; margins: 6 }
            z: 2
            opacity: overlayHover.active || hoverGrace.running ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: 200 } }
        }

        component ResizeEdge: MouseArea {
            property int edge
            width: 8
            anchors { top: parent.top; bottom: parent.bottom }
            cursorShape: Qt.SizeHorCursor
            visible: overlayHover.active
            onPressed: {
                if (controller)
                    controller.dragStarted()     // a resized overlay is no longer snapped
                overlay.startSystemResize(edge)
            }
        }
        ResizeEdge { anchors.left: parent.left; edge: Qt.LeftEdge }
        ResizeEdge { anchors.right: parent.right; edge: Qt.RightEdge }

        TapHandler {
            acceptedButtons: Qt.RightButton
            onTapped: contextMenu.popup()
        }
        Menu {
            id: contextMenu
            MenuItem { text: "Settings…"; onTriggered: controller.openSettings() }
            MenuItem { text: "Hide captions"; onTriggered: controller.hide() }
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
                visible: status.state !== "listening" || status.notice !== ""
                radius: height / 2
                color: ["no-device", "no-microphone", "model-error"].indexOf(status.state) >= 0 ? "#b3261e" : "#5a5a5a"
                width: statusText.implicitWidth + 20
                height: statusText.implicitHeight + 6
                anchors.horizontalCenter: parent.horizontalCenter
                Text {
                    id: statusText
                    anchors.centerIn: parent
                    color: "white"
                    font.pixelSize: 13
                    text: status.notice !== "" ? status.notice : ({ "loading": "Loading speech model…", "no-device": "No audio device", "paused": "Paused",
                             "no-microphone": "No microphone — check Windows privacy settings",
                             "model-error": "Speech model unavailable — check your connection and restart",
                             "settings-reset": "Settings were damaged and have been reset",
                             "lagging": "Falling behind — try a smaller model" })[status.state] || status.state
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
