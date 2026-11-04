using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using Microsoft.Win32;
using static Yggdrasil.Sky.Native;

namespace Yggdrasil.Sky;

/// <summary>
/// The wallpaper window: a WebView2 that only ever shows the local scene in web\,
/// placed behind the desktop icons. Pauses itself whenever nobody can see it.
/// </summary>
internal sealed class SkyForm : Form
{
    const string Origin = "https://sky.yggdrasil/";
    static readonly string[] ShellClasses = { "Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "SHELLDLL_DefView" };

    readonly Settings settings = Settings.Load();
    readonly Weather weather;
    readonly WebView2 web = new() { Dock = DockStyle.Fill };
    readonly NotifyIcon tray = new();
    readonly System.Windows.Forms.Timer watch = new() { Interval = 1000 };
    readonly ToolStripMenuItem pauseItem = new("Pause");

    Desktop.Host? host;
    bool ready, manualPause, locked, displayOff;
    string mode = "running";            // running | soft (covered: stop drawing) | hard (hidden + suspended)
    IntPtr powerNotify;
    DateTime nextAttachTry = DateTime.MinValue, nextWeather = DateTime.MinValue;

    readonly bool startup;

    public SkyForm(bool startup)
    {
        this.startup = startup;
        weather = new Weather(settings);
        Text = "Yggdrasil Sky";
        FormBorderStyle = FormBorderStyle.None;
        ShowInTaskbar = false;
        StartPosition = FormStartPosition.Manual;
        BackColor = Color.FromArgb(0x0B, 0x12, 0x20);
        Bounds = new Rectangle(-32000, -32000, 1, 1);   // off-screen until it sits behind the icons
        web.DefaultBackgroundColor = BackColor;
        Controls.Add(web);

        var menu = new ContextMenuStrip();
        menu.Items.Add("Show the demo (80 s)", null, (_, _) => Post(new { type = "demo" }));
        menu.Items.Add(pauseItem);
        pauseItem.Click += (_, _) => { manualPause = !manualPause; pauseItem.Text = manualPause ? "Resume" : "Pause"; Evaluate(); };
        menu.Items.Add("Refresh weather", null, async (_, _) => SendWeather(await weather.Refresh()));
        menu.Items.Add("Open settings folder", null, (_, _) =>
            System.Diagnostics.Process.Start("explorer.exe", $"\"{Settings.Dir}\""));
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Quit Yggdrasil Sky", null, (_, _) => Close());
        using (var s = typeof(SkyForm).Assembly.GetManifestResourceStream("Yggdrasil.Sky.assets.yggdrasil.ico"))
            tray.Icon = s != null ? new Icon(s) : SystemIcons.Application;
        tray.Text = "Yggdrasil Sky";
        tray.ContextMenuStrip = menu;
        tray.Visible = true;

        watch.Tick += (_, _) => Tick();
        SystemEvents.SessionSwitch += OnSessionSwitch;
        SystemEvents.DisplaySettingsChanged += (_, _) => Reattach();
    }

    // Tool window that never takes focus and stays out of Alt+Tab.
    protected override CreateParams CreateParams
    {
        get { var cp = base.CreateParams; cp.ExStyle |= 0x80 /*TOOLWINDOW*/ | 0x08000000 /*NOACTIVATE*/; return cp; }
    }
    protected override bool ShowWithoutActivation => true;

    protected override async void OnShown(EventArgs e)
    {
        base.OnShown(e);
        var guid = GUID_CONSOLE_DISPLAY_STATE;
        powerNotify = RegisterPowerSettingNotification(Handle, ref guid, 0);
        Reattach();
        // Windows 8+ never plays its own sign-in sound, so the horn comes from here.
        if (startup && settings.SignInHorn) Horn("Sign In");
        await StartWebView();
        watch.Start();
    }

    async Task StartWebView()
    {
        string webDir = Path.Combine(AppContext.BaseDirectory, "web");
        var opts = new CoreWebView2EnvironmentOptions("--disable-background-networking --disable-sync --no-first-run");
        var env = await CoreWebView2Environment.CreateAsync(null, Path.Combine(Settings.Dir, "WebView2"), opts);
        await web.EnsureCoreWebView2Async(env);
        var core = web.CoreWebView2!;

        var st = core.Settings;   // a picture, not a browser: switch everything else off
        st.AreDevToolsEnabled = false;
        st.AreDefaultContextMenusEnabled = false;
        st.AreDefaultScriptDialogsEnabled = false;
        st.AreBrowserAcceleratorKeysEnabled = false;
        st.AreHostObjectsAllowed = false;
        st.IsStatusBarEnabled = false;
        st.IsZoomControlEnabled = false;
        st.IsPinchZoomEnabled = false;
        st.IsSwipeNavigationEnabled = false;
        st.IsPasswordAutosaveEnabled = false;
        st.IsGeneralAutofillEnabled = false;
        st.IsBuiltInErrorPageEnabled = false;
        st.IsWebMessageEnabled = true;

        core.SetVirtualHostNameToFolderMapping("sky.yggdrasil", webDir, CoreWebView2HostResourceAccessKind.Deny);
        core.NavigationStarting += (_, a) => { if (!a.Uri.StartsWith(Origin, StringComparison.Ordinal)) a.Cancel = true; };
        core.FrameNavigationStarting += (_, a) => a.Cancel = true;
        core.NewWindowRequested += (_, a) => a.Handled = true;
        core.PermissionRequested += (_, a) => a.State = CoreWebView2PermissionState.Deny;
        core.DownloadStarting += (_, a) => a.Cancel = true;
        core.WebMessageReceived += OnWebMessage;
        core.ProcessFailed += (_, a) => { Log.Write("webview process failed: " + a.ProcessFailedKind); core.Reload(); };
        core.Navigate(Origin + "index.html");
    }

    async void OnWebMessage(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        if (!e.Source.StartsWith(Origin, StringComparison.Ordinal)) return;
        try
        {
            using var doc = JsonDocument.Parse(e.WebMessageAsJson);
            if (doc.RootElement.TryGetProperty("type", out var t) && t.GetString() == "ready")
            {
                ready = true;
                Post(new { type = "fps", fps = settings.Fps });
                Post(new { type = "calm", fps = settings.CalmFps });
                Post(new { type = "scale", scale = settings.RenderScale });
                SendWeather(weather.Last);
                if (weather.Stale) SendWeather(await weather.Refresh());
                mode = "running";
                Evaluate();
            }
        }
        catch (JsonException) { }
    }

    void SendWeather(Weather.Now? w)
    {
        if (w != null) Post(new { type = "weather", code = w.Code, sunrise = w.Sunrise, sunset = w.Sunset });
    }

    void Post(object msg)
    {
        if (ready && web.CoreWebView2 != null) web.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(msg));
    }

    // ------------------------------------------------------------- desktop placement
    void Reattach()
    {
        host = Desktop.Find();
        if (host == null) { Log.Write("desktop layer not found; normal wallpaper stays"); Hide(); return; }
        Desktop.Attach(Handle, host, Screen.PrimaryScreen!.Bounds);
        Log.Write($"attached ({host.Layout})");
    }

    async void Tick()
    {
        // Explorer restarted (or the layer vanished): find it again, at most every 5 s.
        if ((host == null || !IsWindow(host.Parent) || GetParent(Handle) != host.Parent) && DateTime.Now >= nextAttachTry)
        {
            nextAttachTry = DateTime.Now.AddSeconds(5);
            Reattach();
            if (host != null && mode != "hard") Show();
        }
        if (ready && weather.Stale && mode == "running" && DateTime.Now >= nextWeather)
        {
            nextWeather = DateTime.Now.AddMinutes(5);           // don't hammer the API when offline
            SendWeather(await weather.Refresh());
        }
        Evaluate();
    }

    // ------------------------------------------------------------- pausing
    void Evaluate()
    {
        string want = "running";
        if (manualPause || locked || displayOff || FullScreenAppRunning()) want = "hard";
        else if (settings.PauseWhenCovered && DesktopCovered()) want = "soft";
        if (want != mode) _ = Apply(want);
    }

    async Task Apply(string want)
    {
        string was = mode;
        mode = want;
        var core = web.CoreWebView2;
        if (core == null) return;
        if (want == "running")
        {
            if (was == "hard") { Show(); web.Visible = true; core.Resume(); if (host != null) Desktop.Place(Handle, host, Screen.PrimaryScreen!.Bounds); }
            Post(new { type = "resume" });
        }
        else
        {
            Post(new { type = "pause" });
            if (want == "hard")
            {
                web.Visible = false;
                Hide();                                  // the static Fjord wallpaper shows through
                try { await core.TrySuspendAsync(); } catch (Exception e) { Log.Write("suspend: " + e.Message); }
            }
            else if (was == "hard") { Show(); web.Visible = true; core.Resume(); Post(new { type = "pause" }); }
        }
    }

    static void Horn(string name)
    {
        string wav = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Yggdrasil", "Theme", "Sounds", $"Yggdrasil - {name}.wav");
        try { if (File.Exists(wav)) new System.Media.SoundPlayer(wav).Play(); }
        catch (Exception e) { Log.Write("horn: " + e.Message); }
    }

    static bool FullScreenAppRunning()
    {
        // 2 = busy (full-screen app), 3 = Direct3D full-screen game, 4 = presentation mode
        return SHQueryUserNotificationState(out int s) == 0 && s is 2 or 3 or 4;
    }

    bool DesktopCovered()
    {
        IntPtr fg = GetForegroundWindow();
        if (fg == IntPtr.Zero || fg == Handle || !IsWindowVisible(fg)) return false;
        if (Array.IndexOf(ShellClasses, ClassOf(fg)) >= 0) return false;
        if (!GetWindowRect(fg, out var r)) return false;
        var wa = Screen.PrimaryScreen!.WorkingArea;
        // Maximised or full screen: covers the whole working area (a few px of slack for borders).
        return r.Left <= wa.Left + 8 && r.Top <= wa.Top + 8 && r.Right >= wa.Right - 8 && r.Bottom >= wa.Bottom - 8;
    }

    void OnSessionSwitch(object? s, SessionSwitchEventArgs e)
    {
        if (e.Reason is SessionSwitchReason.SessionLock or SessionSwitchReason.ConsoleDisconnect) locked = true;
        if (e.Reason is SessionSwitchReason.SessionUnlock or SessionSwitchReason.ConsoleConnect) locked = false;
        if (e.Reason is SessionSwitchReason.SessionUnlock && settings.UnlockHorn) Horn("Unlock");
        Evaluate();
    }

    protected override void WndProc(ref Message m)
    {
        if (m.Msg == WM_POWERBROADCAST && m.WParam.ToInt32() == PBT_POWERSETTINGCHANGE)
        {
            var ps = System.Runtime.InteropServices.Marshal.PtrToStructure<POWERBROADCAST_SETTING>(m.LParam);
            if (ps.PowerSetting == GUID_CONSOLE_DISPLAY_STATE) { displayOff = ps.Data == 0; Evaluate(); }
        }
        base.WndProc(ref m);
    }

    protected override void OnFormClosed(FormClosedEventArgs e)
    {
        watch.Stop();
        SystemEvents.SessionSwitch -= OnSessionSwitch;
        if (powerNotify != IntPtr.Zero) UnregisterPowerSettingNotification(powerNotify);
        tray.Visible = false;
        tray.Dispose();
        web.Dispose();
        base.OnFormClosed(e);
        Desktop.RefreshWallpaper();   // no frozen frame left behind
    }
}
