"""Keep the static SDK wheel unchanged during cibuildwheel's repair phase."""
import os
import shutil
import sys
from pathlib import Path

wheel, destination = map(Path, sys.argv[1:])
destination.mkdir(parents=True, exist_ok=True)
shutil.copy2(wheel, destination / wheel.name)
if os.environ.get("MLC_LLVM_STATIC_USE_CACHE") == "1":
    # Keep the compiled payload even when a later verification step fails.
    cache = Path(__file__).resolve().parents[1] / ".sdk-cache"
    cache.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wheel, cache / wheel.name)
