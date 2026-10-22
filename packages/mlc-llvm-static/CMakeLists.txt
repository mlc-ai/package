cmake_minimum_required(VERSION 3.31)
project(mlc_llvm_static LANGUAGES NONE)
find_package(Python3 REQUIRED COMPONENTS Interpreter)

if(NOT "$ENV{MLC_LLVM_STATIC_ALLOW_SOURCE_BUILD}" STREQUAL "1"
   AND "$ENV{MLC_LLVM_STATIC_PREFIX}" STREQUAL "")
  message(FATAL_ERROR
    "Install an mlc-llvm-static wheel. To build LLVM explicitly, set "
    "MLC_LLVM_STATIC_ALLOW_SOURCE_BUILD=1; to package an existing SDK produced "
    "by this project, set MLC_LLVM_STATIC_PREFIX.")
endif()

set(stage "${CMAKE_BINARY_DIR}/staged/mlc_llvm_static")
add_custom_target(stage_mlc_llvm_static ALL
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/prepare_llvm.py"
    --output "${stage}" --work-root "${CMAKE_BINARY_DIR}/llvm-build"
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  COMMENT "Preparing the LLVM static development SDK"
  VERBATIM)
install(DIRECTORY "${stage}/static" "${stage}/licenses" DESTINATION mlc_llvm_static)
install(FILES "${stage}/staticlib.json" DESTINATION mlc_llvm_static)
