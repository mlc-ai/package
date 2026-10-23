cmake_minimum_required(VERSION 3.31)
project(mlc_llvm_probe LANGUAGES C CXX)
set(ZLIB_USE_STATIC_LIBS ON)
find_package(LLVM CONFIG REQUIRED)
if(NOT LLVM_PACKAGE_VERSION VERSION_EQUAL "23.1.1")
  message(FATAL_ERROR "Unexpected LLVM version: ${LLVM_PACKAGE_VERSION}")
endif()

# A missing export or stale path anywhere in the SDK must fail configuration.
foreach(name IN LISTS LLVM_AVAILABLE_LIBS)
  if(NOT TARGET "${name}")
    message(FATAL_ERROR "Missing LLVM export: ${name}")
  endif()
  get_target_property(kind "${name}" TYPE)
  if(NOT kind STREQUAL "STATIC_LIBRARY" AND NOT kind STREQUAL "INTERFACE_LIBRARY")
    message(FATAL_ERROR "Unexpected non-static LLVM export: ${name} (${kind})")
  endif()
endforeach()
foreach(name ${LLVM_AVAILABLE_LIBS} ZLIB::ZLIB zstd::libzstd_static)
  get_target_property(kind "${name}" TYPE)
  if(kind STREQUAL "INTERFACE_LIBRARY")
    continue()
  endif()
  get_target_property(location "${name}" IMPORTED_LOCATION_RELEASE)
  if(NOT location)
    get_target_property(location "${name}" IMPORTED_LOCATION)
  endif()
  file(REAL_PATH "${location}" actual)
  file(REAL_PATH "${MLC_LLVM_EXPECTED_PREFIX}" expected)
  cmake_path(IS_PREFIX expected "${actual}" NORMALIZE inside)
  if(NOT inside)
    message(FATAL_ERROR "${name} resolves outside the SDK: ${actual}")
  endif()
endforeach()

foreach(feature LLVM_ENABLE_LIBXML2 LLVM_ENABLE_LIBEDIT LLVM_ENABLE_FFI
    LLVM_WITH_Z3 LLVM_ENABLE_CURL LLVM_ENABLE_HTTPLIB LLVM_ENABLE_DIA_SDK)
  if(${feature})
    message(FATAL_ERROR "Unexpected optional dependency enabled: ${feature}")
  endif()
endforeach()

llvm_map_components_to_libnames(libraries Core OrcJIT Support native IRReader BitWriter Linker Passes Object DebugInfoDWARF)
option(MLC_LLVM_USE_CONFIG_FLAGS "Link using llvm-config output instead of imported targets" OFF)
if(MLC_LLVM_USE_CONFIG_FLAGS)
  if(EXISTS "${LLVM_TOOLS_BINARY_DIR}/llvm-config.py")
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    set(llvm_config_command "${Python3_EXECUTABLE}" "${LLVM_TOOLS_BINARY_DIR}/llvm-config.py")
  else()
    set(llvm_config_command "${LLVM_TOOLS_BINARY_DIR}/llvm-config${CMAKE_EXECUTABLE_SUFFIX}")
  endif()
  execute_process(
    COMMAND ${llvm_config_command}
      --quote-paths --link-static --libfiles --system-libs
      Core OrcJIT Support native IRReader BitWriter Linker Passes Object DebugInfoDWARF
    OUTPUT_VARIABLE flags OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY)
  separate_arguments(libraries NATIVE_COMMAND "${flags}")
  execute_process(
    COMMAND ${llvm_config_command}
      --quote-paths --link-static --ldflags
    OUTPUT_VARIABLE flags OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY)
  separate_arguments(config_link_options NATIVE_COMMAND "${flags}")
endif()
add_library(mlc_llvm_probe SHARED main.cpp dependencies.cpp)
target_include_directories(mlc_llvm_probe SYSTEM PRIVATE ${LLVM_INCLUDE_DIRS})
separate_arguments(definitions NATIVE_COMMAND "${LLVM_DEFINITIONS}")
target_compile_options(mlc_llvm_probe PRIVATE ${definitions})
target_compile_features(mlc_llvm_probe PRIVATE cxx_std_17)
target_link_libraries(mlc_llvm_probe PRIVATE ${libraries})
target_link_options(mlc_llvm_probe PRIVATE ${config_link_options})
option(MLC_LLVM_WHOLE_ARCHIVE "Check every static library member with the Windows linker" OFF)
if(MLC_LLVM_WHOLE_ARCHIVE AND MSVC)
  foreach(name ${LLVM_AVAILABLE_LIBS} ZLIB::ZLIB zstd::libzstd_static)
    get_target_property(kind "${name}" TYPE)
    if(kind STREQUAL "STATIC_LIBRARY")
      target_link_options(mlc_llvm_probe PRIVATE "LINKER:/WHOLEARCHIVE:$<TARGET_FILE:${name}>")
    endif()
  endforeach()
endif()

# Static archives do not make their symbols private in a downstream DSO.
# Exercise the export controls required when another LLVM can share a process.
set_target_properties(mlc_llvm_probe PROPERTIES
  CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN ON)
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
  target_link_options(mlc_llvm_probe PRIVATE
    "LINKER:-z,defs" "LINKER:--exclude-libs,ALL"
    "LINKER:--version-script=${CMAKE_CURRENT_SOURCE_DIR}/exports.lds")
elseif(APPLE)
  target_link_options(mlc_llvm_probe PRIVATE
    "LINKER:-exported_symbols_list,${CMAKE_CURRENT_SOURCE_DIR}/exports.macos")
endif()
