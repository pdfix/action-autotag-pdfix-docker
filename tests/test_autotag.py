import contextlib
import io
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, Path(__file__).resolve().parent.parent.joinpath("src").as_posix())

import main  # noqa: E402
from autotag import Autotag  # noqa: E402
from constants import LATEST_SDK_VERSION  # noqa: E402
from exceptions import (  # noqa: E402
    EC_ARG_GENERAL,
    EC_ARG_TEMPLATE_FILE_NOT_EXISTS,
    EC_PDFIX_ERROR,
    EC_TEMPLATE_JSON_INVALID,
    MESSAGE_PDFIX_ERROR,
    ExpectedException,
)

# Real pdfix_app 8.7.1 output for a file that is not a PDF
SDK_OPEN_ERROR_STDOUT: str = "Error: 31, open_doc_from_stream, 423\n\nError:31 Failed to open the document.\n"


def finished_process(returncode: int, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


class TestAutotaggingPdf(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.directory: Path = Path(temporary_directory.name)
        self.input_path: Path = self.directory.joinpath("input.pdf")
        self.input_path.write_bytes(b"%PDF-1.7")
        self.output_path: Path = self.directory.joinpath("output.pdf")
        self.template_path: Path = self.directory.joinpath("template.json")

    def autotag(self) -> None:
        main.autotagging_pdf(
            "", "", self.input_path.as_posix(), self.output_path.as_posix(), self.template_path.as_posix()
        )

    def assert_error_code(self, error_code: int) -> ExpectedException:
        with self.assertRaises(ExpectedException) as context:
            self.autotag()
        self.assertEqual(context.exception.error_code, error_code)
        return context.exception

    @mock.patch("main.Autotag")
    def test_missing_template_file_is_reported(self, autotag_class: mock.MagicMock) -> None:
        exception: ExpectedException = self.assert_error_code(EC_ARG_TEMPLATE_FILE_NOT_EXISTS)
        self.assertIn(self.template_path.resolve().as_posix(), exception.message)
        autotag_class.assert_not_called()

    @mock.patch("main.Autotag")
    def test_existing_template_file_runs_autotag(self, autotag_class: mock.MagicMock) -> None:
        self.template_path.write_text("{}", encoding="utf-8")
        self.autotag()
        autotag_class.return_value.run.assert_called_once()


class TestArguments(unittest.TestCase):
    def test_tag_without_template_is_argument_error(self) -> None:
        argv: list[str] = ["main.py", "tag", "-i", "input.pdf", "-o", "output.pdf"]
        with mock.patch.object(sys, "argv", argv), mock.patch("sys.stderr"):
            with self.assertRaises(SystemExit) as context:
                main.main()
        self.assertEqual(context.exception.code, EC_ARG_GENERAL)


class TestAutotagRun(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.directory: Path = Path(temporary_directory.name)
        self.template_path: Path = self.directory.joinpath("template.json")
        self.template_path.write_text("{}", encoding="utf-8")

    def run_autotag(self) -> None:
        autotag = Autotag(
            "",
            "",
            self.directory.joinpath("input.pdf").as_posix(),
            self.directory.joinpath("output.pdf").as_posix(),
            self.template_path.as_posix(),
        )
        autotag.run()

    @mock.patch("autotag.subprocess.run")
    def test_sdk_error_is_logged_and_reported(self, run: mock.MagicMock) -> None:
        run.return_value = finished_process(31, SDK_OPEN_ERROR_STDOUT)
        with self.assertLogs("autotag", level="ERROR") as logs:
            with self.assertRaises(ExpectedException) as context:
                self.run_autotag()
        self.assertEqual(context.exception.error_code, EC_PDFIX_ERROR)
        self.assertEqual(context.exception.message, MESSAGE_PDFIX_ERROR)
        self.assertIn("Failed to open the document.", "\n".join(logs.output))

    @mock.patch("autotag.subprocess.run")
    def test_sdk_success_raises_nothing(self, run: mock.MagicMock) -> None:
        run.return_value = finished_process(0)
        self.run_autotag()
        run.assert_called_once()

    @mock.patch("autotag.subprocess.run")
    def test_progress_matches_config_progress_regex(self, run: mock.MagicMock) -> None:
        # Same pattern as "progress_regex" in config.json (Python named groups)
        progress_regex: re.Pattern[str] = re.compile(r"^(?P<text>[^:]+):\s+(?P<progress>\d{1,3})%")
        run.return_value = finished_process(0)
        stderr: io.StringIO = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.run_autotag()
        progress: list[tuple[str, str]] = []
        for line in re.split(r"[\r\n]", stderr.getvalue()):
            match: re.Match[str] | None = progress_regex.match(line)
            if match:
                progress.append((match.group("text"), match.group("progress")))
        self.assertEqual(progress[0], ("Starting", "0"))
        self.assertEqual(progress[-1], ("Done", "100"))


class TestSdkVersion(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.template_path: Path = Path(temporary_directory.name).joinpath("template.json")

    def sdk_version(self, template: str) -> str:
        self.template_path.write_text(template, encoding="utf-8")
        autotag = Autotag("", "", "input.pdf", "output.pdf", self.template_path.as_posix())
        return autotag._get_sdk_version()

    def test_unknown_version_logs_and_uses_latest(self) -> None:
        with self.assertLogs("autotag", level="INFO") as logs:
            version: str = self.sdk_version('{"metadata": {"sdk_version": "0.0.1"}}')
        self.assertEqual(version, LATEST_SDK_VERSION)
        self.assertIn(
            f"Unknown SDK version 0.0.1 in template file. Using latest version {LATEST_SDK_VERSION}.",
            "\n".join(logs.output),
        )

    def test_invalid_json_is_reported(self) -> None:
        for template in ("{bad", "[]"):
            with self.assertRaises(ExpectedException) as context:
                self.sdk_version(template)
            self.assertEqual(context.exception.error_code, EC_TEMPLATE_JSON_INVALID)

    def test_missing_version_uses_latest(self) -> None:
        self.assertEqual(self.sdk_version("{}"), LATEST_SDK_VERSION)


if __name__ == "__main__":
    unittest.main()
