echo on

cd mlc-llm
rd /s /q build
mkdir build
cd build

cmake -A x64 -Thost=x64 ^
      -G "Visual Studio 17 2022" ^
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ^
      -DUSE_VULKAN=ON ^
      ..

if %errorlevel% neq 0 exit %errorlevel%

cmake --build . --parallel 3 --config Release -- /m

if %errorlevel% neq 0 exit %errorlevel%

cd ..\..
