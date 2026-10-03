import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    objectName: "onboardingWindow"
    title: "Welcome to EchoLine"
    width: 480
    height: 400
    visible: false
    readonly property var s: settingsStore.values
    onClosing: setup.windowClosed()

    StackLayout {
        anchors.fill: parent
        anchors.margins: 24
        currentIndex: setup.step

        ColumnLayout {          // 0: getting ready
            spacing: 14
            Label { text: setup.repair ? "Fixing the speech model" : "Welcome to EchoLine"; font.pixelSize: 24; font.weight: Font.DemiBold }
            Label {
                text: "Live captions for anything playing on your PC. Everything runs on this computer — nothing you hear leaves it."
                wrapMode: Text.Wrap; Layout.fillWidth: true
            }
            Item { Layout.fillHeight: true }
            Label {
                objectName: "phaseLabel"
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: ({ downloading: "Downloading the speech model… " + Math.round(setup.progress * 100) + "%",
                         checking: "Checking how fast your PC is…",
                         error: "Couldn't download — check your internet connection",
                         ready: "All set." })[setup.phase] || ""
            }
            ProgressBar {
                Layout.fillWidth: true
                visible: setup.phase === "downloading" || setup.phase === "checking"
                indeterminate: setup.phase === "checking"
                value: setup.progress
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button { objectName: "retryButton"; text: "Retry"; visible: setup.phase === "error"; onClicked: setup.retry() }
                Button {
                    objectName: "nextButton"; text: "Next"; highlighted: true
                    visible: !setup.repair; enabled: setup.phase === "ready"
                    onClicked: setup.nextStep()
                }
            }
        }

        ColumnLayout {          // 1: sound test
            spacing: 14
            Label { text: "Sound test"; font.pixelSize: 24; font.weight: Font.DemiBold }
            Label {
                text: "Play a video or music — captions appear at the bottom of your screen."
                wrapMode: Text.Wrap; Layout.fillWidth: true
            }
            Label {
                objectName: "echoLabel"
                Layout.fillWidth: true; wrapMode: Text.Wrap; font.italic: !captions.latestText
                text: captions.latestText || "Waiting for sound…"
            }
            Item { Layout.fillHeight: true }
            Button {
                objectName: "soundNextButton"; text: "Next"; highlighted: true
                Layout.alignment: Qt.AlignRight
                onClicked: setup.nextStep()
            }
        }

        ColumnLayout {          // 2: theme
            spacing: 14
            Label { text: "Pick a look"; font.pixelSize: 24; font.weight: Font.DemiBold }
            GridLayout {
                columns: 2; columnSpacing: 10; rowSpacing: 10; Layout.fillWidth: true
                Repeater {
                    model: settingsStore.themeNames
                    delegate: Button {
                        required property string modelData
                        Layout.fillWidth: true; Layout.preferredHeight: 56
                        objectName: "theme " + modelData
                        text: modelData
                        highlighted: win.s.theme === modelData
                        onClicked: settingsStore.applyTheme(modelData)
                    }
                }
            }
            Label {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: (win.s.hotkey_show_hide ? win.s.hotkey_show_hide + " shows or hides captions. " : "")
                      + "Everything else is in the tray icon and Settings."
            }
            Item { Layout.fillHeight: true }
            Button {
                objectName: "finishButton"; text: "Finish"; highlighted: true
                Layout.alignment: Qt.AlignRight
                onClicked: setup.finish()
            }
        }
    }
}
