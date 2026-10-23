"""Keep the static SDK wheel unchanged during cibuildwheel's repair phase."""
import shutil
import sys
from pathlib import Path

wheel, destination = map(Path, sys.argv[1:])
destination.mkdir(parents=True, exist_ok=True)
shutil.copy2(wheel, destination / wheel.name)
