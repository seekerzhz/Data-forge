import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.sandbox import run_generator_in_sandbox
from core.service import ForgeService


class GeneratorExecutionTests(unittest.TestCase):
    @staticmethod
    def _write_generator(workspace: Path, code: str = "") -> None:
        source = workspace / "source"
        source.mkdir(parents=True, exist_ok=True)
        (source / "generator.py").write_text(code)

    def test_stdout_case_is_saved_when_generator_omits_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._write_generator(workspace)
            with patch(
                "core.sandbox.run_sandboxed",
                return_value=subprocess.CompletedProcess([], 0, stdout=b"3 1 4\n"),
            ):
                generated = run_generator_in_sandbox(
                    workspace, "source/generator.py", 7, output_dir="build/generated/7"
                )

            self.assertEqual(generated, workspace / "build/generated/7/7.in")
            self.assertEqual(generated.read_text(), "3 1 4\n")

    def test_legacy_testdata_case_is_recovered_into_staging_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._write_generator(workspace)

            def generate_legacy_case(*args, **kwargs) -> subprocess.CompletedProcess[bytes]:
                run_dir = args[0]
                legacy_input = run_dir / "testdata" / "3.in"
                legacy_input.parent.mkdir()
                legacy_input.write_text("legacy input\n")
                return subprocess.CompletedProcess([], 0, stdout=b"")

            with patch("core.sandbox.run_sandboxed", side_effect=generate_legacy_case):
                generated = run_generator_in_sandbox(
                    workspace, "source/generator.py", 3, output_dir="build/generated/3"
                )

            self.assertEqual(generated, workspace / "build/generated/3/3.in")
            self.assertEqual(generated.read_text(), "legacy input\n")

    def test_nonstandard_filename_is_recovered_from_isolated_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._write_generator(
                workspace,
                "from pathlib import Path\nPath('testdata').mkdir()\nPath('testdata/input.in').write_text('42\\n')\n",
            )

            generated = run_generator_in_sandbox(
                workspace, "source/generator.py", 1, output_dir="build/generated/1"
            )

            self.assertEqual(generated.read_text(), "42\n")
            self.assertFalse((workspace / "testdata/input.in").exists())

    def test_parallel_legacy_generators_cannot_overwrite_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            problem_dir = Path(directory)
            self._write_generator(
                problem_dir,
                "import argparse\n"
                "from pathlib import Path\n"
                "parser = argparse.ArgumentParser()\n"
                "parser.add_argument('--id', type=int, required=True)\n"
                "parser.add_argument('--output-dir')\n"
                "args = parser.parse_args()\n"
                "Path('testdata').mkdir()\n"
                "Path('testdata/input.in').write_text(f'{args.id}\\n')\n",
            )
            service = object.__new__(ForgeService)
            service.case_workers = 2

            service._generate_cases_parallel(problem_dir, 2, None)

            self.assertEqual((problem_dir / "testdata/1.in").read_text(), "1\n")
            self.assertEqual((problem_dir / "testdata/2.in").read_text(), "2\n")

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
