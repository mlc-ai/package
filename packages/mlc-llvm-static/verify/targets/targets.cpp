#include <llvm/ADT/SmallVector.h>
#include <llvm/Config/Targets.h>
#include <llvm/IR/LegacyPassManager.h>
#include <llvm/IR/Module.h>
#include <llvm/IRReader/IRReader.h>
#include <llvm/MC/TargetRegistry.h>
#include <llvm/Object/ObjectFile.h>
#include <llvm/Support/CodeGen.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/MemoryBuffer.h>
#include <llvm/Support/SourceMgr.h>
#include <llvm/Support/TargetSelect.h>
#include <llvm/Support/raw_ostream.h>
#include <llvm/Target/TargetMachine.h>
#include <llvm/Target/TargetOptions.h>

#if defined(MLC_LLVM_EXPECT_ALL_PROFILE)
#if !LLVM_HAS_X86_TARGET || !LLVM_HAS_AARCH64_TARGET || !LLVM_HAS_RISCV_TARGET
#error All-profile target-availability headers are inconsistent
#endif
#elif defined(MLC_LLVM_EXPECT_NATIVE_X86)
#if !LLVM_HAS_X86_TARGET || LLVM_HAS_AARCH64_TARGET || LLVM_HAS_RISCV_TARGET
#error Native X86 target-availability headers are inconsistent
#endif
#elif defined(MLC_LLVM_EXPECT_NATIVE_AArch64)
#if LLVM_HAS_X86_TARGET || !LLVM_HAS_AARCH64_TARGET || LLVM_HAS_RISCV_TARGET
#error Native AArch64 target-availability headers are inconsistent
#endif
#endif

int main(int argc, char** argv) {
  // These expand the selected generated headers. A profile/library mismatch
  // must fail the link, even when the host JIT itself would have worked.
  llvm::InitializeAllTargetInfos();
  llvm::InitializeAllTargets();
  llvm::InitializeAllTargetMCs();
  llvm::InitializeAllAsmPrinters();
  llvm::InitializeAllAsmParsers();
  llvm::InitializeAllDisassemblers();
  for (int i = 1; i < argc; ++i) {
    llvm::Triple triple(argv[i]);
    std::string error;
    auto* target = llvm::TargetRegistry::lookupTarget(triple, error);
    if (!target) { llvm::errs() << error << '\n'; return 1; }
    llvm::TargetOptions options;
    std::unique_ptr<llvm::TargetMachine> machine(
        target->createTargetMachine(triple, "", "", options, llvm::Reloc::PIC_));
    if (!machine) return 2;
    llvm::LLVMContext context;
    llvm::SMDiagnostic diagnostic;
    auto module = llvm::parseIR(llvm::MemoryBufferRef(
        "define i32 @answer() { ret i32 42 }", "cross-target-probe"), diagnostic, context);
    if (!module) return 3;
    module->setTargetTriple(triple);
    module->setDataLayout(machine->createDataLayout());
    llvm::SmallVector<char, 0> bytes;
    llvm::raw_svector_ostream output(bytes);
    llvm::legacy::PassManager passes;
    if (machine->addPassesToEmitFile(passes, output, nullptr, llvm::CodeGenFileType::ObjectFile)) return 4;
    passes.run(*module);
    auto object = llvm::object::ObjectFile::createObjectFile(
        llvm::MemoryBufferRef(llvm::StringRef(bytes.data(), bytes.size()), "cross-object"));
    if (!object) { llvm::logAllUnhandledErrors(object.takeError(), llvm::errs()); return 5; }
    if ((*object)->getArch() != triple.getArch()) return 6;
    if (triple.isOSBinFormatELF() && !(*object)->isELF()) return 8;
    if (triple.isOSBinFormatCOFF() && !(*object)->isCOFF()) return 9;
    if (triple.isOSBinFormatMachO() && !(*object)->isMachO()) return 10;
    if (triple.isOSBinFormatWasm() && !(*object)->isWasm()) return 11;
    llvm::outs() << "Verified object generation: " << triple.str() << '\n';
  }
  return argc > 1 ? 0 : 7;
}
