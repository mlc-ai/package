# LLVM static SDK dependency audit

The LLVM 23.1.1 SDK includes PIC static zlib and zstd in its base package and
keeps the other optional integrations disabled. libxml2 is unnecessary for the
IR, optimization, code generation, object, debug-info, and ORC paths used by the
current consumers. Its absence does remove Windows manifest merging. Adding all
standard code-generation backends does not require enabling libxml2 or adding
vendor host libraries.

This audit covers the recipe introduced in [package PR 115](https://github.com/mlc-ai/package/pull/115),
LLVM tag `llvmorg-23.1.1`, TVM-FFI `29c01dc89bf65e41b5647dc301718284cd594ede`,
TIRx `3dbcef3ca477db7f10b930f32d24bc038f5571bf`, and TVM
`18ec45ed7729b70ae94c340014624b34b6ecf5a7`. Static LLVM and compression libraries
still depend on the host operating system and C++ runtime.

## Dependency matrix

"Required by profile" means required with the features this SDK deliberately
enables; LLVM can be built without either compression library. The ORC addon
also explicitly requires both static archives in its current build script.

| Dependency | LLVM owner and feature | Effect on these consumers | SDK policy |
| --- | --- | --- | --- |
| zlib 1.3.1 | `LLVMSupport`; compression used by Object/DWARF and other file readers/writers | Required by profile and the ORC addon. Disabling it prevents processing zlib-compressed sections. Ordinary uncompressed IR/code generation does not inherently require it. | Bundle PIC static archive, headers, notice. |
| zstd 1.5.7 | `LLVMSupport`; Zstandard compression, including ELF debug sections | Required by profile and the ORC addon. Disabling it removes Zstandard processing. | Bundle PIC static archive, headers, CMake exports, notice; keep multithreaded zstd disabled. |
| libxml2 | `LLVMWindowsManifest`; Windows manifest merging | Optional. `windows_manifest::isAvailable()` becomes false; merging returns an error. No requirement in the selected Core/ORC/native or TIRx code-generation paths. `llvm-mt` and LLD's manifest use are outside this SDK. | Keep off; do not add an otherwise unused static XML dependency. |
| libedit and its possible curses/terminfo dependencies | `LLVMLineEditor`; interactive editing, completion, history | Optional library feature, mainly useful to interactive tools. The fallback still reads lines. These consumers do not use interactive LLVM tools. | Keep off; no libedit, ncurses, or libtinfo bundle. |
| libffi | `LLVMInterpreter`; calls to arbitrary external functions from interpreted IR | Optional. Without it the interpreter can still use its known wrappers, but cannot perform general libffi calls. ORC executes native machine code and does not use this path. Apache TVM-FFI is a separate project from libffi. | Keep off. |
| Z3 | `LLVMSupport`'s SMT interface; also used by Clang analysis outside this SDK | Optional. LLVM's Z3 solver factory is unavailable. TIRx's separately configurable Z3 integration is independent of `LLVM_ENABLE_Z3_SOLVER`. | Keep LLVM Z3 off. A consumer enabling its own Z3 feature supplies its own dependency. |
| libcurl | `LLVMHTTP` client, used by `LLVMDebuginfod` | Optional network debug-file fetching. Local Object/DWARF reading works without it. Windows has a separate WinHTTP client even with CURL off. | Keep off; avoid its TLS, HTTP, and compression dependency closure. |
| cpp-httplib | `LLVMHTTP` server | Optional HTTP/debuginfod serving. No requirement in these JIT/code-generation paths. | Keep off. |
| libpfm | `LLVMExegesis` under `tools/llvm-exegesis`; performance-counter measurements | Only needed for that excluded tool's counter support. It is not a code-generation backend requirement. | Keep off. |
| DIA SDK | DIA implementation in `LLVMDebugInfoPDB` | Optional Windows COM/DIA integration. LLVM's native PDB, CodeView, and MSF implementations remain available. No DIA runtime is needed by ORC/native code generation. | Keep off. |
| ICU and iconv | `LLVMSupport` text-encoding converter | Optional extended charset conversion. Built-in UTF-8/IBM-1047 conversion remains; other conversions can fail. Disabling these does not remove the SystemZ backend. | Keep both off. Upstream restricts ICU discovery to dynamic libraries and iconv discovery to a built-in implementation. |
| OCaml bindings and build/test/documentation packages | Bindings, Python utilities, tests, documentation, generators | Build-time or excluded outputs. They are not downstream static-link requirements. Python locates the wheel; the SDK payload has no Python ABI dependency. | Keep bindings/tests/docs off; retain only the selected distribution outputs. |
| BLAKE3, xxHash, SipHash and other code carried in LLVM sources | Built into LLVM libraries from the pinned source distribution | No separately discovered host library is required for these implementations. | Keep the matching LLVM source/version and notices. |

The compression relationship is established by
[Support's link interface](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/Support/CMakeLists.txt),
the [compression implementation](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/Support/Compression.cpp),
and [ELF decompression](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/Object/Decompressor.cpp).
The narrower optional features follow their implementations:
[manifest merger](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/WindowsManifest/WindowsManifestMerger.cpp),
[line editor](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/LineEditor/LineEditor.cpp),
[interpreter external calls](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/ExecutionEngine/Interpreter/ExternalFunctions.cpp),
[Z3 solver](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/Support/Z3Solver.cpp),
[HTTP client](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/HTTP/HTTPClient.cpp),
[HTTP server](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/HTTP/HTTPServer.cpp),
[exegesis](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/tools/llvm-exegesis/lib/CMakeLists.txt),
[PDB](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/DebugInfo/PDB/CMakeLists.txt),
and [text encoding](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/Support/TextEncoding.cpp).

## Downstream requirements

| Consumer | LLVM discovery and link behavior | Consequence |
| --- | --- | --- |
| Apache TVM-FFI core | The core FFI library and the ORC addon are separate builds. | Installing or linking the core does not itself require this LLVM SDK. |
| TVM-FFI ORC addon | Uses CMake discovery, `llvm-config --link-static --libs Core OrcJIT Support native`, `--ldflags`, and explicit static zlib/zstd discovery. It filters compression/XML entries from the remaining system flags. | The SDK must supply both compression archives and correct native/ORC component ordering. Enabling XML would require a separate audit of any component path that reaches manifest merging. Linux also needs the matching host ORC runtime for the addon's platform lifecycle. |
| Apache TIRx | LLVM is optional. The CMake route maps `all`; the command route requests `--libfiles`, `--system-libs`, include/version/prefix/CMake/target information. It recognizes compression flags and runs package discovery. | Supply an internally consistent profile and all transitive static dependencies. Continue passing `CMAKE_PREFIX_PATH` and `ZLIB_USE_STATIC_LIBS=ON`; `--link-static` alone cannot control a separate `find_package(ZLIB)` call. |
| Apache TVM at the audited revision | Uses an installed TIRx package or the TIRx source submodule, and links its compiler target. | Its LLVM requirements are inherited through the selected TIRx build. Older TVM revisions with their own LLVM discovery require revision-specific checks. |
| mlc-ai/package's existing TVM wheel scripts | Select static LLVM, have optional backend/vendor configurations, and currently install distribution `libxml2-devel` for the distribution LLVM. | That installation does not make XML mandatory for this SDK. Changing those wheel scripts or replacing the vendor toolchain is a separate migration. |

Sources:
[ORC addon build](https://github.com/apache/tvm-ffi/blob/29c01dc89bf65e41b5647dc301718284cd594ede/addons/tvm_ffi_orcjit/CMakeLists.txt),
[TIRx discovery](https://github.com/apache/tvm-tirx/blob/3dbcef3ca477db7f10b930f32d24bc038f5571bf/cmake/utils/FindLLVM.cmake),
[TIRx LLVM sources](https://github.com/apache/tvm-tirx/blob/3dbcef3ca477db7f10b930f32d24bc038f5571bf/cmake/modules/LLVM.cmake),
[TVM composition](https://github.com/apache/tvm/blob/18ec45ed7729b70ae94c340014624b34b6ecf5a7/CMakeLists.txt),
and the [package wheel scripts](https://github.com/mlc-ai/package/blob/f7596e54d810fae7627c256b10843ef8430621bb/scripts/build_mlc_ai_wheel_manylinux.sh).

## Static link closure and platform libraries

For the selected profile, the common dependency path is:

```text
consumer -> Core / Passes / native / OrcJIT / Object / DebugInfoDWARF
         -> ... -> LLVMSupport -> ZLIB::ZLIB + zstd::libzstd_static
                             -> LLVMDemangle + host system libraries
```

The inspected Linux aarch64 SDK exports the following Support interface:

```cmake
INTERFACE_LINK_LIBRARIES
  "rt;dl;-lpthread;m;ZLIB::ZLIB;zstd::libzstd_static;LLVMDemangle"
```

Its `llvm-config --link-static --system-libs` reports
`-lrt -ldl -lpthread -lm -lz -lzstd`. The C++ driver supplies the C++ runtime and
compiler support libraries separately. These flags describe the host running
LLVM, including when LLVM generates code for another architecture.

| Host | Expected remaining platform requirements |
| --- | --- |
| Linux x86_64/aarch64 | glibc, the selected C++ runtime/compiler support, and configure-detected `rt`, `dl`, pthread, math. `libatomic` is conditional on the host compiler/architecture; preserve its discovered flags if present. Backtrace/execinfo dependencies are conditional on other host platforms. Do not bundle a second glibc. |
| macOS arm64 | Apple SDK/system libraries, libc++, libSystem, and any flags reported by the actual build. Static LLVM/zlib/zstd does not imply static libc++ or libSystem. The SDK's deployment floor remains macOS 14.0. No vendor framework is required merely to include extra backends. |
| Windows AMD64/ARM64 | Support links `psapi`, `shell32`, `ole32`, `uuid`, `advapi32`, `ws2_32`, `ntdll`. Its CMake interface also carries `delayimp` and delay-load options. Windows `LLVMHTTP` additionally links `winhttp` and `crypt32`, even with CURL off. The archives use `/MD`; downstream code must use a compatible release CRT for its architecture and provide the VC/UCRT runtime environment. |

The table combines the inspected Linux export with upstream
[platform detection](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/cmake/config-ix.cmake),
[atomic checks](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/cmake/modules/CheckAtomic.cmake),
[Support](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/Support/CMakeLists.txt),
and [HTTP](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/HTTP/CMakeLists.txt).
Capture each platform's actual exported interface when producing metadata;
do not infer flags from the target triple.

For archive-based command-line linking, put objects first, then LLVM archives
in dependency order, then compression archives and platform libraries. Use
`llvm-config`'s ordered closure or CMake imported targets. Alphabetical archive
lists are unsuitable for ordinary one-pass ELF linking; explicit groups or
whole-archive operations have different semantics. Do not apply whole-archive
to normal consumers merely to work around ordering.

`--link-static` chooses LLVM's static mode. On Unix, a later `-lz` can still
select a shared library if the bundled archive is not found first. Use resolved
SDK archive paths when constructing a link line under SDK control. CMake's
`ZLIB::ZLIB` is an `UNKNOWN IMPORTED` target in common FindZLIB implementations,
so inspect its location rather than assuming the target name proves staticness.

The current CMake exports call `find_package(ZLIB)` and `find_package(zstd)`.
They are relocatable with the documented prefix/static-discovery settings, but
can reuse pre-existing targets or find unrelated system packages. The next
configuration implementation should bind SDK-owned archive paths relative to
its prefix and fail clearly on conflicting dependency targets. This is a
configuration recommendation, not a change to the recipe in this audit.
See [LLVMConfig](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/cmake/modules/LLVMConfig.cmake.in).

If manifest support is later requested, pin and build static libxml2, select
`LLVM_USE_STATIC_LIBXML2=ON`, and capture the XML build's entire dependency
closure. It may include compression, charset, thread, and platform libraries,
depending on that libxml2 version and configuration. LLVM's
[static XML discovery](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/cmake/modules/FindLibXml2.cmake)
uses pkg-config's static dependency list; a standalone archive is insufficient
evidence that those requirements are satisfied. Validate manifest merging and
its failure cases before adding this feature.

## Extra backends and target runtimes

LLVM 23.1.1's standard set is AArch64, AMDGPU, ARM, AVR, BPF, Hexagon, Lanai,
LoongArch, Mips, MSP430, NVPTX, PowerPC, RISCV, Sparc, SPIRV, SystemZ, VE,
WebAssembly, X86, and XCore. ARC, CSKY, DirectX, M68k, and Xtensa are separately
listed as experimental. The standard backend CMake files in the pinned source
have no extra `find_package`, `find_library`, or external `LINK_LIBS` additions.
Their LLVM component dependencies still need inclusion in the selected profile.
See [the upstream target lists](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/CMakeLists.txt)
and [backend build trees](https://github.com/llvm/llvm-project/tree/llvmorg-23.1.1/llvm/lib/Target).

These libraries contain host code that emits target code. They do not provide
target libc/libm/C++ libraries, compiler builtins, unwinders, sanitizer
runtimes, startup objects, linkers, OS headers, device libraries, or sysroots.
For example, emitting AMDGPU or NVPTX code does not require installing those
vendor runtimes into this SDK; applications using such targets may need vendor
tools and device libraries separately. Cross-compilation and cross-target JIT
execution are different capabilities.

The native base owns zlib, zstd, their headers/notices, generic LLVM libraries,
and the Linux host ORC runtime. The exact-version extra-targets add-on owns only
additional target archives and its distinct profile metadata/headers/CMake
files. Installing it preserves the base's compression libraries and host runtime.
Both profiles use the same dependency feature policy and build fingerprint.
Remote CI initializes every selected backend and emits representative
cross-target objects on every supported host.

## Metadata needed by a configuration frontend

A Python compatibility frontend needs build-generated data, not a handwritten
list of `-l` flags:

1. Per-profile component names, pseudo-component/target expansion, installed
   archive paths relative to the prefix, and ordered transitive LLVM closures.
   Record non-component exports such as `LLVMHTTP` and `LLVMDebuginfod`
   separately; the current SDK ships them, but `llvm-config --components` and
   `--libfiles all` do not include them.
2. Per-library external requirements, including imported dependency targets,
   resolved bundled archives, platform library names, grouped linker options,
   frameworks if any, and the distinction between link libraries and options.
   Preserve generator-expression/platform conditions after evaluating the
   supported build configuration.
3. The conservative upstream `--system-libs` output as structured tokens, plus
   the richer per-component closure for new interfaces. Upstream constructs
   that output from **Support and WindowsManifest only**, and prints the same
   union regardless of requested components. It omits requirements from other
   archives, including Windows HTTP and interpreter/libedit integrations if
   enabled. An exact compatibility mode should preserve the documented
   behavior; an improved closure must be explicit and tested.
4. Compression and optional-feature flags, compiler/CRT/C++ ABI information,
   deployment/ABI floor, RTTI/EH/assertions/PIC/LTO settings, default and host
   triples, available targets, LLVM/package version, and an exact profile
   fingerprint. `/MD` and compiler default libraries are not fully described
   by `--system-libs`.
5. Path relocation and output-format rules for `--libfiles`, `--libs`,
   `--ldflags`, includes, and system libraries, including quoting and spaces
   on Windows. Store SDK paths relative to the installed prefix. Do not store
   build-machine paths or rely on a string replacement limited to one library.

The upstream behavior is visible in
[llvm-config generation](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/tools/llvm-config/CMakeLists.txt)
and [option processing](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/tools/llvm-config/llvm-config.cpp).

## Downstream visibility and validation

Static linking removes a shared-library dependency only for archive members
actually incorporated into the consumer. It does not automatically hide their
symbols. A downstream DSO should export its own API and keep LLVM/zlib/zstd
private to avoid interposition with another LLVM in the same process. On ELF,
use an export/version script plus `--exclude-libs,ALL`; on macOS use an exported
symbols list; on Windows use explicit DLL exports. Setting hidden visibility
only while compiling the consumer cannot change previously compiled archives.
Windows ORC consumers can additionally export `__jit_debug_descriptor` and
`__jit_debug_register_code`: LLVM marks these GDB JIT hooks with
`LLVM_ALWAYS_EXPORT`, embedding export directives in archive members. Treat
them as explicit debugger ABI exceptions. Full suppression would require a
separately validated LLVM/source or object transformation; a consumer's export
list alone does not remove them. See
[JITLoaderGDB](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.1/llvm/lib/ExecutionEngine/Orc/TargetProcess/JITLoaderGDB.cpp).
The [ORC addon](https://github.com/apache/tvm-ffi/blob/29c01dc89bf65e41b5647dc301718284cd594ede/addons/tvm_ffi_orcjit/CMakeLists.txt)
already applies export controls on ELF and macOS.

The verification probe runs through both imported CMake targets and raw
`llvm-config` flags. It exercises zlib and zstd compression/decompression,
malformed-stream errors, and real ELF `SHF_COMPRESSED` sections containing a
DWARF compilation unit. LLVM Object and DWARF must recover the expected DIE
name for both codecs on every host, without external LLVM tools. It also
restricts and inspects exported symbols with the named Windows debugger
exceptions, rejects dynamic disabled optional
dependencies, and checks every available imported archive's location after
relocation. The existing IR/optimization/bitcode/JIT and Linux ABI checks
continue to run.

Retain these validation requirements as the SDK changes:

- Keep both discovery routes working when introducing the configuration
  frontend. Extend coverage to additional representative roots and `all`,
  including non-component exports through CMake.
- Test with a competing system zlib/zstd installation and with dependency
  targets already defined. Require an SDK path or a clear collision error.
- Link all installed archives with strict unresolved-symbol checks in a
  dedicated coverage probe. Inspect the resulting dependencies, exported
  symbols, and ABI versions. Keep this separate from normal consumer linking.
- For All, emit and inspect representative cross-target objects/assembly,
  including compressed debug information where supported. Do not execute
  foreign machine code or claim a target sysroot is included.
- Re-run the FFI ORC addon and TIRx through their actual discovery routes,
  checking host ORC-runtime initialization/finalization, C/C++ symbol imports,
  compressed external objects, dependency visibility, and same-process loading
  alongside another LLVM-bearing extension. Keep native-profile test exclusions
  explicit.

The published experimental wheels' earlier four-platform and downstream checks
are recorded in [PR 115](https://github.com/mlc-ai/package/pull/115).

The [experimental dev3 release](https://github.com/mlc-ai/package/releases/tag/mlc-llvm-static-v23.1.1.dev3)
records four-platform Native/All validation, both discovery routes, add-on
removal, relocation, static dependency and export checks, cross-target objects,
and downstream FFI/TIRx results. Target availability is checked against LLVM's
configured backend list rather than a fixed set of architectures or a count.
