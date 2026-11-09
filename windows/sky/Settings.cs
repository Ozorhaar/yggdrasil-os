using System.Text.Json;

namespace Yggdrasil.Sky;

/// <summary>%LOCALAPPDATA%\Yggdrasil\Sky\settings.json — created with defaults on first run.</summary>
internal sealed class Settings
{
    public double Latitude { get; set; } = 41.134;     // Cuyahoga Falls, Ohio (same as the launcher)
    public double Longitude { get; set; } = -81.485;
    public int Fps { get; set; } = 15;                  // rain, snow, storms, aurora, the demo
    public int CalmFps { get; set; } = 5;               // everything else: drifting clouds, shimmering water (0 = once a minute)
    public double RenderScale { get; set; } = 1.0;      // 0.5-1: draw at lower resolution if the GPU ever struggles
    public bool PauseWhenCovered { get; set; } = true;  // maximised or full-screen window in front
    public bool Weather { get; set; } = true;
    public bool SailWind { get; set; } = true;          // the longship's sail fills with the real wind
    public bool SignInHorn { get; set; } = true;        // horn call when Windows starts Sky at sign-in
    public bool UnlockHorn { get; set; } = false;       // short horn on every unlock
    public bool Steading { get; set; } = true;          // the longhouse and longship follow the house (home network only)
    public string SteadingUrl { get; set; } = "https://homelab.ozorhaar.com/steading";

    public static string Dir { get; } =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Yggdrasil", "Sky");

    static readonly JsonSerializerOptions Json = new() { WriteIndented = true };

    public static Settings Load()
    {
        Directory.CreateDirectory(Dir);
        string file = Path.Combine(Dir, "settings.json");
        Settings s;
        try { s = File.Exists(file) ? JsonSerializer.Deserialize<Settings>(File.ReadAllText(file)) ?? new() : new(); }
        catch { s = new(); }
        s.Latitude = Math.Clamp(s.Latitude, -90, 90);
        s.Longitude = Math.Clamp(s.Longitude, -180, 180);
        s.Fps = Math.Clamp(s.Fps, 5, 30);
        s.CalmFps = Math.Clamp(s.CalmFps, 0, 15);
        s.RenderScale = Math.Clamp(s.RenderScale, 0.5, 1.0);
        try { File.WriteAllText(file, JsonSerializer.Serialize(s, Json)); } catch { /* read-only is fine */ }
        return s;
    }
}
