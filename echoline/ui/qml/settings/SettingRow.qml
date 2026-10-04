import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// One setting: title and an optional explanation on the left, its control on the right.
Item {
    id: row
    property var theme
    property string title
    property string description
    default property alias control: holder.data
    Layout.fillWidth: true
    implicitHeight: Math.max(description !== "" ? 60 : 48, content.implicitHeight + 20)

    // Rows after the first get a hairline above them.
    Rectangle {
        objectName: "divider"
        visible: row.parent !== null && row.parent.children[0] !== row
        anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: 16; rightMargin: 16 }
        height: 1
        color: row.theme.divider
    }

    RowLayout {
        id: content
        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter
                  leftMargin: 16; rightMargin: 16 }
        spacing: 16

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Label { text: row.title; color: row.theme.text; font.pixelSize: 14; Layout.fillWidth: true; elide: Text.ElideRight }
            Label {
                visible: row.description !== ""
                text: row.description
                color: row.theme.subtext
                font.pixelSize: 12
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
        }

        RowLayout {
            id: holder
            spacing: 8
            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
        }
    }
}
