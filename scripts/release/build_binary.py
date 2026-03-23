from __future__ import annotations

import subprocess
import sys


def main() -> None:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "mxterm",
        "--onefile",
        "--collect-data",
        "mxterm.hooks",
        "src/mxterm/cli.py",
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
