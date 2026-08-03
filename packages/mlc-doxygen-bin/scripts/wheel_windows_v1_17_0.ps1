$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

if (-not $env:MLC_DOXYGEN_BIN_ARCH) {
  $env:MLC_DOXYGEN_BIN_ARCH = "AMD64"
}
if ($env:MLC_DOXYGEN_BIN_ARCH -ne "AMD64") {
  throw "Unsupported Windows architecture: $env:MLC_DOXYGEN_BIN_ARCH"
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  throw "uv executable not found"
}
if (-not (Get-Command win_flex -ErrorAction SilentlyContinue) -and -not (Get-Command flex -ErrorAction SilentlyContinue)) {
  throw "winflexbison3 is required to build Doxygen. Install it with: choco install winflexbison3"
}
if (-not (Get-Command win_bison -ErrorAction SilentlyContinue) -and -not (Get-Command bison -ErrorAction SilentlyContinue)) {
  throw "winflexbison3 is required to build Doxygen. Install it with: choco install winflexbison3"
}

if (-not $env:CMAKE_BUILD_PARALLEL_LEVEL) {
  $env:CMAKE_BUILD_PARALLEL_LEVEL = [string]$env:NUMBER_OF_PROCESSORS
}
if (-not $env:MLC_DOXYGEN_BIN_PLAT_NAME) {
  $env:MLC_DOXYGEN_BIN_PLAT_NAME = "win_amd64"
}
if (-not $env:CIBW_BUILD) {
  $env:CIBW_BUILD = "cp311-win_amd64"
}
if (-not $env:CIBW_ARCHS_WINDOWS) {
  $env:CIBW_ARCHS_WINDOWS = "AMD64"
}
if (-not $env:CIBW_BUILD_VERBOSITY) {
  $env:CIBW_BUILD_VERBOSITY = "1"
}
if (-not $env:CIBW_ENVIRONMENT) {
  $env:CIBW_ENVIRONMENT = "MLC_DOXYGEN_BIN_PLAT_NAME='$env:MLC_DOXYGEN_BIN_PLAT_NAME' CMAKE_BUILD_PARALLEL_LEVEL='$env:CMAKE_BUILD_PARALLEL_LEVEL'"
}

uv tool run --isolated --from "cibuildwheel==3.3.1" cibuildwheel --platform windows --output-dir wheelhouse .

$Wheels = Get-ChildItem -Path wheelhouse -Filter "*-py3-none-$env:MLC_DOXYGEN_BIN_PLAT_NAME.whl"
if ($Wheels.Count -eq 0) {
  throw "No $env:MLC_DOXYGEN_BIN_PLAT_NAME wheels found in wheelhouse"
}
foreach ($Wheel in $Wheels) {
  if ($Wheel.Name -notlike "*-py3-none-*") {
    throw "Expected Python-agnostic py3-none wheel tag, got $($Wheel.Name)"
  }
}
