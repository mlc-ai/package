# mlc-z3-static uv consumer example

This is a minimal downstream project that consumes `mlc-z3-static==4.16.0`
with `uv`, then links a tiny C++ program against the static Z3 CMake target
shipped in the wheel.

## Install

From this directory:

```bash
uv sync
uv run python -m mlc_z3_static_example
```

## Build The CMake Consumer

```bash
scripts/link_static.sh
```

The script resolves the installed Z3 static CMake prefix through the
configuration CLI:

```bash
uv run python -m mlc_z3_static.config --prefix
```

Then it configures CMake with that prefix so `find_package(Z3 CONFIG REQUIRED)`
finds the wheel-provided package instead of a system Z3.
