using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using static Yggdrasil.Sky.Native;

namespace Yggdrasil.Sky;

/// <summary>
/// The wallpaper itself: a window created directly as a child of Explorer's desktop
/// (never a normal app window, so virtual desktops and Task View leave it alone),
/// hosting a WebView2 that only ever shows the local scene in web\.
/// If Explorer restarts, the window dies with it and SkyApp makes a new one.
/// </summary>
internal sealed class SkyView : NativeWindow, IDisposable
{
    public const string Origin = "https://sky.yggdrasil/";
    static readonly Color Night = Color.FromArgb(0x0B, 0x12, 0x20);

    public Desktop.Host Host { get; private set; }
    public CoreWebView2Controller? Controller { get; private set; }
    public CoreWebView2? Core => Controller?.CoreWebView2;
    public event Action<JsonElement>? Message;
    public int Restacks { get; private set; }

    public SkyView(Desktop.Host host, Rectangle screen)
    {
        Host = host;
        var r = Desktop.ToParent(host, screen);
        CreateHandle(new CreateParams
        {
            Caption = "Yggdrasil Sky",
            Parent = host.Parent,
            X = r.Left, Y = r.Top, Width = r.Width, Height = r.Height,
            Style = unchecked((int)(WS_CHILD | WS_VISIBLE | WS_CLIPCHILDREN | WS_CLIPSIBLINGS)),
            ExStyle = WS_EX_NOACTIVATE,
        });
        Stack();
    }

    public async Task StartAsync(CoreWebView2Environment env)
    {
        Controller = await env.CreateCoreWebView2ControllerAsync(Handle);
        Controller.DefaultBackgroundColor = Night;
        Controller.Bounds = ClientBounds();
        Controller.IsVisible = true;
        var core = Controller.CoreWebView2;

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

        core.SetVirtualHostNameToFolderMapping("sky.yggdrasil", Path.Combine(AppContext.BaseDirectory, "web"),
            CoreWebView2HostResourceAccessKind.Deny);
        core.NavigationStarting += (_, a) => { if (!a.Uri.StartsWith(Origin, StringComparison.Ordinal)) a.Cancel = true; };
        core.FrameNavigationStarting += (_, a) => a.Cancel = true;
        core.NewWindowRequested += (_, a) => a.Handled = true;
        core.PermissionRequested += (_, a) => a.State = CoreWebView2PermissionState.Deny;
        core.DownloadStarting += (_, a) => a.Cancel = true;
        core.ProcessFailed += (_, a) => { Log.Write("webview process failed: " + a.ProcessFailedKind); core.Reload(); };
        core.WebMessageReceived += (_, e) =>
        {
            if (!e.Source.StartsWith(Origin, StringComparison.Ordinal)) return;
            try { using var doc = JsonDocument.Parse(e.WebMessageAsJson); Message?.Invoke(doc.RootElement.Clone()); }
            catch (JsonException) { }
        };
        core.Navigate(Origin + "index.html");
    }

    public void Post(object msg) => Core?.PostWebMessageAsJson(JsonSerializer.Serialize(msg));

    /// <summary>Our window still exists and still lives in Explorer's desktop.</summary>
    public bool Alive => Handle != IntPtr.Zero && IsWindow(Handle) && IsWindow(Host.Parent) && GetParent(Handle) == Host.Parent;

    /// <summary>
    /// Puts Sky back where it belongs if Explorer moved things (unlock, virtual-desktop
    /// switch, wallpaper change, display change). Returns what it fixed, for the log.
    /// </summary>
    public string? Ensure(Rectangle screen, bool visible)
    {
        string? fixedWhat = null;

        // Explorer can recreate the icon layer; follow it.
        if (Host.Icons != IntPtr.Zero)
        {
            IntPtr icons = FindWindowEx(Host.Parent, IntPtr.Zero, "SHELLDLL_DefView", null);
            if (icons != IntPtr.Zero && icons != Host.Icons) { Host = Host with { Icons = icons }; fixedWhat = "icons layer changed"; }
            if (GetWindow(Handle, GW_HWNDPREV) != Host.Icons) fixedWhat ??= "wallpaper layer was above Sky";
        }

        var want = Desktop.ToParent(Host, screen);
        GetWindowRect(Handle, out var have);
        var haveP = have; MapWindowPoints(IntPtr.Zero, Host.Parent, ref haveP, 2);
        if (haveP.Left != want.Left || haveP.Top != want.Top || haveP.Width != want.Width || haveP.Height != want.Height)
            fixedWhat ??= "size or position";

        if (visible && !IsWindowVisible(Handle)) fixedWhat ??= "hidden";

        if (fixedWhat != null)
        {
            Stack(want);
            if (visible) ShowWindow(Handle, SW_SHOWNA);
            if (Controller != null) Controller.Bounds = ClientBounds();
            Restacks++;
        }
        return fixedWhat;
    }

    void Stack(RECT? r = null)
    {
        uint flags = SWP_NOACTIVATE;
        if (r is { } p) SetWindowPos(Handle, Host.Icons, p.Left, p.Top, p.Width, p.Height, flags);
        else SetWindowPos(Handle, Host.Icons, 0, 0, 0, 0, flags | SWP_NOMOVE | SWP_NOSIZE);
    }

    Rectangle ClientBounds() { GetClientRect(Handle, out var c); return new Rectangle(0, 0, c.Width, c.Height); }

    public void ShowNow() => ShowWindow(Handle, SW_SHOWNA);
    public void HideNow() => ShowWindow(Handle, SW_HIDE);   // the static Fjord wallpaper shows through

    public bool IsCloaked() =>
        DwmGetWindowAttribute(Handle, DWMWA_CLOAKED, out int c, sizeof(int)) == 0 && c != 0;

    public void Dispose()
    {
        try { Controller?.Close(); } catch { }
        Controller = null;
        if (Handle != IntPtr.Zero) DestroyHandle();
    }
}
