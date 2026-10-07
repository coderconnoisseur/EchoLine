import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "settings"

ApplicationWindow {
    id: win
    objectName: "settingsWindow"
    title: "EchoLine Settings"
    width: 880
    height: 620
    minimumWidth: 760
    minimumHeight: 520
    visible: false
    color: theme.window
    readonly property var s: settingsStore.values
    property string page: "appearance"

    readonly property var pages: [
        { key: "appearance", label: "Appearance", icon: "palette" },
        { key: "position", label: "Position", icon: "screen" },
        { key: "behavior", label: "Behavior", icon: "tune" },
        { key: "speech", label: "Speech", icon: "mic" },
        { key: "shortcuts", label: "Shortcuts", icon: "keyboard" },
        { key: "about", label: "About", icon: "info" }
    ]
    function pageIndex(key) { return pages.findIndex(p => p.key === key) }

    Theme { id: theme; objectName: "theme" }

    component HotkeyButton: Button {
        property string key
        property bool recording: false
        Layout.preferredWidth: 200
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
        spacing: 8
        Repeater {
            model: ["#ffffff", "#ffff00", "#00ffff", "#00ff00", "#000000", "#808080"]
            delegate: Rectangle {
                required property string modelData
                width: 24; height: 24; radius: 12
                color: modelData
                border.width: win.s[swatches.key] === modelData ? 3 : 1
                border.color: win.s[swatches.key] === modelData ? theme.accent : theme.cardBorder
                TapHandler { onTapped: settingsStore.setValue(swatches.key, parent.modelData) }
            }
        }
    }

    // A page: centered column, at most 640 px wide, scrolling when tall.
    component Page: ScrollView {
        id: pageView
        property string title
        default property alias content: column.data
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            id: column
            x: Math.max(24, (pageView.availableWidth - width) / 2)
            width: Math.min(640, pageView.availableWidth - 48)
            spacing: 12
            Label {
                text: pageView.title
                color: theme.text
                font.pixelSize: 24
                font.weight: Font.DemiBold
                Layout.topMargin: 24
                Layout.bottomMargin: 4
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 176
            color: theme.sidebar

            ListView {
                id: sidebar
                objectName: "sidebar"
                anchors { fill: parent; topMargin: 16; leftMargin: 8; rightMargin: 8 }
                model: win.pages
                spacing: 2
                focus: true
                activeFocusOnTab: true       // Shift+Tab from a page leads back here
                keyNavigationEnabled: true
                currentIndex: 0
                onCurrentIndexChanged: win.page = win.pages[currentIndex].key
                interactive: false

                delegate: Rectangle {
                    id: entry
                    required property var modelData
                    required property int index
                    readonly property bool selected: ListView.isCurrentItem
                    width: ListView.view.width
                    height: 36
                    radius: 6
                    color: selected ? theme.sidebarSelected : (hover.hovered ? Qt.darker(theme.sidebar, theme.dark ? 0.85 : 1.04) : "transparent")

                    Rectangle {
                        visible: entry.selected
                        anchors { left: parent.left; verticalCenter: parent.verticalCenter }
                        width: 3; height: 16; radius: 2
                        color: theme.accent
                    }
                    Row {
                        anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter }
                        spacing: 12
                        Icon {
                            name: entry.modelData.icon
                            size: 16
                            color: theme.text
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Label {
                            text: entry.modelData.label
                            color: theme.text
                            font.pixelSize: 14
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    HoverHandler { id: hover }
                    TapHandler {
                        // Take focus too, so keys stop acting on a control of the page left behind.
                        onTapped: { sidebar.currentIndex = entry.index; sidebar.forceActiveFocus() }
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: win.pageIndex(win.page)
            onCurrentIndexChanged: sidebar.currentIndex = currentIndex

            Page {
                objectName: "page appearance"
                title: "Appearance"
                PreviewPane { Layout.fillWidth: true; theme: theme; s: win.s; sample: sampleCaptions }
                ThemeGallery { Layout.topMargin: 8; theme: theme; s: win.s }
                SettingsCard {
                    theme: theme
                    title: "Text"
                    SettingRow {
                        theme: theme; title: "Font"
                        ComboBox {
                            objectName: "fontBox"
                            Layout.preferredWidth: 220
                            model: controller.fonts
                            currentIndex: model.indexOf(win.s.font_family)
                            onActivated: (index) => settingsStore.setValue("font_family", model[index])
                        }
                    }
                    SettingRow {
                        theme: theme; title: "Size"; description: "How big caption text is"
                        Slider {
                            objectName: "sizeSlider"
                            Layout.preferredWidth: 220
                            from: 14; to: 64
                            value: win.s.font_size
                            onMoved: settingsStore.setValue("font_size", Math.round(value))
                        }
                    }
                    SettingRow {
                        theme: theme; title: "Weight"
                        ComboBox {
                            objectName: "weightBox"
                            Layout.preferredWidth: 220
                            textRole: "text"; valueRole: "value"
                            model: [{ text: "Regular", value: 400 }, { text: "Medium", value: 500 },
                                    { text: "Semibold", value: 600 }, { text: "Bold", value: 700 }]
                            currentIndex: model.findIndex(item => item.value === win.s.font_weight)
                            onActivated: settingsStore.setValue("font_weight", currentValue)
                        }
                    }
                    SettingRow { theme: theme; title: "Color"; Swatches { key: "text_color" } }
                    SettingRow {
                        theme: theme; title: "Effect"; description: "Keeps text readable over bright video"
                        ComboBox {
                            objectName: "effectBox"
                            Layout.preferredWidth: 220
                            textRole: "text"; valueRole: "value"
                            model: [{ text: "Outline", value: "outline" }, { text: "Shadow", value: "shadow" },
                                    { text: "None", value: "none" }]
                            currentIndex: model.findIndex(item => item.value === win.s.outline)
                            onActivated: settingsStore.setValue("outline", currentValue)
                        }
                    }
                }
                SettingsCard {
                    theme: theme
                    title: "Background"
                    SettingRow { theme: theme; title: "Color"; Swatches { key: "background_color" } }
                    SettingRow {
                        theme: theme; title: "Opacity"; description: "How solid the caption box is"
                        Slider {
                            objectName: "opacitySlider"
                            Layout.preferredWidth: 220
                            from: 0; to: 1
                            value: win.s.background_opacity
                            onMoved: settingsStore.setValue("background_opacity", Math.round(value * 20) / 20)
                        }
                    }
                    SettingRow {
                        theme: theme; title: "Corner radius"
                        Slider {
                            Layout.preferredWidth: 220
                            from: 0; to: 32
                            value: win.s.corner_radius
                            onMoved: settingsStore.setValue("corner_radius", Math.round(value))
                        }
                    }
                    SettingRow {
                        theme: theme; title: "Blur behind"; description: "Frosted glass under the captions"
                        Switch { checked: win.s.blur_behind; onToggled: settingsStore.setValue("blur_behind", checked) }
                    }
                }
                Item { Layout.preferredHeight: 16 }
            }

            Page {
                objectName: "page position"
                title: "Position"
                PreviewPane { Layout.fillWidth: true; theme: theme; s: win.s; sample: sampleCaptions }
                SettingsCard {
                    theme: theme
                    title: "Layout"
                    SettingRow {
                        theme: theme; title: "Caption style"; description: "Rolling lines scroll up; subtitle blocks replace each phrase"
                        ComboBox {
                            objectName: "modeBox"
                            Layout.preferredWidth: 200
                            textRole: "text"; valueRole: "value"
                            model: [{ text: "Rolling lines", value: "rolling" }, { text: "Subtitle blocks", value: "subtitle" }]
                            currentIndex: model.findIndex(item => item.value === win.s.caption_mode)
                            onActivated: settingsStore.setValue("caption_mode", currentValue)
                        }
                    }
                    SettingRow {
                        theme: theme; title: "Lines"; description: "How many lines stay on screen"
                        SpinBox {
                            from: 1; to: 3
                            value: win.s.line_count
                            onValueModified: settingsStore.setValue("line_count", value)
                        }
                    }
                    SettingRow {
                        theme: theme; title: "Width"; description: "Share of the screen width"
                        Slider {
                            Layout.preferredWidth: 220
                            from: 20; to: 90
                            value: win.s.width_percent
                            onMoved: settingsStore.setValue("width_percent", Math.round(value))
                        }
                    }
                }
                SettingsCard {
                    theme: theme
                    title: "Placement"
                    SettingRow {
                        theme: theme; title: "Move captions to"
                        Button { text: "Top"; onClicked: controller.snap("top") }
                        Button { text: "Center"; onClicked: controller.snap("center") }
                        Button { text: "Bottom"; onClicked: controller.snap("bottom") }
                    }
                    SettingRow {
                        theme: theme; title: "Always on top"; description: "Keep captions above other windows"
                        Switch {
                            objectName: "onTopSwitch"
                            checked: win.s.always_on_top
                            onToggled: settingsStore.setValue("always_on_top", checked)
                        }
                    }
                }
                Item { Layout.preferredHeight: 16 }
            }

            Page {
                objectName: "page behavior"
                title: "Behavior"
                SettingsCard {
                    theme: theme
                    title: "Audio"
                    SettingRow {
                        theme: theme; title: "Listen to"; description: "What EchoLine captions"
                        ComboBox {
                            objectName: "sourceBox"
                            Layout.preferredWidth: 200
                            textRole: "text"; valueRole: "value"
                            model: [{ text: "System audio", value: "system" }, { text: "Microphone", value: "microphone" }]
                            currentIndex: model.findIndex(item => item.value === win.s.audio_source)
                            onActivated: (index) => controller.setSource(model[index].value)
                        }
                    }
                }
                SettingsCard {
                    theme: theme
                    title: "Visibility"
                    SettingRow {
                        theme: theme; title: "Hide after silence"; description: "Fade out after 5 seconds without speech"
                        Switch {
                            objectName: "autoHideSwitch"
                            checked: win.s.auto_hide
                            onToggled: settingsStore.setValue("auto_hide", checked)
                        }
                    }
                    SettingRow {
                        theme: theme; title: "Click-through"; description: "Clicks pass through captions to the window below"
                        Switch {
                            objectName: "clickThroughSwitch"
                            checked: win.s.click_through
                            onToggled: controller.setClickThrough(checked)
                        }
                    }
                }
                SettingsCard {
                    theme: theme
                    title: "Startup"
                    SettingRow {
                        theme: theme; title: "Start with Windows"; description: "Open EchoLine when you sign in"
                        Switch {
                            objectName: "autostartSwitch"
                            checked: win.s.start_with_windows
                            onToggled: settingsStore.setValue("start_with_windows", checked)
                        }
                    }
                }
                Item { Layout.preferredHeight: 16 }
            }

            Page {
                objectName: "page speech"
                title: "Speech"
                SettingsCard {
                    theme: theme
                    title: "Model"
                    SettingRow {
                        theme: theme; title: "Speech model"
                        description: "Tiny is fastest and works on any PC. Small is more accurate but needs a faster CPU."
                        ComboBox {
                            objectName: "modelBox"
                            Layout.preferredWidth: 220
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
                    SettingRow {
                        visible: setup.phase === "downloading"
                        theme: theme; title: "Downloading…"
                        ProgressBar {
                            objectName: "modelProgress"
                            Layout.preferredWidth: 220
                            visible: setup.phase === "downloading"
                            value: setup.progress
                        }
                    }
                }
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: theme.subtext
                    font.pixelSize: 12
                    text: "Speech is recognised on this PC. Models are stored in your local app data and work offline."
                }
            }

            Page {
                objectName: "page shortcuts"
                title: "Shortcuts"
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: theme.subtext
                    text: "Click a shortcut, then press the new keys. Esc cancels, Backspace turns it off."
                }
                SettingsCard {
                    theme: theme
                    SettingRow { theme: theme; title: "Show or hide captions"; HotkeyButton { objectName: "hotkeyShowHide"; key: "hotkey_show_hide" } }
                    SettingRow { theme: theme; title: "Pause or resume"; HotkeyButton { objectName: "hotkeyPause"; key: "hotkey_pause" } }
                    SettingRow { theme: theme; title: "Click-through on or off"; HotkeyButton { objectName: "hotkeyClickThrough"; key: "hotkey_click_through" } }
                }
            }

            Page {
                objectName: "page about"
                title: "About"
                SettingsCard {
                    theme: theme
                    SettingRow {
                        theme: theme; title: "EchoLine"; description: "Version 0.3.0"
                    }
                    SettingRow {
                        theme: theme; title: "Private by design"
                        description: "Live captions run entirely on this PC; nothing you hear leaves it."
                    }
                    SettingRow {
                        theme: theme; title: "Open source"; description: "MIT License"
                        Button {
                            text: "GitHub"
                            onClicked: Qt.openUrlExternally("https://github.com/coderconnoisseur/EchoLine")
                        }
                    }
                }
            }
        }
    }
}
