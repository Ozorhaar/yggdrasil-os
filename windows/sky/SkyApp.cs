using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using Microsoft.Win32;
using static Yggdrasil.Sky.Native;

namespace Yggdrasil.Sky;

/// <summary>
/// Runs Sky: the tray icon, the wallpaper view, the weather, and the watchdog that
/// keeps the view in place and pauses it whenever nobody can see it.
/// </summary>
internal sealed class SkyApp : ApplicationContext
{
    static readonly string[] ShellClasses = { "Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "SHELLDLL_DefView" };

    readonly Settings settings = Settings.Load();
    readonly Weather weather;
    readonly NotifyIcon tray = new();
    readonly ToolStripMenuItem pauseItem = new("Pause");
    readonly System.Windows.Forms.Timer watch = new() { Interval = 500 };
    readonly PowerWindow power;
    readonly bool startup;

    CoreWebView2Environment? env;
    SkyView? view;
    bool ready, manualPause, locked, displayOff, creating;
    string mode = "running";            // running | soft (covered: stop drawing) | hard (hidden + suspended)
    DateTime nextCreate = DateTime.MinValue, nextWeather = DateTime.MinValue;
    int fixesLogged;

    public SkyApp(bool startup)
    {
        this.startup = startup;
        weather = new Weather(settings);
        power = new PowerWindow(off => { displayOff = off; Evaluate(); });

        var menu = new ContextMenuStrip();
        menu.Items.Add("Show the demo (80 s)", null, (_, _) => view?.Post(new { type = "demo" }));
        menu.Items.Add(pauseItem);
        pauseItem.Click += (_, _) => { manualPause = !manualPause; pauseItem.Text = manualPause ? "Resume" : "Pause"; Evaluate(); };
        menu.Items.Add("Refresh weather", null, async (_, _) => SendWeather(await weather.Refresh()));
        menu.Items.Add("Open settings folder", null, (_, _) =>
            System.Diagnostics.Process.Start("explorer.exe", $"\"{Settings.Dir}\""));
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Quit Yggdrasil Sky", null, (_, _) => ExitThread());
        using (var s = typeof(SkyApp).Assembly.GetManifestResourceStream("Yggdrasil.Sky.assets.yggdrasil.ico"))
            tray.Icon = s != null ? new Icon(s) : SystemIcons.Application;
        tray.Text = "Yggdrasil Sky";
        tray.ContextMenuStrip = menu;
        tray.Visible = true;

        SystemEvents.SessionSwitch += OnSessionSwitch;
        watch.Tick += (_, _) => Tick();
        _ = StartAsync();
    }

    async Task StartAsync()
    {
        // Windows 8+ never plays its own sign-in sound, so the sign-in tune comes from here.
        if (startup && settings.SignInHorn) Play("Sign In");
        var opts = new CoreWebView2EnvironmentOptions("--disable-background-networking --disable-sync --no-first-run");
        env = await CoreWebView2Environment.CreateAsync(null, Path.Combine(Settings.Dir, "WebView2"), opts);
        await CreateView();
        watch.Start();
    }

    // ------------------------------------------------------------- the view
    async Task CreateView()
    {
        if (creating || env == null) return;
        creating = true;
        try
        {
            view?.Dispose(); view = null; ready = false;
            var host = Desktop.Find();
            if (host == null) { Log.Write("desktop layer not found; normal wallpaper stays"); return; }
            var v = new SkyView(host, Screen.PrimaryScreen!.Bounds);
            v.Message += OnMessage;
            view = v;
            await v.StartAsync(env);
            mode = "running";
            Log.Write($"attached ({host.Layout})");
        }
        catch (Exception e) { Log.Write("create: " + e.Message); view?.Dispose(); view = null; }
        finally { creating = false; nextCreate = DateTime.Now.AddSeconds(5); }
    }

    async void OnMessage(JsonElement m)
    {
        if (!m.TryGetProperty("type", out var t) || t.GetString() != "ready" || view == null) return;
        ready = true;
        view.Post(new { type = "fps", fps = settings.Fps });
        view.Post(new { type = "calm", fps = settings.CalmFps });
        view.Post(new { type = "scale", scale = settings.RenderScale });
        SendWeather(weather.Last);
        if (weather.Stale) SendWeather(await weather.Refresh());
        var want = mode; mode = "running";
        if (want != "running") _ = Apply(want); else Evaluate();
    }

    void SendWeather(Weather.Now? w)
    {
        if (w != null && ready) view?.Post(new { type = "weather", code = w.Code, sunrise = w.Sunrise, sunset = w.Sunset });
    }

    async void Tick()
    {
        // Explorer restarted, or our window went with an old desktop: make a new one.
        if (view == null || !view.Alive)
        {
            if (!creating && DateTime.Now >= nextCreate)
            {
                if (view != null) Log.Write("desktop changed; re-attaching");
                await CreateView();
            }
            return;
        }

        // Unlock, virtual-desktop switches and wallpaper changes can put Explorer's
        // wallpaper layer back on top of Sky: put Sky back (twice a second).
        string? fix = view.Ensure(Screen.PrimaryScreen!.Bounds, visible: mode != "hard");
        if (fix != null && fixesLogged < 200) { fixesLogged++; Log.Write($"restacked: {fix}{(view.IsCloaked() ? " (cloaked)" : "")}"); }

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
        Log.Write($"{was} -> {want}{(locked ? " [locked]" : "")}{(displayOff ? " [display off]" : "")}{(manualPause ? " [paused]" : "")}");
        var v = view; var c = v?.Controller;
        if (v == null || c == null || !ready) return;
        try
        {
            if (want == "hard")
            {
                v.Post(new { type = "pause" });
                c.IsVisible = false;
                v.HideNow();
                await c.CoreWebView2.TrySuspendAsync();
                return;
            }
            if (was == "hard")
            {
                v.ShowNow();
                c.IsVisible = true;
                c.CoreWebView2.Resume();
                v.Ensure(Screen.PrimaryScreen!.Bounds, visible: true);
            }
            v.Post(new { type = want == "running" ? "resume" : "pause" });
        }
        catch (Exception e) { Log.Write("apply: " + e.Message); }
    }

    static bool FullScreenAppRunning()
    {
        // 2 = busy (full-screen app), 3 = Direct3D full-screen game, 4 = presentation mode
        return SHQueryUserNotificationState(out int s) == 0 && s is 2 or 3 or 4;
    }

    bool DesktopCovered()
    {
        IntPtr fg = GetForegroundWindow();
        if (fg == IntPtr.Zero || !IsWindowVisible(fg)) return false;
        if (Array.IndexOf(ShellClasses, ClassOf(fg)) >= 0) return false;
        if (!GetWindowRect(fg, out var r)) return false;
        var wa = Screen.PrimaryScreen!.WorkingArea;
        // Maximised or full screen: covers the whole working area (a few px of slack for borders).
        return r.Left <= wa.Left + 8 && r.Top <= wa.Top + 8 && r.Right >= wa.Right - 8 && r.Bottom >= wa.Bottom - 8;
    }

    void OnSessionSwitch(object? s, SessionSwitchEventArgs e)
    {
        if (e.Reason is SessionSwitchReason.SessionLock or SessionSwitchReason.ConsoleDisconnect or SessionSwitchReason.RemoteDisconnect) locked = true;
        if (e.Reason is SessionSwitchReason.SessionUnlock or SessionSwitchReason.ConsoleConnect or SessionSwitchReason.RemoteConnect) locked = false;
        if (e.Reason is SessionSwitchReason.SessionUnlock && settings.UnlockHorn) Play("Unlock");
        Evaluate();
    }

    static void Play(string name)
    {
        // Install.ps1 records which build's theme folder is current.
        string root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Yggdrasil", "Theme");
        string theme = root;
        try { var c = File.ReadAllText(Path.Combine(root, "current.txt")).Trim(); if (Directory.Exists(c)) theme = c; } catch { }
        string wav = Path.Combine(theme, "Sounds", $"Yggdrasil - {name}.wav");
        try { if (File.Exists(wav)) new System.Media.SoundPlayer(wav).Play(); }
        catch (Exception e) { Log.Write("sound: " + e.Message); }
    }

    protected override void ExitThreadCore()
    {
        watch.Stop();
        SystemEvents.SessionSwitch -= OnSessionSwitch;
        power.Dispose();
        tray.Visible = false;
        tray.Dispose();
        view?.Dispose();
        Desktop.RefreshWallpaper();   // no frozen frame left behind
        base.ExitThreadCore();
    }

    /// <summary>Hidden window that hears "display on/off" from Windows.</summary>
    sealed class PowerWindow : NativeWindow, IDisposable
    {
        readonly Action<bool> onChange;
        readonly IntPtr notify;
        public PowerWindow(Action<bool> onChange)
        {
            this.onChange = onChange;
            CreateHandle(new CreateParams { Caption = "Yggdrasil Sky power" });   // never shown
            var guid = GUID_CONSOLE_DISPLAY_STATE;
            notify = RegisterPowerSettingNotification(Handle, ref guid, 0);
        }
        protected override void WndProc(ref Message m)
        {
            if (m.Msg == WM_POWERBROADCAST && m.WParam.ToInt32() == PBT_POWERSETTINGCHANGE)
            {
                var ps = System.Runtime.InteropServices.Marshal.PtrToStructure<POWERBROADCAST_SETTING>(m.LParam);
                if (ps.PowerSetting == GUID_CONSOLE_DISPLAY_STATE) onChange(ps.Data == 0);
            }
            base.WndProc(ref m);
        }
        public void Dispose() { if (notify != IntPtr.Zero) UnregisterPowerSettingNotification(notify); DestroyHandle(); }
    }
}
