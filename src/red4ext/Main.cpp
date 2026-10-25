#include "RED4ext/RTTISystem.hpp"
#include "Red/TypeInfo/Registrar.hpp"
#include "Utils.hpp"
#include <RED4ext/Common.hpp>
#include <Windows.h>
#include <stdio.h>


#include "ModSettings.hpp"

#include <RedLib.hpp>
#include <ArchiveXL.hpp>
#include <CyberpunkMod.hpp>
#include <CNames.hpp>

namespace ModSettings {
const RED4ext::Sdk *sdk;
RED4ext::PluginHandle pluginHandle;
} // namespace ModSettings

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
  switch (fdwReason) {
  case DLL_PROCESS_ATTACH:
    ModSettings::ModSettings::GetInstance();
    break;
  }
  return true;
}

RED4EXT_C_EXPORT bool RED4EXT_CALL Main(RED4ext::PluginHandle aHandle, RED4ext::EMainReason aReason,
                                        const RED4ext::Sdk *aSdk) {
  switch (aReason) {
  case RED4ext::EMainReason::Load: {
    ModSettings::sdk = aSdk;
    ModSettings::pluginHandle = aHandle;

    aSdk->logger->Info(aHandle, "Starting up Mod Settings " MOD_VERSION_STR);
    auto ptr = GetModuleHandle(nullptr);
    aSdk->logger->InfoF(aHandle, "Base address: %p", ptr);

    for (const auto& relative : {"r6/scripts/mod_settings", "archive/pc/mod/ModSettings.archive",
                                "archive/pc/mod/ModSettings.archive.xl", "archive/pc/mod/ModSettings.xl"}) {
      if (std::filesystem::exists(Utils::GetRootDir() / relative))
        aSdk->logger->WarnF(aHandle, "Legacy Mod Settings path exists; manage it in Vortex, not automatically delete it: %s", relative);
    }

    Red::TypeInfoRegistrar::RegisterDiscovered();

    aSdk->scripts->Add(aHandle, L"packed.reds");
    aSdk->scripts->Add(aHandle, L"module.reds");
    ArchiveXL::RegisterArchive(aHandle, "ModSettings.archive");
    ModModuleFactory::GetInstance().Load(aSdk, aHandle);
    // Engine::RTTIRegistrar::RegisterPending();

    break;
  }
  case RED4ext::EMainReason::Unload: {
    aSdk->logger->Info(aHandle, "Shutting down");
    ModModuleFactory::GetInstance().Unload(aSdk, aHandle);
    break;
  }
  }

  return true;
}

RED4EXT_C_EXPORT void RED4EXT_CALL Query(RED4ext::PluginInfo *aInfo) {
  aInfo->name = L"Mod Settings";
  aInfo->author = L"Jack Humbert";
  aInfo->version = RED4EXT_V1_SEMVER(MOD_VERSION_MAJOR, MOD_VERSION_MINOR, MOD_VERSION_PATCH);
  // aInfo->runtime = RED4EXT_RUNTIME_LATEST;
  aInfo->runtime = RED4EXT_V1_RUNTIME_VERSION_2_50;
  aInfo->sdk = RED4EXT_V1_SDK_VERSION_CURRENT;
}

RED4EXT_C_EXPORT uint32_t RED4EXT_CALL Supports() { return RED4EXT_API_VERSION_1_COMPAT_0; }
