from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parent
kind = sys.argv[1]
if kind == "profile":
    command = [sys.executable, root / "profile-check.py"]
elif kind == "launcher":
    ps = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    command = [ps, "-NoProfile", "-ExecutionPolicy", "RemoteSigned", "-File", root / "verify-launcher.ps1"]
else:
    raise ValueError(kind)
with (root / (kind + "-trial.log")).open("wb") as log:
    sys.exit(subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode)
