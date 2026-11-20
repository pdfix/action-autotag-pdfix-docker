import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

from tqdm import tqdm

from constants import LATEST_SDK_VERSION
from exceptions import PdfixException, TemplateJsonInvalidException
from logger import get_logger

logger: logging.Logger = get_logger(__name__)


class Autotag:
    """
    Class that runs inputs with proper SDK.
    """

    def __init__(
        self,
        license_name: Optional[str],
        license_key: Optional[str],
        input_path: str,
        output_path: str,
        tempalte_path: str,
    ) -> None:
        """
        Initialize class for tagging pdf.

        Args:
            license_name (Optional[str]): Pdfix SDK license name (e-mail).
            license_key (Optional[str]): Pdfix SDK license key.
            input_path (str): Path to PDF document.
            output_path (str): Path where tagged PDF should be saved.
            tempalte_path (str): Path to layout template JSON file.
        """
        self.license_name = license_name
        self.license_key = license_key
        self.input_path_str = input_path
        self.output_path_str = output_path
        self.template_path_str = tempalte_path

    def run(self) -> None:
        """
        Run PDFix SDK autotagging.
        """
        with tqdm(total=100) as progress_bar:
            progress_bar.set_description("Starting")
            progress_bar.refresh()

            sdk_folder: str = self._get_sdk_version()
            sdk_executable: Path = Path(__file__).parent.parent.joinpath("sdk", sdk_folder, "pdfix_app")

            command: list[str] = [sdk_executable.as_posix()]

            # @KA:action pdfix_autotag_pdfix
            # @KA:logic PDFix license
            # @KA:desc PDFix Desktop passes your PDFix license to the action automatically. Without a
            # license the action runs in trial mode.
            # @KA:problem The output PDF has watermarks or randomly redacted content.
            # @KA:solution Trial mode is active. Activate your PDFix license in PDFix Desktop and run
            # the action again.
            if self.license_name:
                command.append("--email")
                command.append(self.license_name)

            # PDFix license name
            if self.license_key:
                command.append("--key")
                command.append(self.license_key)

            # @KA:logic Existing tags are replaced
            # @KA:desc The whole document is tagged from scratch: the old structure tree and all old
            # tags and artifact marks on the pages are removed first, nothing of them is kept. The new
            # tree has one `Document` root, heading levels are kept in sequence (H1, H2, ...), and
            # content that is not real content (headers, footers, decorations, as the template
            # defines) is marked as artifact. Content inside Form XObjects is tagged too.
            #
            # @KA:logic What is not done
            # @KA:desc The action only creates tags. It does not run OCR, add alternate text, set the
            # document title or language, or fix metadata, and it does not validate the result. Run
            # the matching actions afterwards and check the result with a PDF/UA validation.
            command.append("add-tags")

            # Input
            command.append("-i")
            input_path: Path = Path(self.input_path_str).resolve()
            command.append(input_path.as_posix())

            # Template
            command.append("-c")
            template_path: Path = Path(self.template_path_str).resolve()
            command.append(template_path.as_posix())

            # Output
            command.append("-o")
            output_path: Path = Path(self.output_path_str).resolve()
            command.append(output_path.as_posix())

            logger.info(f"Running:\n{' '.join(command)}")

            result: subprocess.CompletedProcess[str] = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )

            logger.debug(f"Return code: {result.returncode}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")

            # @KA:logic Tagging failed
            # @KA:desc When PDFix SDK cannot open, tag or save the document, the action stops with
            # error 20 "PDFix SDK failed to tag the document." and no output PDF is created. The log
            # line above it, "PDFix SDK failed with return code ...", shows the code and the SDK
            # message.
            # @KA:problem Error 20 and the log shows return code 5.
            # @KA:solution The input PDF does not exist or the output folder does not exist. Check
            # both paths.
            # @KA:problem Error 20 and the log shows return code 31 ("Failed to open the document").
            # @KA:solution The input file is not a valid PDF. Open and save it again in a PDF editor
            # and run the action again.
            # @KA:problem Error 20 and the log shows return code 34.
            # @KA:solution The input PDF is password-protected. Remove the password and run the
            # action again.
            if result.returncode != 0:
                # PDFix SDK prints its error message to stdout
                logger.error(f"PDFix SDK failed with return code {result.returncode}:\n{result.stdout}{result.stderr}")
                raise PdfixException()

            progress_bar.n = 100
            progress_bar.set_description("Done")
            progress_bar.refresh()

    def _get_sdk_version(self) -> str:
        """
        Get SDK version from template JSON file.

        Returns:
            SDK version or latest version if template is not provided.
        """
        template_path: Path = Path(self.template_path_str)

        # @KA:logic SDK version from the template
        # @KA:desc The action contains the released PDFix SDK versions and tags the document with the
        # version written in the template (`sdk_version` in the template metadata). The same template
        # with the same SDK version gives the same tags as when the template was tuned, independent
        # of the PDFix Desktop version you use. If the template has no SDK version, or the version
        # is not available in the action, the newest SDK version in the action is used.
        # @KA:problem Tagging differs from what the template produced when it was created.
        # @KA:solution Look in the action log. "Unknown SDK version ... Using latest version ..."
        # means the template's SDK version is not available in the action and a newer one was used.
        # Update the action or recreate the template with a current PDFix version.
        # @KA:problem "PDFix layout template is not a valid JSON file." (error 21)
        # @KA:solution The template file is damaged or is not a layout template. The log shows where
        # reading failed. Export the template again or select another template file.
        if template_path.exists():
            logger.debug("Searching for SDK version in template file.")
            with open(template_path, "r", encoding="utf-8") as file:
                try:
                    template: Any = json.load(file)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.error(f"Failed to read template file: {e}")
                    raise TemplateJsonInvalidException()
                if not isinstance(template, dict):
                    raise TemplateJsonInvalidException()
                metadata: dict[str, Any] = template.get("metadata", {})
                version: str = metadata.get("sdk_version", "")
                if version:
                    logger.info(f"Found SDK version in template file: {version}")
                else:
                    logger.debug("No SDK version found in template file. Using latest version.")
                    return LATEST_SDK_VERSION

                teoretical_path_to_sdk_folder: Path = Path(__file__).parent.parent.joinpath("sdk", version)
                if teoretical_path_to_sdk_folder.exists():
                    logger.debug("Verified existence of SDK folder in docker image.")
                    return version

                prefixed_version: str = f"v{version}"

                teoretical_path_to_sdk_folder = Path(__file__).parent.parent.joinpath("sdk", prefixed_version)
                if teoretical_path_to_sdk_folder.exists():
                    logger.debug("Verified existence of SDK folder in docker image.")
                    return prefixed_version

                logger.info(
                    f"Unknown SDK version {version} in template file. Using latest version {LATEST_SDK_VERSION}."
                )

        return LATEST_SDK_VERSION
