using System;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

namespace Gs1Belu.MyProductManager.Download.Auth;

/// <summary>
/// The observation the <c>Sunset</c> header carries: the raw value as sent, the parsed instant (if
/// it parsed as an HTTP-date), and whether that instant has already passed.
/// </summary>
public sealed record SunsetNotice(string Raw, DateTimeOffset? ParsedAt, bool IsPast);

/// <summary>
/// Observes the <c>Sunset</c> header (RFC 8594) GS1 uses to announce that an API version will stop
/// responding — the Download manual documents this as best practice to monitor, including preparing
/// for a date already in the past. Dependency-free and purely observational, a sibling of
/// <see cref="LoggingHandler"/>: it never alters, retries, or fails a request, and reports through
/// the same plain-callback seam. A response without the header costs nothing beyond the lookup.
/// </summary>
internal sealed class SunsetHandler : DelegatingHandler
{
    private readonly Action<string>? _log;
    private readonly Action<SunsetNotice>? _onSunset;

    public SunsetHandler(Action<string>? log, Action<SunsetNotice>? onSunset)
    {
        _log = log;
        _onSunset = onSunset;
    }

    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var response = await base.SendAsync(request, cancellationToken).ConfigureAwait(false);

        var raw = response.Headers.TryGetValues("Sunset", out var values) ? values.FirstOrDefault() : null;
        if (raw is null)
        {
            return response;
        }

        DateTimeOffset? parsedAt = DateTimeOffset.TryParse(raw, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var parsed)
            ? parsed
            : null;
        var notice = new SunsetNotice(raw, parsedAt, parsedAt is not null && parsedAt <= DateTimeOffset.UtcNow);

        _log?.Invoke(FormatMessage(notice));
        _onSunset?.Invoke(notice);

        return response;
    }

    private static string FormatMessage(SunsetNotice notice)
    {
        if (notice.ParsedAt is null)
        {
            return $"Sunset: GS1 announced an API-version sunset but the header value could not be parsed as an HTTP-date: \"{notice.Raw}\".";
        }

        if (notice.IsPast)
        {
            return $"Sunset: this API version's announced sunset ({notice.ParsedAt:O}) is already in the past — it may stop responding at any time.";
        }

        var days = (notice.ParsedAt.Value - DateTimeOffset.UtcNow).Days;
        return $"Sunset: GS1 announced this API version will stop responding at {notice.ParsedAt:O} (in {days} days). Plan a version migration.";
    }
}
