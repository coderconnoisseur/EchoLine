import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    objectName: "settingsWindow"
    title: "EchoLine settings"
    width: 520
    height: 600
    visible: false
    readonly property var s: settingsStore.values

    component Row2: RowLayout {
        property alias label: name.text
        Layout.fillWidth: true
        spacing: 12
        Label { id: name; Layout.preferredWidth: 150 }
    }

    component Swatches: Row {
        id: swatches
        property string key
        spacing: 6
        Repeater {
            model: ["#ffffff", "#ffff00", "#00ffff", "#00ff00", "#000000", "#808080"]
            delegate: Rectangle {
                required property string modelData
                width: 28; height: 28; radius: 14
                color: modelData
                border.width: win.s[swatches.key] === modelData ? 3 : 1
                border.color: win.palette.highlight
                TapHandler { onTapped: settingsStore.setValue(swatches.key, parent.modelData) }
            }
        }
    }

    header: TabBar {
        id: tabs
        objectName: "tabs"
        TabButton { text: "Appearance" }
        TabButton { text: "Layout" }
        TabButton { text: "About" }
    }

    StackLayout {
        anchors.fill: parent
        anchors.margins: 20
        currentIndex: tabs.currentIndex

        ColumnLayout {
            spacing: 14
            Row2 {
                label: "Theme"
                ComboBox {
                    objectName: "themeBox"
                    Layout.fillWidth: true
                    model: settingsStore.themeNames
                    displayText: win.s.theme
                    onActivated: (index) => settingsStore.applyTheme(model[index])
                }
            }
            Row2 {
                label: "Font"
                ComboBox {
                    objectName: "fontBox"
                    Layout.fillWidth: true
                    model: controller.fonts
                    currentIndex: model.indexOf(win.s.font_family)
                    onActivated: (index) => settingsStore.setValue("font_family", model[index])
                }
            }
            Row2 {
                label: "Size"
                Slider {
                    objectName: "sizeSlider"
                    Layout.fillWidth: true
                    from: 14; to: 64
                    value: win.s.font_size
                    onMoved: settingsStore.setValue("font_size", Math.round(value))
                }
            }
            Row2 {
                label: "Weight"
                ComboBox {
                    objectName: "weightBox"
                    Layout.fillWidth: true
                    textRole: "text"; valueRole: "value"
                    model: [{ text: "Regular", value: 400 }, { text: "Medium", value: 500 },
                            { text: "Semibold", value: 600 }, { text: "Bold", value: 700 }]
                    currentIndex: model.findIndex(item => item.value === win.s.font_weight)
                    onActivated: settingsStore.setValue("font_weight", currentValue)
                }
            }
            Row2 { label: "Text color"; Swatches { key: "text_color" } }
            Row2 {
                label: "Text effect"
                ComboBox {
                    objectName: "effectBox"
                    Layout.fillWidth: true
                    textRole: "text"; valueRole: "value"
                    model: [{ text: "Outline", value: "outline" }, { text: "Shadow", value: "shadow" },
                            { text: "None", value: "none" }]
                    currentIndex: model.findIndex(item => item.value === win.s.outline)
                    onActivated: settingsStore.setValue("outline", currentValue)
                }
            }
            Row2 { label: "Background"; Swatches { key: "background_color" } }
            Row2 {
                label: "Background opacity"
                Slider {
                    objectName: "opacitySlider"
                    Layout.fillWidth: true
                    from: 0; to: 1
                    value: win.s.background_opacity
                    onMoved: settingsStore.setValue("background_opacity", Math.round(value * 20) / 20)
                }
            }
            Row2 {
                label: "Corner radius"
                Slider {
                    Layout.fillWidth: true
                    from: 0; to: 32
                    value: win.s.corner_radius
                    onMoved: settingsStore.setValue("corner_radius", Math.round(value))
                }
            }
            Row2 {
                label: "Blur behind"
                Switch { checked: win.s.blur_behind; onToggled: settingsStore.setValue("blur_behind", checked) }
            }
            Item { Layout.fillHeight: true }
        }

        ColumnLayout {
            spacing: 14
            Row2 {
                label: "Caption style"
                ComboBox {
                    objectName: "modeBox"
                    Layout.fillWidth: true
                    textRole: "text"; valueRole: "value"
                    model: [{ text: "Rolling lines", value: "rolling" }, { text: "Subtitle blocks", value: "subtitle" }]
                    currentIndex: model.findIndex(item => item.value === win.s.caption_mode)
                    onActivated: settingsStore.setValue("caption_mode", currentValue)
                }
            }
            Row2 {
                label: "Lines"
                SpinBox {
                    from: 1; to: 3
                    value: win.s.line_count
                    onValueModified: settingsStore.setValue("line_count", value)
                }
            }
            Row2 {
                label: "Width"
                Slider {
                    Layout.fillWidth: true
                    from: 20; to: 90
                    value: win.s.width_percent
                    onMoved: settingsStore.setValue("width_percent", Math.round(value))
                }
            }
            Row2 {
                label: "Position"
                Button { text: "Top"; onClicked: controller.snap("top") }
                Button { text: "Center"; onClicked: controller.snap("center") }
                Button { text: "Bottom"; onClicked: controller.snap("bottom") }
            }
            Item { Layout.fillHeight: true }
        }

        ColumnLayout {
            spacing: 10
            Label { text: "EchoLine"; font.pixelSize: 24; font.weight: Font.DemiBold }
            Label { text: "Version 0.2.0" }
            Label {
                text: "Live captions run entirely on this PC; nothing you hear leaves it."
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
            Label {
                text: "<a href='https://github.com/coderconnoisseur/EchoLine'>github.com/coderconnoisseur/EchoLine</a>"
                onLinkActivated: (link) => Qt.openUrlExternally(link)
            }
            Item { Layout.fillHeight: true }
        }
    }
}
