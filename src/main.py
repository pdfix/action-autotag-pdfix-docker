import argparse
import logging
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from autotag import Autotag
from constants import CONFIG_FILE
from exceptions import (
    EC_ARG_GENERAL,
    MESSAGE_ARG_GENERAL,
    ArgumentInputPdfOutputPdfException,
    ArgumentTemplateFileNotExistsException,
    ArgumentTemplateJsonException,
    ExpectedException,
)
from image_update import DockerImageContainerUpdateChecker
from logger import get_logger

logger: logging.Logger = get_logger("app_logger")


def set_arguments(
    parser: argparse.ArgumentParser, names: list, required_output: bool = True, output_help: str = ""
) -> None:
    """
    Set arguments for the parser based on the provided names and options.

    Args:
        parser (argparse.ArgumentParser): The argument parser to set arguments for.
        names (list): List of argument names to set.
        required_output (bool): Whether the output argument is required. Defaults to True.
        output_help (str): Help for output argument. Defaults to "".
    """
    for name in names:
        match name:
            case "input":
                parser.add_argument("--input", "-i", type=str, required=True, help="The input PDF file.")
            case "key":
                parser.add_argument("--key", type=str, default="", nargs="?", help="PDFix license key.")
            case "name":
                parser.add_argument("--name", type=str, default="", nargs="?", help="PDFix license name.")
            case "output":
                parser.add_argument("--output", "-o", type=str, required=required_output, help=output_help)
            case "template":
                parser.add_argument(
                    "--template", "-t", type=str, required=True, help="PDFix layout template JSON file."
                )


def run_config_subcommand(args) -> None:
    get_pdfix_config(args.output)


def get_pdfix_config(path: str) -> None:
    """
    If Path is not provided, output content of config.
    If Path is provided, copy config to destination path.

    Args:
        path (string): Destination path for config.json file
    """
    config_path: Path = Path(__file__).parent.parent.joinpath(CONFIG_FILE)

    with open(config_path, "r", encoding="utf-8") as file:
        if path is None:
            # We want to print the config without additional logging formatting
            print(file.read())
        else:
            with open(path, "w") as out:
                out.write(file.read())


def run_autotag_subcommand(args) -> None:
    autotagging_pdf(args.name, args.key, args.input, args.output, args.template)


# @KA:action pdfix_autotag_pdfix
# @KA:desc Automatically tags the whole PDF with a PDFix layout template, using the same PDFix SDK
# version the template was created for. Existing tags are removed and the document gets a new
# structure tree; the input file is not changed, the tagged PDF is saved as the output file.
# @KA:context Run on the **whole document** when a PDF is untagged or its tags should be replaced,
# and you have a layout template for this kind of document (made in the PDFix Desktop template
# editor or by an AI layout action). Use it when results must match the template exactly as it was
# tuned, even if your PDFix Desktop is newer. Runs locally in Docker; the first run downloads the
# image and takes longer.
# @KA:param input_pdf
# @KA:desc PDF document to tag. It is only read, never changed. Password-protected PDFs are not
# supported. Scanned pages without real text get no text tags; run an OCR action first.
# @KA:problem "Input and output file must be PDF documents." (error 12)
# @KA:solution Use files with the `.pdf` extension for both input and output.
# @KA:param output_pdf
# @KA:desc Where the tagged PDF is saved. The folder must already exist; an existing file with
# the same name is overwritten.
# @KA:param template_json
# @KA:desc PDFix layout template (`.json`) that drives the tagging: what is a heading, paragraph,
# table, list or artifact. Required, the file must exist. The template remembers the PDFix SDK
# version it was made with, and the action uses that version (see **SDK version from the
# template**).
# @KA:problem "PDFix layout template was not provided." (error 11)
# @KA:solution Select a template file with the `.json` extension in the **Template JSON** field.
# @KA:problem "PDFix layout template file does not exist." (error 13)
# @KA:solution The selected template file was not found. The message shows the path the action
# looked for; select an existing template file.
# @KA:logic PDFix license
# @KA:desc PDFix Desktop passes your PDFix license to the action automatically. Without a
# license the action runs in trial mode.
# @KA:problem The output PDF has watermarks or randomly redacted content.
# @KA:solution Trial mode is active. Activate your PDFix license in PDFix Desktop and run
# the action again.
# @KA:logic Existing tags are replaced
# @KA:desc The whole document is tagged from scratch: the old structure tree and all old
# tags and artifact marks on the pages are removed first, nothing of them is kept. The new
# tree has one `Document` root, heading levels are kept in sequence (H1, H2, ...), and
# content that is not real content (headers, footers, decorations, as the template
# defines) is marked as artifact. Content inside Form XObjects is tagged too.
# @KA:logic What is not done
# @KA:desc The action only creates tags. It does not run OCR, add alternate text, set the
# document title or language, or fix metadata, and it does not validate the result. Run
# the matching actions afterwards and check the result with a PDF/UA validation.
# @KA:logic Tagging failed
# @KA:desc When PDFix SDK cannot open, tag or save the document, the action stops with
# error 20 "PDFix SDK failed to tag the document." and no output PDF is created. The log
# line below it, "PDFix SDK error ...", shows the SDK error code and message.
# @KA:problem Error 20 and the log shows PDFix SDK error 5.
# @KA:solution The input PDF does not exist or the output folder does not exist. Check
# both paths.
# @KA:problem Error 20 and the log shows PDFix SDK error 31 ("Failed to open document").
# @KA:solution The input file is not a valid PDF. Open and save it again in a PDF editor
# and run the action again.
# @KA:problem Error 20 and the log shows PDFix SDK error 34.
# @KA:solution The input PDF is password-protected. Remove the password and run the
# action again.
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
def autotagging_pdf(
    license_name: Optional[str],
    license_key: Optional[str],
    input_path: str,
    output_path: str,
    template_path: str,
) -> None:
    """
    Autotagging PDF document with provided arguments

    Args:
        license_name (Optional[str]): Name used in authorization in PDFix-SDK.
        license_key (Optional[str]): Key used in authorization in PDFix-SDK.
        input_path (str): Path to PDF document.
        output_path (str): Path to PDF document.
        template_path (str): Path to template JSON file.
    """
    if not template_path.lower().endswith(".json"):
        raise ArgumentTemplateJsonException()

    template_file_path: Path = Path(template_path).resolve()
    if not template_file_path.is_file():
        raise ArgumentTemplateFileNotExistsException(template_file_path.as_posix())

    if input_path.lower().endswith(".pdf") and output_path.lower().endswith(".pdf"):
        autotag = Autotag(
            license_name,
            license_key,
            input_path,
            output_path,
            template_path,
        )
        autotag.run()
    else:
        raise ArgumentInputPdfOutputPdfException()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autotag PDF file using PDFix SDK",
    )

    subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

    # Config subparser
    config_subparser = subparsers.add_parser(
        "config",
        help="Extract config file for integration",
    )
    set_arguments(
        config_subparser,
        ["output"],
        False,
        "Output to save the config JSON file. Application output is used if not provided.",
    )
    config_subparser.set_defaults(func=run_config_subcommand)

    # Autotag subparser
    autotag_subparser = subparsers.add_parser(
        "tag",
        help="Run autotag PDF document",
    )
    set_arguments(
        autotag_subparser,
        ["name", "key", "input", "output", "template"],
        True,
        "The output PDF file.",
    )
    autotag_subparser.set_defaults(func=run_autotag_subcommand)

    # Parse arguments
    try:
        args = parser.parse_args()
    except ExpectedException as e:
        logger.error(e.message)
        sys.exit(e.error_code)
    except SystemExit as e:
        if e.code != 0:
            logger.error(MESSAGE_ARG_GENERAL)
            sys.exit(EC_ARG_GENERAL)
        # This happens when --help is used, exit gracefully
        sys.exit(0)
    except Exception as e:
        logger.error("Failed to run the program:")
        logger.exception(e)
        sys.exit(1)

    if hasattr(args, "func"):
        # Check for updates only when help is not checked
        update_checker = DockerImageContainerUpdateChecker()
        # Check it in separate thread not to be delayed when there is slow or no internet connection
        update_thread = threading.Thread(target=update_checker.check_for_image_updates)
        update_thread.start()

        # Measure the time it takes to make all requests
        start_time = time.time()  # Record the start time
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logger.info(f"Processing started at: {current_time}")

        # Run subcommand
        try:
            args.func(args)
        except ExpectedException as e:
            logger.error(e.message)
            if e.sdk_error:
                logger.error(e.sdk_error)
            sys.exit(e.error_code)
        except Exception as e:
            # not expected exception -> print stack trace and what exception happened
            logger.error("Failed to run the program:")
            logger.exception(e)
            sys.exit(1)
        finally:
            end_time = time.time()  # Record the end time
            elapsed_time = end_time - start_time  # Calculate the elapsed time
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            logger.info(f"Processing finished at: {current_time}. Elapsed time: {elapsed_time:.2f} seconds")

            # Make sure to let update thread finish before exiting
            update_thread.join()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
