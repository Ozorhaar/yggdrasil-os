namespace Yggdrasil.Sky;

internal static class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        using var single = new Mutex(true, @"Local\YggdrasilSky", out bool first);
        if (!first) return;                         // already running
        Directory.CreateDirectory(Settings.Dir);
        ApplicationConfiguration.Initialize();
        Application.ThreadException += (_, e) => Log.Write("error: " + e.Exception);
        Application.Run(new SkyApp(args.Contains("--startup")));
    }
}
