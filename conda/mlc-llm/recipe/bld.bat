:: Build on windows
echo on

rd /s /q build
mkdir build
cd build

cmake ^
      -G "Visual Studio 17 2022" ^
      -DCMAKE_PREFIX_PATH=%LIBRARY_PREFIX% ^
      -DCMAKE_INSTALL_PREFIX:PATH=%LIBRARY_PREFIX% ^
      -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ^
      -DCMAKE_BUILD_TYPE=Release ^
      -DUSE_VULKAN=ON ^
      %SRC_DIR%

cd ..
