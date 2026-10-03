import QtQuick
import "captions.js" as Captions

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

    readonly property string latestMarkup: Captions.markup(captions.latestText, captions.latestSettled,
                                                          s.unsettled_words, s.text_color)

    component SubtitleText: Text {
        textFormat: Text.StyledText
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
    }

    SubtitleText {
        id: outgoing
        objectName: "subtitleOutgoing"
        opacity: 0
    }

    SubtitleText {
        id: subtitleText
        objectName: "subtitleText"
        text: root.shownText
    }

    ParallelAnimation {
        id: crossFade
        NumberAnimation { target: outgoing; property: "opacity"; from: 1; to: 0; duration: 200 }
        NumberAnimation { target: subtitleText; property: "opacity"; from: 0; to: 1; duration: 200 }
    }

    // Follows caption updates and dim/hide switches alike. A new phrase with nothing
    // to show yet ("hide" mode) keeps the old one up instead of blanking the screen.
    onLatestMarkupChanged: {
        if (latestMarkup === "" && captions.latestId !== shownId)
            return
        if (captions.latestId !== shownId && shownId !== -1) {
            outgoing.text = shownText
            crossFade.restart()
        }
        shownId = captions.latestId
        shownText = latestMarkup
    }
}
