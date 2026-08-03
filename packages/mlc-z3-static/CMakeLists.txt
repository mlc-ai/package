cmake_minimum_required(VERSION 3.26)
project(mlc_z3_static LANGUAGES NONE)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

if(NOT "$ENV{MLC_Z3_STATIC_ALLOW_SOURCE_BUILD}" STREQUAL "1")
  message(FATAL_ERROR
    "mlc-z3-static source builds are disabled by default. Install a prebuilt "
    "wheel, or set MLC_Z3_STATIC_ALLOW_SOURCE_BUILD=1 to build Z3 from source "
    "explicitly.")
endif()

set(MLC_Z3_STATIC_STAGE_DIR "${CMAKE_BINARY_DIR}/staged/mlc_z3_static")
set(MLC_Z3_STATIC_BUILD_ROOT "${CMAKE_BINARY_DIR}/z3-build")

add_custom_target(stage_mlc_z3_static ALL
  COMMAND
    "${CMAKE_COMMAND}" -E env
    "MLC_Z3_STATIC_PACKAGE_DIR=${MLC_Z3_STATIC_STAGE_DIR}"
    "MLC_Z3_STATIC_BUILD_ROOT=${MLC_Z3_STATIC_BUILD_ROOT}"
    "MLC_Z3_STATIC_CMAKE_GENERATOR=${CMAKE_GENERATOR}"
    "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/prepare_z3_v4_16_0.py"
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  COMMENT "Building Z3 static and shared artifacts"
  VERBATIM
)

install(DIRECTORY "${MLC_Z3_STATIC_STAGE_DIR}/static" DESTINATION mlc_z3_static)
install(DIRECTORY "${MLC_Z3_STATIC_STAGE_DIR}/shared" DESTINATION mlc_z3_static)
install(DIRECTORY "${MLC_Z3_STATIC_STAGE_DIR}/licenses" DESTINATION mlc_z3_static)
install(FILES "${MLC_Z3_STATIC_STAGE_DIR}/staticlib.json" DESTINATION mlc_z3_static)
