cmake_minimum_required(VERSION 3.26)
project(mlc_doxygen_bin LANGUAGES NONE)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(MLC_DOXYGEN_BIN_STAGE_DIR "${CMAKE_BINARY_DIR}/staged/mlc_doxygen_bin")
set(MLC_DOXYGEN_BIN_BUILD_ROOT "${CMAKE_BINARY_DIR}/doxygen-build")

# scripts/prepare_doxygen.py reads version.py, downloads and verifies the
# pinned Doxygen source, builds the CLI, and stages bin/, licenses/,
# doxygen.json, and the generated _version.py for installation into the wheel.
add_custom_target(stage_mlc_doxygen_bin ALL
  COMMAND
    "${CMAKE_COMMAND}" -E env
    "MLC_DOXYGEN_BIN_PACKAGE_DIR=${MLC_DOXYGEN_BIN_STAGE_DIR}"
    "MLC_DOXYGEN_BIN_BUILD_ROOT=${MLC_DOXYGEN_BIN_BUILD_ROOT}"
    "MLC_DOXYGEN_BIN_CMAKE_COMMAND=${CMAKE_COMMAND}"
    "MLC_DOXYGEN_BIN_CMAKE_GENERATOR=${CMAKE_GENERATOR}"
    "MLC_DOXYGEN_BIN_CMAKE_GENERATOR_PLATFORM=${CMAKE_GENERATOR_PLATFORM}"
    "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/prepare_doxygen.py"
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  COMMENT "Building the Doxygen executable"
  VERBATIM
)

install(DIRECTORY "${MLC_DOXYGEN_BIN_STAGE_DIR}/bin" DESTINATION mlc_doxygen_bin USE_SOURCE_PERMISSIONS)
install(DIRECTORY "${MLC_DOXYGEN_BIN_STAGE_DIR}/licenses" DESTINATION mlc_doxygen_bin)
install(FILES
  "${MLC_DOXYGEN_BIN_STAGE_DIR}/doxygen.json"
  "${MLC_DOXYGEN_BIN_STAGE_DIR}/_version.py"
  DESTINATION mlc_doxygen_bin)
