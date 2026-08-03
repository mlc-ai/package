from __future__ import annotations

import subprocess
import sys

from . import get_executable_path


def main() -> int:
    cmd = [get_executable_path(), *sys.argv[1:]]
    return subprocess.run(cmd, check=False).returncode
