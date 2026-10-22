import hashlib
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

base = "https://github.com/mlc-ai/package/releases/download/mlc-llvm-static-v23.1.1.dev0/"
name = f"mlc_llvm_static-23.1.1.dev0-py3-none-{os.environ['SDK_TAG']}.whl"
checksums = urllib.request.urlopen(base + "SHA256SUMS").read().decode()
expected = next(line.split()[0] for line in checksums.splitlines() if line.split()[-1] == name)
path = Path(name)
urllib.request.urlretrieve(base + name, path)
assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", str(path)], check=True)
