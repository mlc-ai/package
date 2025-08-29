echo on

python --version
python -m pip install wheel

cd tvm
if exist config.cmake del /f config.cmake

if exist build rmdir /s /q build
mkdir build

echo set(USE_LLVM "llvm-config --link-static") >> config.cmake
echo set(ZLIB_USE_STATIC_LIBS ON) >> config.cmake
echo set(USE_RPC ON) >> config.cmake
echo set(USE_VULKAN ON) >> config.cmake

pip wheel --no-deps -w dist . -v

if %errorlevel% neq 0 exit %errorlevel%
cd ..
