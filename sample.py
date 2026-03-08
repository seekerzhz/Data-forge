"""快速示例：使用本地题面一键生成。"""

import subprocess

subprocess.run(
    [
        "python3",
        "forge.py",
        "workspace/example/problem.txt",
        "--provider",
        "openai",
        "--skip-run",
    ],
    check=True,
)
