#include <llvm/ADT/SmallVector.h>
#include <llvm/BinaryFormat/Dwarf.h>
#include <llvm/BinaryFormat/ELF.h>
#include <llvm/DebugInfo/DWARF/DWARFContext.h>
#include <llvm/DebugInfo/DWARF/DWARFUnit.h>
#include <llvm/Object/ObjectFile.h>
#include <llvm/Support/Compression.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/MemoryBuffer.h>
#include <llvm/Support/raw_ostream.h>

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <vector>

namespace {
// Write ELF explicitly so this fixture also works on macOS and Windows and
// needs neither a cross compiler nor an installed LLVM command-line tool.
void put(std::vector<char> &bytes, size_t offset, uint64_t value, size_t size) {
  for (size_t i = 0; i < size; ++i)
    bytes[offset + i] = static_cast<char>(value >> (8 * i));
}

std::vector<char> compressedObject(llvm::compression::Format format) {
  // A DWARF v4 compile unit with a DW_AT_name string and no child DIEs.
  const uint8_t info[] = {18, 0, 0, 0, 4, 0, 0, 0, 0, 0, 8, 1,
                          's', 'd', 'k', '-', 'p', 'r', 'o', 'b', 'e', 0};
  const char abbrev[] = {1, 0x11, 0, 3, 8, 0, 0, 0};
  const char names[] = "\0.debug_info\0.debug_abbrev\0.shstrtab\0";
  llvm::SmallVector<uint8_t, 0> compressed;
  llvm::compression::compress(llvm::compression::Params(format), info, compressed);

  const size_t infoOffset = 64;
  const size_t infoSize = 24 + compressed.size(); // Elf64_Chdr + compressed data.
  const size_t abbrevOffset = infoOffset + infoSize;
  const size_t namesOffset = abbrevOffset + sizeof(abbrev);
  const size_t sectionOffset = (namesOffset + sizeof(names) + 7) & ~size_t(7);
  std::vector<char> bytes(sectionOffset + 4 * 64, 0);
  std::memcpy(bytes.data(), "\177ELF\2\1\1", 7);
  put(bytes, 16, llvm::ELF::ET_REL, 2);
  put(bytes, 18, llvm::ELF::EM_X86_64, 2);
  put(bytes, 20, 1, 4);
  put(bytes, 40, sectionOffset, 8);
  put(bytes, 52, 64, 2);
  put(bytes, 58, 64, 2);
  put(bytes, 60, 4, 2);
  put(bytes, 62, 3, 2);
  put(bytes, infoOffset, format == llvm::compression::Format::Zlib
                             ? llvm::ELF::ELFCOMPRESS_ZLIB
                             : llvm::ELF::ELFCOMPRESS_ZSTD, 4);
  put(bytes, infoOffset + 8, sizeof(info), 8);
  put(bytes, infoOffset + 16, 1, 8);
  std::memcpy(bytes.data() + infoOffset + 24, compressed.data(), compressed.size());
  std::memcpy(bytes.data() + abbrevOffset, abbrev, sizeof(abbrev));
  std::memcpy(bytes.data() + namesOffset, names, sizeof(names));
  auto section = [&](size_t index, size_t name, unsigned type, uint64_t flags,
                     size_t offset, size_t size, size_t align) {
    size_t base = sectionOffset + index * 64;
    put(bytes, base, name, 4);
    put(bytes, base + 4, type, 4);
    put(bytes, base + 8, flags, 8);
    put(bytes, base + 24, offset, 8);
    put(bytes, base + 32, size, 8);
    put(bytes, base + 48, align, 8);
  };
  section(1, 1, llvm::ELF::SHT_PROGBITS, llvm::ELF::SHF_COMPRESSED,
          infoOffset, infoSize, 8);
  section(2, 13, llvm::ELF::SHT_PROGBITS, 0, abbrevOffset, sizeof(abbrev), 1);
  section(3, 27, llvm::ELF::SHT_STRTAB, 0, namesOffset, sizeof(names), 1);
  return bytes;
}

bool checkFormat(llvm::compression::Format format) {
  if (const char *reason = llvm::compression::getReasonIfUnsupported(format)) {
    llvm::errs() << reason << '\n';
    return false;
  }
  std::vector<uint8_t> input(4096, 42);
  llvm::SmallVector<uint8_t, 0> compressed, restored;
  llvm::compression::compress(llvm::compression::Params(format), input, compressed);
  if (auto error = llvm::compression::decompress(format, compressed, restored, input.size())) {
    llvm::logAllUnhandledErrors(std::move(error), llvm::errs(), "compression: ");
    return false;
  }
  if (restored.size() != input.size() || !std::equal(input.begin(), input.end(), restored.begin())) {
    llvm::errs() << "Compression round trip changed the input\n";
    return false;
  }
  // A malformed stream must report an error, rather than silently succeeding.
  const uint8_t invalid[] = {'n', 'o', 't', ' ', 'a', ' ', 's', 't', 'r', 'e', 'a', 'm'};
  auto error = llvm::compression::decompress(format, invalid, restored, input.size());
  if (!error) {
    llvm::errs() << "Malformed compressed stream was accepted\n";
    return false;
  }
  llvm::consumeError(std::move(error));

  auto bytes = compressedObject(format);
  llvm::MemoryBufferRef buffer(llvm::StringRef(bytes.data(), bytes.size()), "compressed-debug.o");
  auto object = llvm::object::ObjectFile::createObjectFile(buffer);
  if (!object) {
    llvm::logAllUnhandledErrors(object.takeError(), llvm::errs(), "object: ");
    return false;
  }
  bool failed = false, foundCompressed = false;
  for (auto section : (*object)->sections()) foundCompressed |= section.isCompressed();
  auto handleError = [&](llvm::Error error) {
    failed = true;
    llvm::logAllUnhandledErrors(std::move(error), llvm::errs(), "DWARF: ");
  };
  auto dwarf = llvm::DWARFContext::create(
      **object, llvm::DWARFContext::ProcessDebugRelocations::Ignore,
      nullptr, "", handleError, handleError);
  if (!foundCompressed || dwarf->getNumCompileUnits() != 1) {
    llvm::errs() << "Compressed ELF did not produce one DWARF compile unit\n";
    return false;
  }
  auto &unit = *dwarf->compile_units().begin();
  auto die = unit->getUnitDIE();
  const char *name = die.getShortName();
  if (failed || die.getTag() != llvm::dwarf::DW_TAG_compile_unit ||
      !name || std::strcmp(name, "sdk-probe") != 0) {
    llvm::errs() << "Compressed DWARF compile unit has incorrect attributes\n";
    return false;
  }
  return true;
}
} // namespace

bool mlc_llvm_check_dependencies() {
  return checkFormat(llvm::compression::Format::Zlib) &&
         checkFormat(llvm::compression::Format::Zstd);
}
