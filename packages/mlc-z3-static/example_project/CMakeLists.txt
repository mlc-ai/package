cmake_minimum_required(VERSION 3.20)
project(mlc_z3_static_uv_example LANGUAGES C CXX)

find_package(Z3 CONFIG REQUIRED)

if(DEFINED MLC_Z3_STATIC_EXPECTED_PREFIX)
  get_target_property(Z3_IMPORTED_LOCATION z3::libz3 IMPORTED_LOCATION_RELEASE)
  if(NOT Z3_IMPORTED_LOCATION)
    get_target_property(Z3_IMPORTED_LOCATION z3::libz3 IMPORTED_LOCATION)
  endif()
  if(NOT Z3_IMPORTED_LOCATION)
    message(FATAL_ERROR "z3::libz3 does not expose an imported library location")
  endif()

  file(REAL_PATH "${Z3_IMPORTED_LOCATION}" Z3_IMPORTED_LOCATION_REAL)
  file(REAL_PATH "${MLC_Z3_STATIC_EXPECTED_PREFIX}" MLC_Z3_STATIC_EXPECTED_PREFIX_REAL)
  string(FIND "${Z3_IMPORTED_LOCATION_REAL}" "${MLC_Z3_STATIC_EXPECTED_PREFIX_REAL}/" Z3_PREFIX_POSITION)
  if(NOT Z3_PREFIX_POSITION EQUAL 0)
    message(
      FATAL_ERROR
      "z3::libz3 resolves outside the installed mlc-z3-static wheel prefix.\n"
      "  imported: ${Z3_IMPORTED_LOCATION_REAL}\n"
      "  expected prefix: ${MLC_Z3_STATIC_EXPECTED_PREFIX_REAL}"
    )
  endif()
endif()

add_executable(mlc_z3_static_uv_example cpp/main.cpp)
target_link_libraries(mlc_z3_static_uv_example PRIVATE z3::libz3)
target_compile_features(mlc_z3_static_uv_example PRIVATE cxx_std_20)
