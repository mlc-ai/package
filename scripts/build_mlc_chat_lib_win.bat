echo on

cd tvm
rd /s /q build
mkdir build
cd build

cmake -A x64 -Thost=x64 ^
      -G "Visual Studio 17 2022" ^
      -DUSE_VULKAN=ON ^
      ..

cmake --build . --parallel 3 --config Release -- /m

cd ..\..
