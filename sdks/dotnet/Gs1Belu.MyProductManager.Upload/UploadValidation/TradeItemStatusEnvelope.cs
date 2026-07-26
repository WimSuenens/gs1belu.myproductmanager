using System;
using System.Collections.Generic;
using Microsoft.Kiota.Abstractions.Extensions;
using Microsoft.Kiota.Abstractions.Serialization;

namespace Gs1Belu.MyProductManager.Upload.UploadValidation;

/// <summary>
/// A hand-written response model for <c>GET /tradeitems/{gtin}</c>'s <c>metaData</c> envelope.
/// The committed effective spec's <c>tradeItem</c> schema (shared by POST body and GET response)
/// does not declare a <c>metaData</c> field at all — confirmed against
/// <c>schemas/upload/v17.yaml</c> — even though the vendor manual documents this field's runtime
/// behavior in prose. Kiota can therefore not generate it. This type is deserialized directly via
/// <see cref="Microsoft.Kiota.Abstractions.IRequestAdapter.SendAsync{ModelType}"/> against the same
/// <c>ToGetRequestInformation()</c> the generated client builds, rather than by hand-editing
/// <c>generated/</c> (forbidden — see the #31 regen-sync guarantee).
/// </summary>
internal sealed class TradeItemStatusEnvelope : IParsable
{
    public TradeItemMetaDataEnvelope? MetaData { get; set; }

    public static TradeItemStatusEnvelope CreateFromDiscriminatorValue(IParseNode parseNode)
    {
        _ = parseNode ?? throw new ArgumentNullException(nameof(parseNode));
        return new TradeItemStatusEnvelope();
    }

    public IDictionary<string, Action<IParseNode>> GetFieldDeserializers() => new Dictionary<string, Action<IParseNode>>
    {
        { "metaData", n => { MetaData = n.GetObjectValue(TradeItemMetaDataEnvelope.CreateFromDiscriminatorValue); } },
    };

    public void Serialize(ISerializationWriter writer)
    {
        _ = writer ?? throw new ArgumentNullException(nameof(writer));
        writer.WriteObjectValue("metaData", MetaData);
    }
}

internal sealed class TradeItemMetaDataEnvelope : IParsable
{
    /// <summary>Raw wire value: <c>pendingValidation</c>, <c>active</c>, or <c>incomplete</c>.</summary>
    public string? Status { get; set; }

    public List<TradeItemValidationIssueEnvelope>? ValidationResults { get; set; }

    public static TradeItemMetaDataEnvelope CreateFromDiscriminatorValue(IParseNode parseNode)
    {
        _ = parseNode ?? throw new ArgumentNullException(nameof(parseNode));
        return new TradeItemMetaDataEnvelope();
    }

    public IDictionary<string, Action<IParseNode>> GetFieldDeserializers() => new Dictionary<string, Action<IParseNode>>
    {
        { "status", n => { Status = n.GetStringValue(); } },
        {
            "validationResults", n =>
            {
                ValidationResults = n.GetCollectionOfObjectValues(TradeItemValidationIssueEnvelope.CreateFromDiscriminatorValue)?.AsList();
            }
        },
    };

    public void Serialize(ISerializationWriter writer)
    {
        _ = writer ?? throw new ArgumentNullException(nameof(writer));
        writer.WriteStringValue("status", Status);
        writer.WriteCollectionOfObjectValues("validationResults", ValidationResults);
    }
}

internal sealed class TradeItemValidationIssueEnvelope : IParsable
{
    public string? Severity { get; set; }
    public string? Code { get; set; }
    public string? Message { get; set; }

    public static TradeItemValidationIssueEnvelope CreateFromDiscriminatorValue(IParseNode parseNode)
    {
        _ = parseNode ?? throw new ArgumentNullException(nameof(parseNode));
        return new TradeItemValidationIssueEnvelope();
    }

    public IDictionary<string, Action<IParseNode>> GetFieldDeserializers() => new Dictionary<string, Action<IParseNode>>
    {
        { "severity", n => { Severity = n.GetStringValue(); } },
        { "code", n => { Code = n.GetStringValue(); } },
        { "message", n => { Message = n.GetStringValue(); } },
    };

    public void Serialize(ISerializationWriter writer)
    {
        _ = writer ?? throw new ArgumentNullException(nameof(writer));
        writer.WriteStringValue("severity", Severity);
        writer.WriteStringValue("code", Code);
        writer.WriteStringValue("message", Message);
    }
}
