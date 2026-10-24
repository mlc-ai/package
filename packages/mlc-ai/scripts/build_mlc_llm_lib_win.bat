echo on

python --version
python -m pip install wheel

cd mlc-llm
if exist config.cmake del /f config.cmake

if exist build rmdir /s /q build
mkdir build

echo set(USE_VULKAN ON) >> config.cmake
echo set(CMAKE_POLICY_VERSION_MINIMUM 3.5) >> config.cmake

pip wheel --no-deps -w dist . -v

if %errorlevel% neq 0 exit %errorlevel%
cd ..
