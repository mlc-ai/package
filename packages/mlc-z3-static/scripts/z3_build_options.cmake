# Apply after Z3's project() has identified the compiler. Give downstream
# linkers function/data granularity without changing runtime or ABI settings.
if(MSVC)
  add_compile_options(/Gy /Gw /Zc:inline)
  message(STATUS "Z3 function/data COMDATs: /Gy /Gw /Zc:inline")
elseif(CMAKE_CXX_COMPILER_ID MATCHES "^(GNU|Clang)$" AND NOT APPLE)
  add_compile_options(-ffunction-sections -fdata-sections)
  message(STATUS "Z3 function/data sections: -ffunction-sections -fdata-sections")
endif()
# Mach-O already supports dead stripping individual functions and data atoms.
# Its compiler drivers do not need the ELF function/data section switches.
