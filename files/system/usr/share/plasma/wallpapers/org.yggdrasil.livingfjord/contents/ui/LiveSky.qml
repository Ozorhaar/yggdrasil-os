// The web view, in its own file so a missing Qt WebEngine only costs the live scene
// (the Loader in main.qml then leaves the still fjord showing).
import QtQuick
import QtWebEngine

WebEngineView {
    id: view
    backgroundColor: "#0B1220"
    url: Qt.resolvedUrl("../web/kde.html") + "?selfhost&lat=41.134&lon=-81.485"
    settings.localContentCanAccessFileUrls: true     // the scene reads its own art files (canvas pixels)
    settings.localContentCanAccessRemoteUrls: true   // weather and the steading feed (limited by kde.html's CSP)
    settings.javascriptCanOpenWindows: false
    settings.pluginsEnabled: false
    settings.playbackRequiresUserGesture: true
    settings.showScrollBars: false
    settings.focusOnNavigationEnabled: false
    // the wallpaper never takes clicks or opens links
    enabled: false
    onNewWindowRequested: function (request) { }
    onNavigationRequested: function (request) {
        if (!request.url.toString().startsWith("file:")) request.action = WebEngineNavigationRequest.IgnoreRequest
    }
}
