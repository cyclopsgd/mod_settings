#include "ScriptData.hpp"
#include "ScriptDefinitions/ScriptDefinitions.hpp"
#include "ScriptDefinitions/ScriptProperty.hpp"
#include "BorrowedTextAbi.hpp"
#include <RED4ext/Scripting/Natives/Generated/ink/ActionName.hpp>
#include <RED4ext/Callback.hpp>
#include <RED4ext/Scripting/Functions.hpp>
#include <RED4ext/Scripting/Stack.hpp>
#include <type_traits>
using Callback = RED4ext::Callback<void(*)()>;
static_assert(sizeof(Callback)==0x48);
static_assert(offsetof(Callback, handler)==0x40);
static_assert(sizeof(RED4ext::CBaseFunction)==0xF0);
static_assert(sizeof(RED4ext::CStackFrame)==0xA8);
static_assert(!std::is_copy_constructible_v<RED4ext::CStackFrame>);
static_assert(sizeof(ModSettings::ScriptDefinition)==0x40);
static_assert(offsetof(ModSettings::ScriptData, classes)==0xD8);
static_assert(sizeof(ModSettings::ScriptClass)==0xD8);
static_assert(offsetof(ModSettings::ScriptClass, functions)==0x90);
static_assert(sizeof(ModSettings::ScriptProperty)==0xC0);
static_assert(offsetof(ModSettings::ScriptProperty, type)==0xB8);
static_assert(sizeof(RED4ext::ink::ActionName)==0x58);
static_assert(offsetof(RED4ext::ink::ActionName, unk40)==0x40);
