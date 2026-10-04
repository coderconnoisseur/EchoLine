import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// A titled group of SettingRows on one rounded card.
ColumnLayout {
    id: card
    property var theme
    property string title
    default property alias rows: column.data
    spacing: 8
    Layout.fillWidth: true

    Label {
        visible: card.title !== ""
        text: card.title
        color: card.theme.text
        font.pixelSize: 14
        font.weight: Font.DemiBold
        Layout.topMargin: 8
    }

    Rectangle {
        Layout.fillWidth: true
        implicitHeight: column.implicitHeight
        radius: 8
        color: card.theme.card
        border.color: card.theme.cardBorder

        ColumnLayout {
            id: column
            anchors { left: parent.left; right: parent.right; top: parent.top }
            spacing: 0
        }
    }
}
