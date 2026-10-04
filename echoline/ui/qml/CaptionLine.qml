import QtQuick
import QtQuick.Effects

// One caption line laid out word by word, so words can fade in softly,
// cross-fade when corrected and glide when the line re-wraps.
Item {
    id: line
    required property var words
    required property var s
    readonly property string text: words ? words.text : ""
    readonly property real lineHeight: metrics.height * 1.15
    readonly property real ms: motion.scale
    property int rows: 0
    implicitHeight: rows * lineHeight
    height: implicitHeight

    FontMetrics {
        id: metrics
        font.family: line.s.font_family
        font.pixelSize: line.s.font_size
        font.weight: line.s.font_weight
    }

    onWidthChanged: Qt.callLater(relayout)
    onLineHeightChanged: Qt.callLater(relayout)

    // Greedy rows, each centered; Flow cannot center rows.
    function relayout() {
        const space = metrics.advanceWidth(" ")
        const rowsOut = []
        let current = [], used = 0
        for (let i = 0; i < repeater.count; i++) {
            const item = repeater.itemAt(i)
            if (!item)
                continue
            const w = item.implicitWidth
            const needed = current.length ? used + space + w : w
            if (current.length && needed > width) {
                rowsOut.push({ items: current, width: used })
                current = []
                used = 0
            }
            used = current.length ? used + space + w : w
            current.push(item)
        }
        if (current.length)
            rowsOut.push({ items: current, width: used })
        rows = rowsOut.length
        for (let r = 0; r < rowsOut.length; r++) {
            let x = Math.max(0, (width - rowsOut[r].width) / 2)
            for (const item of rowsOut[r].items) {
                item.place(x, r * lineHeight)
                x += item.implicitWidth + space
            }
        }
    }

    component WordText: Text {
        color: line.s.text_color
        font.family: line.s.font_family
        font.pixelSize: line.s.font_size
        font.weight: line.s.font_weight
        style: ({ "outline": Text.Outline, "shadow": Text.Raised, "none": Text.Normal })[line.s.outline]
        styleColor: line.s.outline_color
    }

    Repeater {
        id: repeater
        model: line.words
        onItemAdded: Qt.callLater(line.relayout)
        onItemRemoved: Qt.callLater(line.relayout)

        delegate: Item {
            id: word
            objectName: "word"
            required property string text
            required property bool settled
            property bool placed: false
            implicitWidth: label.implicitWidth
            width: implicitWidth
            height: line.lineHeight
            opacity: settled ? 1.0 : 0.55
            onImplicitWidthChanged: Qt.callLater(line.relayout)

            Behavior on opacity { NumberAnimation { duration: 200 * line.ms; easing.type: Easing.OutCubic } }
            Behavior on x { enabled: word.placed; NumberAnimation { duration: 220 * line.ms; easing.type: Easing.OutCubic } }
            Behavior on y { enabled: word.placed; NumberAnimation { duration: 220 * line.ms; easing.type: Easing.OutCubic } }

            function place(px, py) {
                x = px
                y = py
                if (!placed) {
                    placed = true
                    if (line.ms > 0)
                        entry.restart()
                }
            }

            onTextChanged: {
                if (ghost.text === "" && label.text === "") {
                    label.text = text
                    return
                }
                ghost.text = label.text
                label.text = text
                if (line.ms > 0)
                    correction.restart()
            }
            Component.onCompleted: label.text = text

            Item {
                id: body
                objectName: "body"
                width: word.width
                height: word.height
                layer.enabled: entry.running
                layer.effect: MultiEffect { blurEnabled: true; blurMax: 16; blur: body.blur }
                property real blur: 0
                property real drift: 0
                transform: Translate { y: body.drift }

                WordText { id: ghost; opacity: 0 }
                WordText { id: label }
            }

            ParallelAnimation {
                id: entry
                NumberAnimation { target: body; property: "opacity"; from: 0; to: 1; duration: 180 * line.ms; easing.type: Easing.OutCubic }
                NumberAnimation { target: body; property: "drift"; from: 6; to: 0; duration: 180 * line.ms; easing.type: Easing.OutCubic }
                NumberAnimation { target: body; property: "blur"; from: 0.6; to: 0; duration: 180 * line.ms; easing.type: Easing.OutCubic }
            }

            ParallelAnimation {
                id: correction
                NumberAnimation { target: ghost; property: "opacity"; from: 1; to: 0; duration: 160 * line.ms; easing.type: Easing.OutCubic }
                NumberAnimation { target: label; property: "opacity"; from: 0; to: 1; duration: 160 * line.ms; easing.type: Easing.OutCubic }
            }
        }
    }
}
