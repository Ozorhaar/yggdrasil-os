// Yggdrasil – Living Fjord: the Fjord at Dusk wallpaper split into layers
// (tools/art.py desktop_fjord_layers) and moved gently. Movement uses Qt Quick
// Animators where it can, so it runs on the render thread and costs very little.
import QtQuick
import org.kde.plasma.plasmoid

WallpaperItem {
    id: root

    Rectangle { anchors.fill: parent; color: "#0B1220" }

    Item {
        id: scene
        // the art is 16:9; cover the screen and crop the overflow
        readonly property real k: Math.max(root.width / 3840, root.height / 2160)
        readonly property real horizon: height * 0.62
        width: 3840 * k
        height: 2160 * k
        anchors.centerIn: parent
        clip: false

        component Layer: Image {
            width: scene.width
            height: scene.height
            sourceSize: Qt.size(Math.max(1, Math.ceil(scene.width)), Math.max(1, Math.ceil(scene.height)))
            fillMode: Image.Stretch
            smooth: true
            asynchronous: false
            cache: true
        }

        Layer { source: "../images/base.png" }

        // stars, plus a few that twinkle
        Layer { source: "../images/stars.png" }
        Repeater {
            model: 70
            Rectangle {
                readonly property real sz: (1.6 + Math.random() * 2.2) * scene.k * 2
                x: Math.random() * scene.width
                y: Math.pow(Math.random(), 1.4) * scene.horizon * 0.62
                width: sz; height: sz; radius: sz / 2
                color: Math.random() < 0.2 ? "#ECD08F" : "#FFFFFF"
                opacity: 0.2
                SequentialAnimation on opacity {
                    loops: Animation.Infinite
                    PauseAnimation { duration: Math.random() * 6000 }
                    OpacityAnimator { from: 0.15; to: 0.95; duration: 900 + Math.random() * 2200; easing.type: Easing.InOutSine }
                    OpacityAnimator { from: 0.95; to: 0.15; duration: 900 + Math.random() * 2200; easing.type: Easing.InOutSine }
                }
            }
        }

        // a shooting star every minute or so
        Rectangle {
            id: meteor
            width: 260 * scene.k; height: 3 * scene.k; radius: height / 2
            rotation: 18
            opacity: 0
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#00FFFFFF" }
                GradientStop { position: 1; color: "#FFFFFF" }
            }
            ParallelAnimation {
                id: fall
                XAnimator { id: fx; target: meteor; duration: 900; easing.type: Easing.InQuad }
                YAnimator { id: fy; target: meteor; duration: 900; easing.type: Easing.InQuad }
                SequentialAnimation {
                    OpacityAnimator { target: meteor; from: 0; to: 0.9; duration: 150 }
                    PauseAnimation { duration: 450 }
                    OpacityAnimator { target: meteor; from: 0.9; to: 0; duration: 300 }
                }
            }
            Timer {
                interval: 45000 + Math.random() * 60000
                running: true; repeat: true
                onTriggered: {
                    interval = 45000 + Math.random() * 60000
                    const x0 = scene.width * (0.1 + Math.random() * 0.6)
                    const y0 = scene.horizon * (0.05 + Math.random() * 0.3)
                    fx.from = x0; fx.to = x0 + 700 * scene.k
                    fy.from = y0; fy.to = y0 + 230 * scene.k
                    fall.restart()
                }
            }
        }

        // the aurora: a slow sway and a breathing glow, with a fainter mirrored
        // copy drifting the other way so the curtains seem to shift
        Layer {
            source: "../images/aurora.png"
            opacity: 0.8
            SequentialAnimation on x {
                loops: Animation.Infinite
                XAnimator { from: -40 * scene.k; to: 40 * scene.k; duration: 47000; easing.type: Easing.InOutSine }
                XAnimator { from: 40 * scene.k; to: -40 * scene.k; duration: 47000; easing.type: Easing.InOutSine }
            }
            SequentialAnimation on opacity {
                loops: Animation.Infinite
                OpacityAnimator { from: 0.55; to: 1.0; duration: 11000; easing.type: Easing.InOutSine }
                OpacityAnimator { from: 1.0; to: 0.55; duration: 11000; easing.type: Easing.InOutSine }
            }
        }
        Layer {
            source: "../images/aurora.png"
            mirror: true
            opacity: 0.0
            SequentialAnimation on x {
                loops: Animation.Infinite
                XAnimator { from: 60 * scene.k; to: -60 * scene.k; duration: 61000; easing.type: Easing.InOutSine }
                XAnimator { from: -60 * scene.k; to: 60 * scene.k; duration: 61000; easing.type: Easing.InOutSine }
            }
            SequentialAnimation on opacity {
                loops: Animation.Infinite
                OpacityAnimator { from: 0.0; to: 0.35; duration: 17000; easing.type: Easing.InOutSine }
                OpacityAnimator { from: 0.35; to: 0.0; duration: 17000; easing.type: Easing.InOutSine }
            }
        }

        Layer { source: "../images/land.png" }

        // sun glitter: two sets cross-fading
        Layer {
            source: "../images/glitter_a.png"
            SequentialAnimation on opacity {
                loops: Animation.Infinite
                OpacityAnimator { from: 1.0; to: 0.2; duration: 1700; easing.type: Easing.InOutSine }
                OpacityAnimator { from: 0.2; to: 1.0; duration: 1700; easing.type: Easing.InOutSine }
            }
        }
        Layer {
            source: "../images/glitter_b.png"
            SequentialAnimation on opacity {
                loops: Animation.Infinite
                OpacityAnimator { from: 0.2; to: 1.0; duration: 1700; easing.type: Easing.InOutSine }
                OpacityAnimator { from: 1.0; to: 0.2; duration: 1700; easing.type: Easing.InOutSine }
            }
        }

        // ripples sliding slowly across the water
        Layer {
            source: "../images/ripples.png"
            SequentialAnimation on x {
                loops: Animation.Infinite
                XAnimator { from: -50 * scene.k; to: 50 * scene.k; duration: 19000; easing.type: Easing.InOutSine }
                XAnimator { from: 50 * scene.k; to: -50 * scene.k; duration: 19000; easing.type: Easing.InOutSine }
            }
        }

        // the longship rides the swell: a gentle bob and a slow roll about its waterline
        Layer {
            source: "../images/ship.png"
            transform: Rotation {
                origin.x: scene.width * 0.36
                origin.y: scene.horizon
                SequentialAnimation on angle {
                    loops: Animation.Infinite
                    NumberAnimation { from: -0.7; to: 0.7; duration: 3300; easing.type: Easing.InOutSine }
                    NumberAnimation { from: 0.7; to: -0.7; duration: 3300; easing.type: Easing.InOutSine }
                }
            }
            SequentialAnimation on y {
                loops: Animation.Infinite
                YAnimator { from: -3 * scene.k; to: 4 * scene.k; duration: 2300; easing.type: Easing.InOutSine }
                YAnimator { from: 4 * scene.k; to: -3 * scene.k; duration: 2300; easing.type: Easing.InOutSine }
            }
        }
    }
}
