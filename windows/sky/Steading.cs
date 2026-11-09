using System.Text.Json;

namespace Yggdrasil.Sky;

/// <summary>
/// The steading feed: what the house is doing (lights, doors, who's home, solar, smoker, printer,
/// leaks, a package or someone at a door) and tonight's Kp, read every 30 seconds from the Mac
/// mini (homelab.ozorhaar.com, home network only). It holds no Home Assistant token and
/// can't change anything; Sky only reads it.
/// </summary>
internal sealed class Steading
{
    static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(6) };
    readonly Settings settings;

    public Steading(Settings s)
    {
        settings = s;
        Http.DefaultRequestHeaders.UserAgent.ParseAdd("YggdrasilSky/1.0");
    }

    /// <summary>(house JSON, kp), or null when the feed can't be reached (away from home).</summary>
    public async Task<(JsonElement? house, double? kp)?> Read()
    {
        if (!settings.Steading || !settings.SteadingUrl.StartsWith("https://")) return null;
        try
        {
            using var doc = JsonDocument.Parse(await Http.GetStringAsync(settings.SteadingUrl));
            var root = doc.RootElement;
            JsonElement? house = root.TryGetProperty("house", out var h) && h.ValueKind == JsonValueKind.Object ? h.Clone() : null;
            double? kp = root.TryGetProperty("kp", out var k) && k.ValueKind == JsonValueKind.Number ? k.GetDouble() : null;
            return (house, kp);
        }
        catch (Exception e) { Log.Write("steading: " + e.Message); return null; }
    }
}
