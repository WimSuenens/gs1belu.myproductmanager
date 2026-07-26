using System;
using Xunit;

namespace Gs1Belu.MyProductManager.Download.Tests;

public class IdentifierValidationTests
{
    [Theory]
    [InlineData("01234567890128")]
    [InlineData("00000000000000")]
    [InlineData("99999999999999")]
    public void AssertValidGtin_accepts_conforming_values(string gtin) => Gs1BeluIdentifierValidation.AssertValidGtin(gtin);

    [Theory]
    [InlineData("02234567890128")] // second digit '2' is excluded by the spec pattern
    [InlineData("1234567890123")] // 13 digits: one short
    [InlineData("123456789012345")] // 15 digits: one too many
    [InlineData("abcdefghij1234")] // non-numeric
    public void AssertValidGtin_rejects_malformed_values(string gtin) =>
        Assert.Throws<ArgumentException>(() => Gs1BeluIdentifierValidation.AssertValidGtin(gtin));

    [Theory]
    [InlineData("5412345678901")]
    [InlineData("0000000000000")]
    public void AssertValidGln_accepts_conforming_values(string gln) => Gs1BeluIdentifierValidation.AssertValidGln(gln);

    [Theory]
    [InlineData("541234567890")] // 12 digits: one short
    [InlineData("54123456789012")] // 14 digits: one too many
    [InlineData("541234567890a")] // non-numeric
    public void AssertValidGln_rejects_malformed_values(string gln) =>
        Assert.Throws<ArgumentException>(() => Gs1BeluIdentifierValidation.AssertValidGln(gln));
}
