// Runs once per user: panel clock in Yggdrasil Runic.
const allPanels = panels();
for (let i = 0; i < allPanels.length; ++i) {
    const widgets = allPanels[i].widgets();
    for (let j = 0; j < widgets.length; ++j) {
        const w = widgets[j];
        if (w.type === "org.kde.plasma.digitalclock") {
            w.currentConfigGroup = ["Appearance"];
            w.writeConfig("autoFontAndSize", false);
            w.writeConfig("fontFamily", "Yggdrasil Runic");
            w.writeConfig("fontWeight", 400);
            w.writeConfig("fontSize", 11);
            w.reloadConfig();
        }
    }
}
