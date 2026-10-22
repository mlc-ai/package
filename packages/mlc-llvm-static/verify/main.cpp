#include <llvm/Bitcode/BitcodeWriter.h>
#include <llvm/ExecutionEngine/Orc/LLJIT.h>
#include <llvm/IR/IRBuilder.h>
#include <llvm/IR/Module.h>
#include <llvm/IRReader/IRReader.h>
#include <llvm/Linker/Linker.h>
#include <llvm/Passes/PassBuilder.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/MemoryBuffer.h>
#include <llvm/Support/SourceMgr.h>
#include <llvm/Support/TargetSelect.h>
#include <llvm/Support/raw_ostream.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif

extern "C" EXPORT int mlc_llvm_probe() {
  if (llvm::InitializeNativeTarget() || llvm::InitializeNativeTargetAsmPrinter()) return -1;
  auto jit = llvm::orc::LLJITBuilder().create();
  if (!jit) {
    llvm::consumeError(jit.takeError());
    return -2;
  }
  auto context = std::make_unique<llvm::LLVMContext>();
  llvm::SMDiagnostic diagnostic;
  auto module = llvm::parseIR(
      llvm::MemoryBufferRef("define i32 @answer() { ret i32 42 }", "probe"), diagnostic, *context);
  if (!module) return -3;
  module->setDataLayout((*jit)->getDataLayout());
  module->setTargetTriple((*jit)->getTargetTriple());
  auto empty = std::make_unique<llvm::Module>("empty", *context);
  if (llvm::Linker::linkModules(*module, std::move(empty))) return -4;
  llvm::PassBuilder passes;
  llvm::LoopAnalysisManager loops;
  llvm::FunctionAnalysisManager functions;
  llvm::CGSCCAnalysisManager cgscc;
  llvm::ModuleAnalysisManager modules;
  passes.registerModuleAnalyses(modules);
  passes.registerCGSCCAnalyses(cgscc);
  passes.registerFunctionAnalyses(functions);
  passes.registerLoopAnalyses(loops);
  passes.crossRegisterProxies(loops, functions, cgscc, modules);
  auto pipeline = passes.buildPerModuleDefaultPipeline(llvm::OptimizationLevel::O2);
  pipeline.run(*module, modules);
  llvm::SmallVector<char, 0> bitcode;
  llvm::raw_svector_ostream stream(bitcode);
  llvm::WriteBitcodeToFile(*module, stream);
  if (bitcode.empty()) return -5;
  if (auto error = (*jit)->addIRModule(
          llvm::orc::ThreadSafeModule(std::move(module), std::move(context)))) {
    llvm::consumeError(std::move(error));
    return -6;
  }
  auto symbol = (*jit)->lookup("answer");
  if (!symbol) {
    llvm::consumeError(symbol.takeError());
    return -7;
  }
  return symbol->toPtr<int (*)()>()();
}
