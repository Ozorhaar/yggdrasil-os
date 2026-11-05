using static Yggdrasil.Sky.Native;

namespace Yggdrasil.Sky;

/// <summary>
/// Finds Explorer's wallpaper layer so Sky can sit behind the desktop icons, the way
/// every live-wallpaper app does: ask Progman (Explorer's desktop window) to create the
/// layer, then put our own child window into it. This only sends Explorer a window
/// message; nothing is injected into or patched in Explorer. The message (0x052C) is
/// undocumented, so a big Windows update can change the layout; if that happens Sky
/// stays out of the way and the normal wallpaper shows.
/// </summary>
internal static class Desktop
{
    /// <param name="Parent">Window Sky lives in.</param>
    /// <param name="Icons">SHELLDLL_DefView: Sky sits directly below it (24H2+ layout), else zero.</param>
    public sealed record Host(IntPtr Parent, IntPtr Icons, string Layout);

    /// <summary>Asks Explorer for its wallpaper layer, then finds it.</summary>
    public static Host? Find()
    {
        IntPtr progman = FindWindow("Progman", null);
        if (progman == IntPtr.Zero) return null;
        SendMessageTimeout(progman, 0x052C, new IntPtr(0xD), new IntPtr(0x1), SMTO_NORMAL, 1000, out _);
        SendMessageTimeout(progman, 0x052C, IntPtr.Zero, IntPtr.Zero, SMTO_NORMAL, 1000, out _);
        return Current();
    }

    /// <summary>Finds the layer without poking Explorer (cheap enough to call twice a second).</summary>
    public static Host? Current()
    {
        IntPtr progman = FindWindow("Progman", null);
        if (progman == IntPtr.Zero) return null;

        // Windows 11 24H2 and later: icons (SHELLDLL_DefView) and the wallpaper (WorkerW)
        // are both children of Progman. Sky sits between them.
        IntPtr icons = FindWindowEx(progman, IntPtr.Zero, "SHELLDLL_DefView", null);
        IntPtr innerWorker = FindWindowEx(progman, IntPtr.Zero, "WorkerW", null);
        if (icons != IntPtr.Zero && innerWorker != IntPtr.Zero)
            return new Host(progman, icons, "progman-child");

        // Older layout: a top-level WorkerW holds the icons; the next WorkerW after it is
        // the wallpaper layer, and Sky lives inside that.
        IntPtr worker = IntPtr.Zero;
        EnumWindows((top, _) =>
        {
            if (FindWindowEx(top, IntPtr.Zero, "SHELLDLL_DefView", null) != IntPtr.Zero)
                worker = FindWindowEx(IntPtr.Zero, top, "WorkerW", null);
            return worker == IntPtr.Zero;
        }, IntPtr.Zero);
        return worker != IntPtr.Zero ? new Host(worker, IntPtr.Zero, "workerw") : null;
    }

    /// <summary>The screen rectangle converted into the host window's coordinates.</summary>
    public static RECT ToParent(Host host, Rectangle screen)
    {
        var r = new RECT { Left = screen.Left, Top = screen.Top, Right = screen.Right, Bottom = screen.Bottom };
        MapWindowPoints(IntPtr.Zero, host.Parent, ref r, 2);
        return r;
    }

    /// <summary>Repaints the normal wallpaper (used when we quit so no stale frame is left behind).</summary>
    public static void RefreshWallpaper()
    {
        var path = new System.Text.StringBuilder(1024);
        if (SystemParametersInfo(SPI_GETDESKWALLPAPER, (uint)path.Capacity, path, 0))
            SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, path, SPIF_SENDCHANGE);
    }
}
