import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, Path(__file__).resolve().parent.parent.joinpath("src").as_posix())

import main  # noqa: E402
from exceptions import EC_ARG_TEMPLATE_FILE_NOT_EXISTS, ExpectedException  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
