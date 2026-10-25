#pragma once

#include <RED4ext/RED4ext.hpp>

// Source compatibility only: the v1 ABI is selected explicitly by our exports.
namespace RED4ext
{
using Sdk = v1::Sdk;
using PluginHandle = v1::PluginHandle;
using EMainReason = v1::EMainReason;
using PluginInfo = v1::PluginInfo;
using ScriptInstance = void*; // Installed-release InstanceType.hpp declared void*.
}
