// Yggdrasil OS login splash: the emblem rises, the runes are carved in
// left-to-right as Plasma loads, and a thin gold line fills underneath.
import QtQuick

Rectangle {
    id: root
    color: "#0b1220"

    property int stage

    onStageChanged: {
        if (stage == 2) {
            intro.running = true
        }
    }

    Image {
        id: logo
        source: "images/logo.png"
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -60
        width: 220; height: 220
        sourceSize.width: 360; sourceSize.height: 360
        opacity: 0
        scale: 0.92
    }

    // The rune word, revealed by widening a clipping box with each stage
    Item {
        id: carve
        anchors.top: logo.bottom
        anchors.topMargin: 36
        anchors.horizontalCenter: parent.horizontalCenter
        width: runes.width
        height: runes.height
        Item {
            clip: true
            height: parent.height
            width: parent.width * Math.min(1, root.stage / 6)
            Behavior on width { NumberAnimation { duration: 600; easing.type: Easing.OutCubic } }
            Image { id: runes; source: "images/name-runes.png" }
        }
    }

    Rectangle {
        anchors.top: carve.bottom
        anchors.topMargin: 28
        anchors.horizontalCenter: parent.horizontalCenter
        width: 260; height: 3; radius: 2
        color: "#2a2f36"
        Rectangle {
            height: parent.height; radius: 2
            color: "#c8a25a"
            width: parent.width * Math.min(1, root.stage / 6)
            Behavior on width { NumberAnimation { duration: 600; easing.type: Easing.OutCubic } }
        }
    }

    ParallelAnimation {
        id: intro
        NumberAnimation { target: logo; property: "opacity"; to: 1; duration: 900; easing.type: Easing.OutQuad }
        NumberAnimation { target: logo; property: "scale"; to: 1; duration: 1200; easing.type: Easing.OutCubic }
    }
}
