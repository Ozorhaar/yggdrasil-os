using static Yggdrasil.Sky.Native;

namespace Yggdrasil.Sky;

/// <summary>
/// Puts a window behind the desktop icons, the way every live-wallpaper app does:
/// ask Progman (Explorer's desktop window) to create its wallpaper layer, then
/// make our window a child of it. This only sends Explorer a window message and
/// re-parents our own window; nothing is injected into or patched in Explorer.
/// The message (0x052C) is undocumented, so a big Windows update can change the
/// layout; if attaching fails the app simply stays hidden and the normal
/// wallpaper shows.
/// </summary>
internal static class Desktop
{
    public sealed record Host(IntPtr Parent, IntPtr InsertAfter, string Layout);

    public static Host? Find()
    {
        IntPtr progman = FindWindow("Progman", null);
        if (progman == IntPtr.Zero) return null;
        SendMessageTimeout(progman, 0x052C, new IntPtr(0xD), new IntPtr(0x1), SMTO_NORMAL, 1000, out _);
        SendMessageTimeout(progman, 0x052C, IntPtr.Zero, IntPtr.Zero, SMTO_NORMAL, 1000, out _);

        // Windows 11 24H2 and later: icons (SHELLDLL_DefView) and the wallpaper layer
        // (WorkerW) are both children of Progman. Sit between them.
        IntPtr defView = FindWindowEx(progman, IntPtr.Zero, "SHELLDLL_DefView", null);
        IntPtr innerWorker = FindWindowEx(progman, IntPtr.Zero, "WorkerW", null);
        if (defView != IntPtr.Zero && innerWorker != IntPtr.Zero)
            return new Host(progman, defView, "progman-child");

        // Older layout: a top-level WorkerW holds the icons; the next WorkerW after it
        // is the wallpaper layer.
        IntPtr worker = IntPtr.Zero;
        EnumWindows((top, _) =>
        {
            if (FindWindowEx(top, IntPtr.Zero, "SHELLDLL_DefView", null) != IntPtr.Zero)
                worker = FindWindowEx(IntPtr.Zero, top, "WorkerW", null);
            return worker == IntPtr.Zero;
        }, IntPtr.Zero);
        return worker != IntPtr.Zero ? new Host(worker, IntPtr.Zero, "workerw") : null;
    }

    /// <summary>Re-parents <paramref name="hwnd"/> under the host and fills the given screen rectangle.</summary>
    public static void Attach(IntPtr hwnd, Host host, Rectangle screen)
    {
        long style = GetWindowLongPtr(hwnd, GWL_STYLE).ToInt64();
        style = (style & ~WS_POPUP) | WS_CHILD | WS_VISIBLE;
        SetWindowLongPtr(hwnd, GWL_STYLE, new IntPtr(style));
        SetParent(hwnd, host.Parent);
        Place(hwnd, host, screen);
    }

    public static void Place(IntPtr hwnd, Host host, Rectangle screen)
    {
        var r = new RECT { Left = screen.Left, Top = screen.Top, Right = screen.Right, Bottom = screen.Bottom };
        MapWindowPoints(IntPtr.Zero, host.Parent, ref r, 2);   // screen -> parent coordinates
        uint flags = SWP_NOACTIVATE | SWP_SHOWWINDOW;
        SetWindowPos(hwnd, host.InsertAfter, r.Left, r.Top, r.Width, r.Height, flags);
    }

    /// <summary>Repaints the normal wallpaper (used when we quit so no stale frame is left behind).</summary>
    public static void RefreshWallpaper()
    {
        var path = new System.Text.StringBuilder(1024);
        if (SystemParametersInfo(SPI_GETDESKWALLPAPER, (uint)path.Capacity, path, 0))
            SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, path, SPIF_SENDCHANGE);
    }
}
