// Runs once per user the first time Plasma starts on Yggdrasil OS:
// world-tree icon on the app-menu button and the fjord as the wallpaper.
const allPanels = panels();
for (let i = 0; i < allPanels.length; ++i) {
    const widgets = allPanels[i].widgets();
    for (let j = 0; j < widgets.length; ++j) {
        const w = widgets[j];
        if (w.type === "org.kde.plasma.kickoff" ||
            w.type === "org.kde.plasma.kicker" ||
            w.type === "org.kde.plasma.kickerdash") {
            w.currentConfigGroup = ["General"];
            w.writeConfig("icon", "yggdrasil-logo");
            w.reloadConfig();
        }
    }
}

const allDesktops = desktops();
for (let i = 0; i < allDesktops.length; ++i) {
    const d = allDesktops[i];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    d.writeConfig("Image", "file:///usr/share/wallpapers/Yggdrasil-Fjord/");
}
