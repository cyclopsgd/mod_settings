#pragma once

#include <cstddef>
#include <cstdint>
#include <type_traits>

namespace ModSettings::Abi
{
// The retail 2.5 caller passes this pointer/size prefix, NOT a CString object.
// The zeroed tail preserves the old RawBuffer extent without owning any data.
struct BorrowedTextDescriptor
{
    const char* data;
    std::uint32_t size;
    std::uint32_t alignment{};
    std::uint64_t allocator[2]{};
};
static_assert(sizeof(void*) == 8);
static_assert(sizeof(BorrowedTextDescriptor) == 0x20);
static_assert(offsetof(BorrowedTextDescriptor, data) == 0);
static_assert(offsetof(BorrowedTextDescriptor, size) == 8);
static_assert(std::is_trivially_destructible_v<BorrowedTextDescriptor>);

inline bool ParseText(const void* type, void* output, const char* data, std::uint32_t size)
{
    if (!type || !output || !data)
        return false;

    BorrowedTextDescriptor input{data, size};
    // Game RVA 0x6c2c44 dispatches this exact RCX/RDX/R8 contract via +0x70.
    // Enum parsing may advance the LOCAL descriptor; the CString stays owned
    // and unchanged by its caller. This must not invoke the SDK's CString ABI.
    using Function = bool (__fastcall*)(const void*, void*, BorrowedTextDescriptor*);
    const auto* table = *static_cast<const std::uintptr_t* const*>(type);
    const auto function = reinterpret_cast<Function>(table[0x70 / sizeof(void*)]);
    return function(type, output, &input);
}
}
