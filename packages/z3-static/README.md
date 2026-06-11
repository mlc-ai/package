# z3-static

`z3-static` is a Python package that carries native Z3 development artifacts
for build systems. It does not provide Z3 Python bindings.

The wheel contains:

- Z3 C and C++ headers.
- A PIC static Z3 library (`libz3.a` on Unix-like platforms, `.lib` on Windows).
- Z3 CMake package files under `z3_static/static/lib/cmake/z3`.
- Z3 pkg-config metadata when upstream install provides it.

Build systems can locate the package from Python:

```python
import z3_static

print(z3_static.get_cmake_dir())
```

## Local Build

Build a wheel from an upstream Z3 tag:

```bash
STATICLIB_Z3_TAG=z3-4.16.0 \
STATICLIB_Z3_ALLOW_SOURCE_BUILD=1 \
python -m build --wheel
```

Use an existing Z3 checkout:

```bash
STATICLIB_Z3_TAG=z3-4.16.0 \
STATICLIB_Z3_SOURCE_DIR=/path/to/z3 \
STATICLIB_Z3_ALLOW_SOURCE_BUILD=1 \
python -m build --wheel
```

Source builds are opt-in to avoid accidental long Z3 builds on unsupported
platforms when pip cannot find a matching prebuilt wheel.

