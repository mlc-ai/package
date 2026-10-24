# Apply after Z3's project() has identified the compiler. Keep the compiler's
# default flags and runtime/ABI settings while omitting unused inline COMDATs.
if(MSVC)
  add_compile_options(/Zc:inline)
  message(STATUS "Z3 MSVC inline COMDAT elimination: /Zc:inline")
endif()
