using System.Text.Json;

namespace Yggdrasil.Sky;

/// <summary>
/// Current weather code and today's sunrise / sunset from Open-Meteo (free, no
/// account, no key), every 30 minutes. This is the app's only network call.
/// </summary>
internal sealed class Weather
{
    public sealed record Now(int Code, long Sunrise, long Sunset, long FetchedAt, double? TempF = null);

    static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(10) };
    readonly Settings settings;
    readonly string cacheFile = Path.Combine(Settings.Dir, "weather.json");

    public Now? Last { get; private set; }

    public Weather(Settings s)
    {
        settings = s;
        Http.DefaultRequestHeaders.UserAgent.ParseAdd("YggdrasilSky/1.0");
        try { Last = JsonSerializer.Deserialize<Now>(File.ReadAllText(cacheFile)); } catch { }
    }

    public bool Stale => Last is null || DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() - Last.FetchedAt > 30 * 60_000;

    public async Task<Now?> Refresh()
    {
        if (!settings.Weather) return null;
        string url = FormattableString.Invariant(
            $"https://api.open-meteo.com/v1/forecast?latitude={settings.Latitude:0.###}&longitude={settings.Longitude:0.###}&current=weather_code,temperature_2m&temperature_unit=fahrenheit&daily=sunrise,sunset&timezone=auto&forecast_days=1&timeformat=unixtime");
        try
        {
            using var doc = JsonDocument.Parse(await Http.GetStringAsync(url));
            var root = doc.RootElement;
            int code = root.GetProperty("current").GetProperty("weather_code").GetInt32();
            var daily = root.GetProperty("daily");
            long rise = daily.GetProperty("sunrise")[0].GetInt64() * 1000;
            long set = daily.GetProperty("sunset")[0].GetInt64() * 1000;
            if (code < 0 || code > 99 || set <= rise) return Last;   // ignore nonsense
            double? temp = root.GetProperty("current").TryGetProperty("temperature_2m", out var tp) && tp.ValueKind == JsonValueKind.Number ? tp.GetDouble() : null;
            Last = new Now(code, rise, set, DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(), temp);
            File.WriteAllText(cacheFile, JsonSerializer.Serialize(Last));
        }
        catch (Exception e) { Log.Write("weather: " + e.Message); }
        return Last;
    }
}

internal static class Log
{
    static readonly string File_ = Path.Combine(Settings.Dir, "sky.log");
    public static void Write(string line)
    {
        try
        {
            if (File.Exists(File_) && new FileInfo(File_).Length > 256 * 1024) File.Delete(File_);
            File.AppendAllText(File_, $"{DateTime.Now:yyyy-MM-dd HH:mm:ss} {line}{Environment.NewLine}");
        }
        catch { }
    }
}
