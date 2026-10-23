"""Remove unneeded COFF symbols with LLVM's relocation-aware object copier."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import struct

from prepare_llvm import sha256


def coff_contents(path: Path) -> list:
    """Record each object's public definitions and every non-debug section."""
    result = []
    with path.open("rb") as stream:
        if stream.read(8) != b"!<arch>\n":
            raise RuntimeError(f"Not a regular COFF archive: {path}")
        while header := stream.read(60):
            size = int(header[48:58])
            data = stream.read(size)
            if size % 2:
                stream.read(1)
            if header[:16].strip() in (b"/", b"//"):
                continue  # Archive indexes and long member-name table.
            big = data[:4] == b"\x00\x00\xff\xff"
            if big:
                count, symbol_offset, symbol_count = struct.unpack_from("<III", data, 44)
                section_offset, symbol_size = 56, 20
            else:
                count = struct.unpack_from("<H", data, 2)[0]
                symbol_offset, symbol_count = struct.unpack_from("<II", data, 8)
                section_offset = 20 + struct.unpack_from("<H", data, 16)[0]
                symbol_size = 18
            strings = data[symbol_offset + symbol_count * symbol_size:]

            def string_at(offset):
                end = strings.index(b"\0", offset)
                return strings[offset:end]

            sections = []
            indices = {}
            for index in range(count):
                section = data[section_offset + index * 40:section_offset + (index + 1) * 40]
                name = section[:8].rstrip(b"\0")
                if name.startswith(b"/"):
                    name = string_at(int(name[1:]))
                if name.startswith(b".debug"):
                    continue
                indices[index + 1] = len(sections)
                raw_size, raw_offset = struct.unpack_from("<II", section, 16)
                payload = data[raw_offset:raw_offset + raw_size] if raw_offset else b""
                characteristics = struct.unpack_from("<I", section, 36)[0]
                sections.append((name, characteristics, raw_size, hashlib.sha256(payload).digest()))
            definitions = []
            index = 0
            while index < symbol_count:
                symbol = data[symbol_offset + index * symbol_size:symbol_offset + (index + 1) * symbol_size]
                value = struct.unpack_from("<I", symbol, 8)[0]
                number = struct.unpack_from("<i" if big else "<h", symbol, 12)[0]
                storage, auxiliaries = symbol[-2:]
                if storage == 2 and number != 0:  # External definition, including absolute symbols.
                    name = symbol[:8].rstrip(b"\0")
                    if symbol[:4] == b"\0\0\0\0":
                        name = string_at(struct.unpack_from("<I", symbol, 4)[0])
                    definitions.append((name, value, indices[number] if number > 0 else number))
                index += 1 + auxiliaries
            result.append((sections, sorted(definitions)))
    return result


def compact_coff(raw: Path) -> None:
    metadata_path = raw / "staticlib.json"
    metadata = json.loads(metadata_path.read_text())
    if metadata["system"] != "Windows":
        return
    executable = os.environ.get("MLC_LLVM_STATIC_OBJCOPY") or shutil.which("llvm-objcopy")
    if not executable:
        raise RuntimeError("Windows wheel packaging requires llvm-objcopy; set MLC_LLVM_STATIC_OBJCOPY to its path")
    version = subprocess.check_output([executable, "--version"], text=True).strip()
    if "LLVM" not in version:
        raise RuntimeError("MLC_LLVM_STATIC_OBJCOPY must be LLVM's llvm-objcopy")
    print(version, flush=True)
    before = after = 0
    prefix = raw / "static"
    for archive in sorted((prefix / "lib").glob("*.lib")):
        before += archive.stat().st_size
        contents = coff_contents(archive)
        # Unlike --strip-all, this retains external definitions, symbols used
        # by relocations, and COFF COMDAT associations. Code, data, relocations,
        # and unwind sections remain available to downstream native linkers.
        subprocess.run([executable, "--strip-unneeded", str(archive)], check=True)
        if coff_contents(archive) != contents:
            raise RuntimeError(f"COFF compaction changed public definitions or non-debug sections: {archive}")
        after += archive.stat().st_size
        metadata["files"][archive.relative_to(prefix).as_posix()] = {
            "sha256": sha256(archive), "size": archive.stat().st_size,
        }
    # The split build fingerprint includes both the transformation and the
    # resulting archive hashes, so compacted and original SDKs cannot be mixed.
    metadata["packaging"] = {"coff": "strip-unneeded", "llvm_objcopy": version}
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"COFF archives: {before:,} -> {after:,} bytes", flush=True)
