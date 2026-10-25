cmake_minimum_required(VERSION 3.24)
project(HELGA_ModSettingsNative VERSION 0.2.21 LANGUAGES CXX)

# No upstream configure_mod/install/download/compiler/archive steps are run.
if(NOT MSVC OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
  message(FATAL_ERROR "This verified ABI lane requires MSVC x64")
endif()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
get_filename_component(SOURCE_ROOT "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)
file(GLOB_RECURSE SOURCES CONFIGURE_DEPENDS "${SOURCE_ROOT}/src/red4ext/*.cpp")
add_library(mod_settings SHARED ${SOURCES})
target_include_directories(mod_settings PRIVATE
  "${SOURCE_ROOT}/src/red4ext" "${SOURCE_ROOT}/include"
  "${SOURCE_ROOT}/deps/red4ext.sdk/include"
  "${SOURCE_ROOT}/deps/red_lib/include" "${SOURCE_ROOT}/deps/red_lib/vendor"
  "${SOURCE_ROOT}/deps/cpcmake/include" "${SOURCE_ROOT}/deps/archive_xl/support/red4ext")
target_compile_definitions(mod_settings PRIVATE
  WINVER=0x0601 _WIN32_WINNT=0x0601 WIN32_LEAN_AND_MEAN NOMINMAX UNICODE _UNICODE
  _ITERATOR_DEBUG_LEVEL=0 _CRT_SECURE_NO_WARNINGS MOD_SETTINGS_DLLDIR_EX
  MOD_VERSION_STR="0.2.21" MOD_VERSION_MAJOR=0 MOD_VERSION_MINOR=2 MOD_VERSION_PATCH=21)
target_compile_options(mod_settings PRIVATE /MP /EHsc /Zi /utf-8
  "/FI${SOURCE_ROOT}/src/red4ext/LocalSdkCompatibility.hpp")
target_link_options(mod_settings PRIVATE /DEBUG:FULL /INCREMENTAL:NO /OPT:REF /OPT:ICF)
target_link_libraries(mod_settings PRIVATE Version User32)

add_executable(BorrowedTextAbiTest "${SOURCE_ROOT}/tests/BorrowedTextAbiTest.cpp")
target_include_directories(BorrowedTextAbiTest PRIVATE "${SOURCE_ROOT}/src/red4ext")
# Keep assertions enabled even in the release-mode marshalling test.
target_compile_options(BorrowedTextAbiTest PRIVATE /UNDEBUG)
