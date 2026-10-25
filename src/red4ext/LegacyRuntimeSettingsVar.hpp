#pragma once

// Minimal base-only extraction of the installed release's SDK custom header:
// jackhumbert/RED4ext.SDK a8cb29c, userRuntimeSettingsVar.hpp (MIT notice in sidecar).
// Its private menu ABI is inherited from 0.2.21, not yet runtime-validated on 2.5.
#include <RED4ext/RED4ext.hpp>

namespace RED4ext::user
{
struct ConfigVarFlags
{
    uint32_t isInPreGame:1, isInGame:1, isVisible:1, isPlatformSpecific:1, isDynamic:1,
             unk20:1, isInitialized:1, listHasDisplayValues:1, canBeRestoredToDefault:1,
             isInput:1, isDisabled:1;
};
enum class EConfigVarFlags : int
{
    isInPreGame=1, isInGame=2, isVisible=4, isPlatformSpecific=8, isDynamic=0x10,
    unk20=0x20, isInitialized=0x40, listHasDisplayValues=0x80,
    canBeRestoredToDefault=0x100, isInput=0x200, isDisabled=0x400
};
DEFINE_ENUM_FLAG_OPERATORS(EConfigVarFlags);
enum class EConfigVarType : char { Bool, Int, Float, Name, IntList, FloatList, StringList, NameList };
enum class EConfigVarUpdatePolicy : char
{ Disabled, Immediately, ConfirmationRequired, RestartRequired, LoadLastCheckpointRequired };
enum class EConfigVarImportPolicy : char { ReadValue, Ignore };

#pragma pack(push, 1)
struct RuntimeSettingsVar
{
    RuntimeSettingsVar() { unk44=0xFF; unk45=0xFF; bitfield={}; }
    virtual Memory::IAllocator* __fastcall GetAllocator(RuntimeSettingsVar*) { return new Memory::DefaultAllocator(); }
    virtual RuntimeSettingsVar* __fastcall Deinitialize(bool)
    { displayNameKeys.Clear(); return this; }
    virtual bool __fastcall WasModifiedSinceLastSave()=0;
    virtual bool __fastcall HasChange()=0;
    virtual bool __fastcall IsDefault()=0;
    virtual bool __fastcall RestoreDefault(uint8_t)=0;
    virtual void __fastcall SetRequestedValue(void*)=0;
    virtual void __fastcall AcceptChange()=0;
    virtual void __fastcall RejectChange()=0;
    virtual void __fastcall MarkAsSaved()=0;
    virtual void __fastcall LoadValue(void*)=0;
    CName name{}, groupPath{}, displayName{};
    DynArray<CName> displayNameKeys;
    CName description{}, warning{};
    EConfigVarType type;
    EConfigVarUpdatePolicy updatePolicy=EConfigVarUpdatePolicy::Immediately;
    EConfigVarImportPolicy importPolicy=EConfigVarImportPolicy::ReadValue;
    uint8_t unk3B;
    ConfigVarFlags bitfield;
    uint32_t order;
    uint8_t unk44, unk45, unk46, unk47;
    uint32_t unk50_new;
};
#pragma pack(pop)
RED4EXT_ASSERT_SIZE(RuntimeSettingsVar, 0x54);
RED4EXT_ASSERT_OFFSET(RuntimeSettingsVar, name, 0x08);
RED4EXT_ASSERT_OFFSET(RuntimeSettingsVar, bitfield, 0x44);
}
