"""Remove unneeded COFF symbols with LLVM's relocation-aware object copier."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import struct
import tempfile

from prepare_llvm import sha256


def coff_contents(path: Path, *, removable: bool = False) -> list | set[bytes]:
    """Record each object's public definitions and every non-debug section."""
    result = []
    candidates, protected = set(), set()
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
            references = set()
            non_associative_comdats = set()
            debug_sections = set()
            for index in range(count):
                section = data[section_offset + index * 40:section_offset + (index + 1) * 40]
                name = section[:8].rstrip(b"\0")
                if name.startswith(b"/"):
                    name = string_at(int(name[1:]))
                characteristics = struct.unpack_from("<I", section, 36)[0]
                if characteristics & 0x1000:  # IMAGE_SCN_LNK_COMDAT.
                    non_associative_comdats.add(index + 1)
                # These tables contain symbol indexes outside normal COFF
                # relocations. Do not rewrite them without dedicated handling.
                if name.startswith((b".gfids", b".giats", b".gljmp", b".gehcont")):
                    raise RuntimeError(f"Unsupported COFF guard table {name!r}: {path}")
                relocation_offset = struct.unpack_from("<I", section, 24)[0]
                relocation_count = struct.unpack_from("<H", section, 32)[0]
                first = 0
                if relocation_count == 0xffff and struct.unpack_from("<I", section, 36)[0] & 0x01000000:
                    relocation_count = struct.unpack_from("<I", data, relocation_offset)[0]
                    first = 1
                for relocation in range(first, relocation_count):
                    references.add(struct.unpack_from("<I", data, relocation_offset + relocation * 10 + 4)[0])
                if name.startswith(b".debug"):
                    debug_sections.add(index + 1)
                    continue
                indices[index + 1] = len(sections)
                raw_size, raw_offset = struct.unpack_from("<II", section, 16)
                payload = data[raw_offset:raw_offset + raw_size] if raw_offset else b""
                characteristics = struct.unpack_from("<I", section, 36)[0]
                if characteristics & 0x80:  # IMAGE_SCN_CNT_UNINITIALIZED_DATA.
                    # BSS is logically zero-filled. objcopy may give it a file
                    # offset instead of the input's null pointer; only its size
                    # and flags describe loaded data.
                    payload = b""
                if name == b".drectve":
                    # /INCLUDE, /EXPORT and /ALTERNATENAME may refer to symbols
                    # without ordinary relocations. Keep every directive token.
                    protected.update(re.split(rb'[\s,:="\x00]+', payload))
                sections.append((name, characteristics, raw_size, hashlib.sha256(payload).digest()))
            definitions, comdats, local_labels = [], [], []
            symbols = {}
            index = 0
            while index < symbol_count:
                symbol = data[symbol_offset + index * symbol_size:symbol_offset + (index + 1) * symbol_size]
                value = struct.unpack_from("<I", symbol, 8)[0]
                number = struct.unpack_from("<i" if big else "<h", symbol, 12)[0]
                storage, auxiliaries = symbol[-2:]
                symbol_type = struct.unpack_from("<H", symbol, symbol_size - 4)[0]
                name = symbol[:8].rstrip(b"\0")
                if symbol[:4] == b"\0\0\0\0":
                    name = string_at(struct.unpack_from("<I", symbol, 4)[0])
                symbols[index] = name
                if not auxiliaries and storage == 3 and number > 0:
                    local_labels.append((number, name))
                elif not auxiliaries and storage == 2 and number == 0 and value == 0:
                    candidates.add(name)
                else:
                    # Preserve section definitions/COMDAT auxiliary records,
                    # public definitions and every other class.
                    protected.add(name)
                if storage == 105 and auxiliaries:
                    references.add(struct.unpack_from("<I", data, symbol_offset + (index + 1) * symbol_size)[0])
                if storage == 2 and (number != 0 or value != 0):
                    # Section zero with a nonzero value is a COMMON definition,
                    # not an unused declaration. Its value is the data size.
                    section_id = ("section", indices[number]) if number > 0 else ("special", number)
                    definitions.append((name, value, section_id, symbol_type))
                if storage == 3 and number < 0:
                    definitions.append((name, value, ("special", number), symbol_type))  # @feat.00.
                if storage == 3 and auxiliaries == 1 and value == 0 and symbol_type == 0 and number in indices:
                    auxiliary = bytearray(data[symbol_offset + (index + 1) * symbol_size:
                                               symbol_offset + (index + 1) * symbol_size + 18])
                    # Bigobj pads each auxiliary record to 20 bytes; ordinary
                    # COFF uses 18. The section-definition fields are the same.
                    if auxiliary[14] == 5:  # IMAGE_COMDAT_SELECT_ASSOCIATIVE.
                        non_associative_comdats.discard(number)
                        associated = struct.unpack_from("<H", auxiliary, 12)[0]
                        associated |= struct.unpack_from("<H", auxiliary, 16)[0] << 16
                        canonical = indices[associated] + 1
                        struct.pack_into("<H", auxiliary, 12, canonical & 0xffff)
                        struct.pack_into("<H", auxiliary, 16, canonical >> 16)
                    else:
                        # Number/HighNumber are meaningful only for associative
                        # COMDATs. LLVM fills in the section's own number where
                        # MSVC emits zero for other selection modes.
                        struct.pack_into("<H", auxiliary, 12, 0)
                        struct.pack_into("<H", auxiliary, 16, 0)
                    comdats.append((name, indices[number], bytes(auxiliary)))
                index += 1 + auxiliaries
            for number, name in local_labels:
                if number in non_associative_comdats or number in debug_sections:
                    # MSVC needs a COMDAT key symbol even if no relocation uses
                    # it. In PCH objects the key can have STATIC storage class.
                    protected.add(name)
                else:
                    candidates.add(name)
            protected.update(symbols[index] for index in references)
            result.append((sections, sorted(definitions), sorted(comdats)))
    if removable:
        # Names are matched across all members of the archive: a local label
        # in one object must not erase a public or referenced name in another.
        return {name for name in candidates - protected
                if name and not any(byte in b' \t\r\n\v\f#,:="' for byte in name)}
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
        # Generic --strip-unneeded removes unreferenced COMDAT section
        # definitions required by MSVC. Explicitly remove only local labels or
        # undefined declarations with no relocation, weak reference, directive,
        # or public-definition name collision anywhere in this archive.
        names = coff_contents(archive, removable=True)
        with tempfile.TemporaryDirectory(prefix="llvm-coff-symbols-") as temporary:
            symbols_file = Path(temporary) / "symbols.txt"
            symbols_file.write_bytes(b"\n".join(sorted(names)) + b"\n")
            subprocess.run([executable, f"--strip-symbols={symbols_file}", str(archive)], check=True)
        actual = coff_contents(archive)
        if actual != contents:
            for index, (expected_object, actual_object) in enumerate(zip(contents, actual)):
                if expected_object == actual_object:
                    continue
                print(f"COFF object {index}: section/definition counts {list(map(len, expected_object))} -> {list(map(len, actual_object))}", flush=True)
                for part, expected_part, actual_part in zip(("sections", "definitions", "COMDATs"), expected_object, actual_object):
                    for expected_entry, actual_entry in zip(expected_part, actual_part):
                        if expected_entry != actual_entry:
                            print(f"First changed {part}: {expected_entry!r} -> {actual_entry!r}", flush=True)
                            break
                break
            raise RuntimeError(f"COFF compaction changed public definitions or non-debug sections: {archive}")
        after += archive.stat().st_size
        metadata["files"][archive.relative_to(prefix).as_posix()] = {
            "sha256": sha256(archive), "size": archive.stat().st_size,
        }
    # The split build fingerprint includes both the transformation and the
    # resulting archive hashes, so compacted and original SDKs cannot be mixed.
    metadata["packaging"] = {"coff": "unreferenced-symbols-preserve-comdat-v1", "llvm_objcopy": version}
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"COFF archives: {before:,} -> {after:,} bytes", flush=True)
