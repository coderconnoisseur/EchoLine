import QtQuick

// Newest utterance as one block; cross-fades when a new utterance starts.
Item {
    id: root
    objectName: "subtitleView"
    required property var s
    required property real lineHeight
    property int shownId: -1
    implicitHeight: lineHeight * s.line_count
    clip: true

    Text {
        id: subtitleText
        objectName: "subtitleText"
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        wrapMode: Text.Wrap
        horizontalAlignment: Text.AlignHCenter
        color: root.s.text_color
        font.family: root.s.font_family
        font.pixelSize: root.s.font_size
        font.weight: root.s.font_weight
        lineHeight: 1.15
        style: ({ "outline": Text.Outline, "shadow": Text.Raised, "none": Text.Normal })[root.s.outline]
        styleColor: root.s.outline_color
        text: captions.latestText
    }

    SequentialAnimation {
        id: crossFade
        NumberAnimation { target: subtitleText; property: "opacity"; to: 0; duration: 150 }
        NumberAnimation { target: subtitleText; property: "opacity"; to: 1; duration: 150 }
    }

    Connections {
        target: captions
        function onLatestChanged() {
            if (captions.latestId !== root.shownId) {
                if (root.shownId !== -1)
                    crossFade.restart()
                root.shownId = captions.latestId
            }
        }
    }
}
