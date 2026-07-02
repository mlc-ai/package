from __future__ import annotations

import mlc_z3_static


def main() -> None:
    print(f"Z3 tag: {mlc_z3_static.Z3_TAG}")
    print(f"Z3 commit: {mlc_z3_static.Z3_COMMIT}")
    print(f"Static CMake prefix: {mlc_z3_static.get_cmake_prefix_path('static')}")
    print(f"Static library: {mlc_z3_static.get_static_library_path()}")


if __name__ == "__main__":
    main()
