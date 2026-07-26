#if NETSTANDARD2_0
namespace System.Runtime.CompilerServices
{
    // netstandard2.0 has no built-in IsExternalInit; the compiler only needs this type to exist to
    // allow C# 9 `record`/init-only members. net8.0 already ships it, hence the #if.
    internal static class IsExternalInit
    {
    }
}
#endif
