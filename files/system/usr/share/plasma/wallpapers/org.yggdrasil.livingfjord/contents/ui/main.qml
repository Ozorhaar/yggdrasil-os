// Yggdrasil – Living Fjord: the same living scene as Yggdrasil Sky on Windows (windows/sky/web,
// copied into contents/web at build time by tools/sync-sky.sh), running in a web view behind the
// desktop. It follows the real sky, weather, moon and northern lights, and the house through the
// steading feed on the Mac mini (home network only); it holds no keys and changes nothing.
// If Qt WebEngine is missing, the still fjord shows instead.
import QtQuick
import org.kde.plasma.plasmoid

WallpaperItem {
    id: root

    Image {
        anchors.fill: parent
        source: "../images/base.png"
        fillMode: Image.PreserveAspectCrop
        smooth: true
    }

    Loader {
        id: live
        anchors.fill: parent
        source: "LiveSky.qml"
    }
}
