import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// One thumbnail per preset, each a tiny caption in that preset's style.
ColumnLayout {
    id: gallery
    property var theme
    property var s
    spacing: 8
    Layout.fillWidth: true

    RowLayout {
        spacing: 8
        Label { text: "Theme"; color: gallery.theme.text; font.pixelSize: 14; font.weight: Font.DemiBold }
        Rectangle {
            objectName: "customBadge"
            visible: gallery.s.theme === "Custom"
            radius: 9
            color: gallery.theme.sidebarSelected
            border.color: gallery.theme.cardBorder
            implicitWidth: customText.implicitWidth + 16
            implicitHeight: 18
            Label { id: customText; anchors.centerIn: parent; text: "Custom"; font.pixelSize: 11; color: gallery.theme.subtext }
        }
    }

    GridLayout {
        columns: 4
        columnSpacing: 10
        rowSpacing: 10
        Layout.fillWidth: true

        Repeater {
            model: settingsStore.themePresets
            delegate: Item {
                id: card
                required property var modelData
                objectName: "theme " + modelData.name
                readonly property bool selected: gallery.s.theme === modelData.name
                signal clicked()
                onClicked: settingsStore.applyTheme(modelData.name)
                activeFocusOnTab: true
                Keys.onSpacePressed: clicked()
                Keys.onReturnPressed: clicked()
                Layout.fillWidth: true
                implicitHeight: 96

                Rectangle {
                    id: thumb
                    anchors { left: parent.left; right: parent.right; top: parent.top }
                    height: 68
                    radius: 8
                    gradient: Gradient {
                        GradientStop { position: 0; color: gallery.theme.backdropTop }
                        GradientStop { position: 1; color: gallery.theme.backdropBottom }
                    }
                    border.width: card.selected ? 2 : 1
                    border.color: card.selected ? gallery.theme.accent : gallery.theme.cardBorder

                    Rectangle {          // keyboard focus ring
                        visible: card.activeFocus
                        anchors { fill: parent; margins: -4 }
                        radius: 11
                        color: "transparent"
                        border.width: 2
                        border.color: gallery.theme.text
                    }

                    Rectangle {
                        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 10 }
                        width: sampleText.implicitWidth + 14
                        height: sampleText.implicitHeight + 6
                        radius: card.modelData.corner_radius * 0.5
                        color: Qt.rgba(0, 0, 0, card.modelData.background_opacity)
                        Text {
                            id: sampleText
                            anchors.centerIn: parent
                            text: "Captions"
                            color: card.modelData.text_color
                            font.family: card.modelData.font_family
                            font.pixelSize: 13
                            font.weight: card.modelData.font_weight
                            style: ({ "outline": Text.Outline, "shadow": Text.Raised, "none": Text.Normal })[card.modelData.outline]
                            styleColor: card.modelData.outline_color
                        }
                    }
                }

                Label {
                    anchors { horizontalCenter: parent.horizontalCenter; top: thumb.bottom; topMargin: 6 }
                    text: card.modelData.name
                    color: card.selected ? gallery.theme.text : gallery.theme.subtext
                    font.pixelSize: 12
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: card.clicked()
                }
            }
        }
    }
}
