cmake_minimum_required(VERSION 3.26)
project(z3_staticlib LANGUAGES NONE)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

if(NOT "$ENV{STATICLIB_Z3_ALLOW_SOURCE_BUILD}" STREQUAL "1")
  message(FATAL_ERROR
    "z3-staticlib source builds are disabled by default. Install a prebuilt "
    "wheel, or set STATICLIB_Z3_ALLOW_SOURCE_BUILD=1 to build Z3 from source "
    "explicitly.")
endif()

set(Z3_STATICLIB_PACKAGE_DIR "${CMAKE_BINARY_DIR}/z3_staticlib")
set(Z3_STATICLIB_BUILD_ROOT "${CMAKE_BINARY_DIR}/z3-build")
set(Z3_STATICLIB_TAG "$ENV{STATICLIB_Z3_TAG}")
if(Z3_STATICLIB_TAG STREQUAL "")
  set(Z3_STATICLIB_TAG "z3-4.16.0")
endif()

add_custom_target(stage_z3_staticlib ALL
  COMMAND
    "${CMAKE_COMMAND}" -E env
    "STATICLIB_Z3_TAG=${Z3_STATICLIB_TAG}"
    "STATICLIB_Z3_PACKAGE_DIR=${Z3_STATICLIB_PACKAGE_DIR}"
    "STATICLIB_Z3_BUILD_ROOT=${Z3_STATICLIB_BUILD_ROOT}"
    "STATICLIB_Z3_SOURCE_DIR=$ENV{STATICLIB_Z3_SOURCE_DIR}"
    "MACOSX_DEPLOYMENT_TARGET=$ENV{MACOSX_DEPLOYMENT_TARGET}"
    "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/z3_staticlib_builder.py"
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  COMMENT "Building static Z3 artifacts"
  VERBATIM
)

install(DIRECTORY "${Z3_STATICLIB_PACKAGE_DIR}/static" DESTINATION z3_staticlib)

