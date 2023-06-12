echo on

cd tvm
rd /s /q build
mkdir build
cd build

cmake -A x64 -Thost=x64 ^
      -G "Visual Studio 17 2022" ^
      -DUSE_LLVM="llvm-config --link-static" ^
      -DZLIB_USE_STATIC_LIBS=ON ^
      -DUSE_RPC=ON ^
      -DUSE_VULKAN=ON ^
      ..

cmake --build . --parallel 2 --config Release -- /m

cd ..\..
