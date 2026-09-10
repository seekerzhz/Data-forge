import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from core.service import ForgeArtifactError, ForgeService
from webui.task_queue import TaskQueue


class _Generator:
    def build(self, *args):
        return "# DATAFORGE_CANNOT_GENERATE: 输入格式缺失\n"


class _Solution:
    def build(self, *args):
        return "int main() {}\n"


class FailureArtifactTests(unittest.TestCase):
    def test_unusable_statement_creates_zip_with_llm_outputs_and_reason(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = object.__new__(ForgeService)
            service.generator_builder = _Generator()
            service.solution_builder = _Solution()
            service.case_workers = 1
            with patch.object(service, "polish_statement", side_effect=lambda value: value):
                with self.assertRaises(ForgeArtifactError) as caught:
                    service.run_with_statement("P1", "# 测试\n", Path(directory), num_cases=1)

            self.assertIn("输入格式缺失", str(caught.exception))
            with zipfile.ZipFile(caught.exception.artifact_path) as archive:
                self.assertEqual(
                    set(archive.namelist()), {"failure.txt", "generator.py", "problem_zh.md", "solution.cpp"}
                )
                self.assertIn("输入格式缺失", archive.read("failure.txt").decode())
                self.assertIn("DATAFORGE_CANNOT_GENERATE", archive.read("generator.py").decode())

    def test_queue_stages_failure_artifact_for_download(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "report.zip"
            artifact.write_bytes(b"placeholder")

            class FailedService:
                def run_with_statement(self, *args, **kwargs):
                    raise ForgeArtifactError("bad generated output", artifact)

            queue = TaskQueue(
                workspace_root=root / "tasks", download_root=root / "downloads", workers=1, service_factory=FailedService
            )
            task_id = queue.submit("", "# test", 1)
            for _ in range(100):
                task = queue.get(task_id, include_internal=True)
                if task and task["status"] == "failed":
                    break
                import time
                time.sleep(0.01)
            self.assertEqual(task["status"], "failed")
            self.assertTrue(task["artifact_available"])
            self.assertTrue(Path(task["zip_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
