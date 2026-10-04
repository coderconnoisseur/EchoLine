import QtQuick

// Newest utterance as one block; the previous phrase fades out as the next fades in.
Item {
    id: root
    objectName: "subtitleView"
    required property var s
    required property real lineHeight
    property int shownId: -1
    property string shownText: ""
    implicitHeight: lineHeight * s.line_count
    clip: true

    // The phrase that is leaving, frozen as plain text while it fades.
    Text {
        id: outgoing
        objectName: "subtitleOutgoing"
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        opacity: 0
        wrapMode: Text.Wrap
        horizontalAlignment: Text.AlignHCenter
        color: root.s.text_color
        font.family: root.s.font_family
        font.pixelSize: root.s.font_size
        font.weight: root.s.font_weight
        lineHeight: 1.15
        style: ({ "outline": Text.Outline, "shadow": Text.Raised, "none": Text.Normal })[root.s.outline]
        styleColor: root.s.outline_color
    }

    CaptionLine {
        id: incoming
        objectName: "subtitleLine"
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        words: captions.latestWords
        s: root.s
    }

    ParallelAnimation {
        id: crossFade
        NumberAnimation { target: outgoing; property: "opacity"; from: 1; to: 0; duration: 200 * motion.scale }
        NumberAnimation { target: incoming; property: "opacity"; from: 0; to: 1; duration: 200 * motion.scale }
    }

    Connections {
        target: captions
        function onLatestChanged() {
            if (captions.latestId !== root.shownId && root.shownId !== -1) {
                outgoing.text = root.shownText
                crossFade.restart()
            }
            root.shownId = captions.latestId
            root.shownText = captions.latestText
        }
    }
}
