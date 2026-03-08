"""Quick example: generate files from local problem statement."""

import subprocess

subprocess.run(
    [
        "python3",
        "forge.py",
        "workspace/example/problem.txt",
        "--provider",
        "ark",
        "--num-cases",
        "50",
        "--skip-run",
    ],
    check=True,
)
