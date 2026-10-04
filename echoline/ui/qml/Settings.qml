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

    component HotkeyButton: Button {
        property string key
        property bool recording: false
        Layout.preferredWidth: 180
        text: recording ? "Press keys…" : (win.s[key] || "None")
        onClicked: { recording = true; forceActiveFocus() }
        onActiveFocusChanged: if (!activeFocus) recording = false
        Keys.onPressed: (event) => {
            if (!recording) return
            event.accepted = true
            if (event.key === Qt.Key_Escape) { recording = false; return }
            if (event.key === Qt.Key_Backspace) { settingsStore.setValue(key, ""); recording = false; return }
            const names = []
            if (event.modifiers & Qt.ControlModifier) names.push("Ctrl")
            if (event.modifiers & Qt.AltModifier) names.push("Alt")
            if (event.modifiers & Qt.ShiftModifier) names.push("Shift")
            if (event.modifiers & Qt.MetaModifier) names.push("Win")
            let k = ""
            if (event.key >= Qt.Key_A && event.key <= Qt.Key_Z) k = String.fromCharCode(event.key)
            else if (event.key >= Qt.Key_0 && event.key <= Qt.Key_9) k = String.fromCharCode(event.key)
            else if (event.key >= Qt.Key_F1 && event.key <= Qt.Key_F12) k = "F" + (event.key - Qt.Key_F1 + 1)
            if (k === "" || names.length === 0) return        // wait for a full combination
            settingsStore.setValue(key, names.concat([k]).join("+"))
            recording = false
        }
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
        TabButton { text: "Behavior" }
        TabButton { text: "Hotkeys" }
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
            Row2 {
                label: "Always on top"
                Switch {
                    objectName: "onTopSwitch"
                    checked: win.s.always_on_top
                    onToggled: settingsStore.setValue("always_on_top", checked)
                }
            }
            Item { Layout.fillHeight: true }
        }

        ColumnLayout {
            spacing: 14
            Row2 {
                label: "Speech model"
                ComboBox {
                    objectName: "modelBox"
                    Layout.fillWidth: true
                    textRole: "text"; valueRole: "value"
                    model: [{ text: "Tiny — faster", value: "tiny" }, { text: "Small — more accurate", value: "small" }]
                    currentIndex: model.findIndex(item => item.value === win.s.model)
                    enabled: setup.phase !== "downloading" && setup.phase !== "checking"
                    onActivated: (index) => {
                        setup.chooseModel(model[index].value)
                        // Clicking broke the binding; follow the setting again so a failed download shows the old model.
                        currentIndex = Qt.binding(() => model.findIndex(item => item.value === win.s.model))
                    }
                }
            }
            ProgressBar {
                objectName: "modelProgress"
                Layout.fillWidth: true
                visible: setup.phase === "downloading"
                value: setup.progress
            }
            Row2 {
                label: "Audio source"
                ComboBox {
                    objectName: "sourceBox"
                    Layout.fillWidth: true
                    textRole: "text"; valueRole: "value"
                    model: [{ text: "System audio", value: "system" }, { text: "Microphone", value: "microphone" }]
                    currentIndex: model.findIndex(item => item.value === win.s.audio_source)
                    onActivated: (index) => controller.setSource(model[index].value)
                }
            }
            Row2 {
                label: "Hide after 5 s of silence"
                Switch {
                    objectName: "autoHideSwitch"
                    checked: win.s.auto_hide
                    onToggled: settingsStore.setValue("auto_hide", checked)
                }
            }
            Row2 {
                label: "Click-through"
                Switch {
                    objectName: "clickThroughSwitch"
                    checked: win.s.click_through
                    onToggled: controller.setClickThrough(checked)
                }
            }
            Row2 {
                label: "Start with Windows"
                Switch {
                    objectName: "autostartSwitch"
                    checked: win.s.start_with_windows
                    onToggled: settingsStore.setValue("start_with_windows", checked)
                }
            }
            Item { Layout.fillHeight: true }
        }

        ColumnLayout {
            spacing: 14
            Label {
                text: "Click a shortcut, then press the new keys. Esc cancels, Backspace turns it off."
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
            Row2 { label: "Show / hide captions"; HotkeyButton { objectName: "hotkeyShowHide"; key: "hotkey_show_hide" } }
            Row2 { label: "Pause / resume"; HotkeyButton { objectName: "hotkeyPause"; key: "hotkey_pause" } }
            Row2 { label: "Click-through"; HotkeyButton { objectName: "hotkeyClickThrough"; key: "hotkey_click_through" } }
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
