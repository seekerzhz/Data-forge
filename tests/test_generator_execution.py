import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.sandbox import run_generator_in_sandbox
from core.service import ForgeService


class GeneratorExecutionTests(unittest.TestCase):
    def test_stdout_case_is_saved_when_generator_omits_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            with patch(
                "core.sandbox.run_sandboxed",
                return_value=subprocess.CompletedProcess([], 0, stdout=b"3 1 4\n"),
            ):
                generated = run_generator_in_sandbox(
                    workspace, "source/generator.py", 7, output_dir="build/generated/7"
                )

            self.assertEqual(generated, workspace / "build/generated/7/7.in")
            self.assertEqual(generated.read_text(), "3 1 4\n")

    def test_parallel_generation_uses_isolated_staging_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            problem_dir = Path(directory)
            calls: list[tuple[int, str]] = []

            def generate(workspace: Path, script_name: str, case_id: int, **kwargs) -> Path:
                output_dir = kwargs["output_dir"]
                calls.append((case_id, output_dir))
                output = workspace / output_dir / f"{case_id}.in"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(f"{case_id}\n")
                return output

            service = object.__new__(ForgeService)
            service.case_workers = 2
            with patch("core.service.run_generator_in_sandbox", side_effect=generate):
                service._generate_cases_parallel(problem_dir, 2, None)

            self.assertEqual(sorted(calls), [(1, "build/generated/1"), (2, "build/generated/2")])
            self.assertEqual((problem_dir / "testdata/1.in").read_text(), "1\n")
            self.assertEqual((problem_dir / "testdata/2.in").read_text(), "2\n")


if __name__ == "__main__":
    unittest.main()
