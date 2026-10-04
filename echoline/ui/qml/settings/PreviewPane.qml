import QtQuick
import ".."

// A looping sample caption, styled exactly like the overlay, over a soft backdrop.
Rectangle {
    id: pane
    objectName: "previewPane"
    property var theme
    property var s
    property var sample
    implicitHeight: Math.max(140, box.height + 32)     // big fonts wrap; never clip the top rows
    radius: 10
    clip: true
    gradient: Gradient {
        GradientStop { position: 0; color: pane.theme.backdropTop }
        GradientStop { position: 1; color: pane.theme.backdropBottom }
    }

    Rectangle {
        id: box
        objectName: "previewCaption"
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 16 }
        width: Math.min(pane.width - 48, 520)
        height: Math.max(line.height, line.lineHeight) + 20
        radius: pane.s.corner_radius
        color: Qt.rgba(Qt.color(pane.s.background_color).r, Qt.color(pane.s.background_color).g,
                       Qt.color(pane.s.background_color).b, pane.s.background_opacity)

        CaptionLine {
            id: line
            objectName: "previewLine"
            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter
                      leftMargin: 16; rightMargin: 16 }
            words: pane.sample ? pane.sample.captions.latestWords : null
            s: pane.s
        }
    }
}
