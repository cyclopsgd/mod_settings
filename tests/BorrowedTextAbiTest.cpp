#include "BorrowedTextAbi.hpp"
#include <cassert>
#include <cstring>
#include <string>

namespace
{
const void* expectedType;
const char* expectedData;
std::uint32_t expectedSize;
unsigned calls;

bool __fastcall FakeFromString(const void* type, void* output,
                              ModSettings::Abi::BorrowedTextDescriptor* input)
{
    assert(type == expectedType);
    assert(input->data == expectedData && input->size == expectedSize);
    assert(input->alignment == 0 && input->allocator[0] == 0 && input->allocator[1] == 0);
    ++calls;
    *static_cast<unsigned*>(output) = input->size;
    // The real enum parser changes its descriptor. Never mutate its owner.
    ++input->data;
    if (input->size) --input->size;
    return true;
}
}

int main()
{
    std::uintptr_t table[15]{};
    table[14] = reinterpret_cast<std::uintptr_t>(&FakeFromString);
    struct Object { const std::uintptr_t* table; } object{table};
    expectedType = &object;
    for (const auto& text : {std::string("true"), std::string(80, 'x'), std::string()})
    {
        const auto original = text;
        expectedData = text.c_str();
        expectedSize = static_cast<std::uint32_t>(text.size());
        unsigned result{};
        assert(ModSettings::Abi::ParseText(&object, &result, text.c_str(), expectedSize));
        assert(result == expectedSize && text == original);
    }
    unsigned result{};
    assert(!ModSettings::Abi::ParseText(nullptr, &result, "x", 1));
    assert(!ModSettings::Abi::ParseText(&object, nullptr, "x", 1));
    assert(!ModSettings::Abi::ParseText(&object, &result, nullptr, 0));
    assert(calls == 3);
}
