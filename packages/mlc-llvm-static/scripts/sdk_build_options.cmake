# LLVM and its compression dependencies remain eligible for downstream dead
# stripping. A project hook also applies when reusing a configured build tree,
# without replacing compiler defaults or caller CFLAGS/CXXFLAGS.
include_guard(GLOBAL)
if(MSVC)
  add_compile_options("$<$<COMPILE_LANGUAGE:C,CXX>:/Gy;/Gw>")
elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
  add_compile_options("$<$<COMPILE_LANGUAGE:C,CXX>:-ffunction-sections;-fdata-sections>")
endif()
