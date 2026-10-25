#pragma once

#include <RED4ext/Common.hpp>
#include <RED4ext/RED4ext.hpp>
#include <RED4ext/Scripting/Natives/Generated/ink/ActionName.hpp>
#include <RedLib.hpp>
#include <cstring>

struct ActionNameEx : Red::ink::ActionName
{
    Red::CName ToName()
    {
        // Retail SetActionName writes +0x40; IsAction compares the same qword.
        // The selected generated SDK keeps it unnamed, so copy its verified
        // representation without redefining the SDK class or aliasing bytes.
        Red::CName action;
        static_assert(sizeof(action) == 8);
        std::memcpy(&action, this->unk40, sizeof(action));
        return action;
    }
};

RTTI_EXPAND_CLASS(Red::ink::ActionName, ActionNameEx, {
    RTTI_METHOD(ToName);
});
