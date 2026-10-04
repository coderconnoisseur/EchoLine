import QtQuick

// Colour tokens for the settings window, for the Windows app theme in use.
// An Item (not QtObject) so it can read the style palette's accent colour.
Item {
    visible: false
    property bool dark: Application.styleHints.colorScheme !== Qt.Light
    property color accent: palette.accent

    readonly property color window: dark ? "#202020" : "#f3f3f3"
    readonly property color sidebar: dark ? "#1b1b1b" : "#ebebeb"
    readonly property color sidebarSelected: dark ? "#2d2d2d" : "#ffffff"
    readonly property color card: dark ? "#2b2b2b" : "#fbfbfb"
    readonly property color cardBorder: dark ? "#353535" : "#e2e2e2"
    readonly property color divider: dark ? "#3a3a3a" : "#e8e8e8"
    readonly property color text: dark ? "#f3f3f3" : "#1b1b1b"
    readonly property color subtext: dark ? "#a6a6a6" : "#616161"
    // Captions sit over video: the preview backdrop stays dark in both themes.
    readonly property color backdropTop: "#33415e"
    readonly property color backdropBottom: "#15161b"
}
