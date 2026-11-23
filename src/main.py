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

logger: logging.Logger = get_logger(__name__)


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
    if not template_path.lower().endswith(".json"):
        raise ArgumentTemplateJsonException()

    template_file_path: Path = Path(template_path).resolve()
    if not template_file_path.is_file():
        raise ArgumentTemplateFileNotExistsException(template_file_path.as_posix())

    # @KA:param input_pdf
    # @KA:desc PDF document to tag. It is only read, never changed. Password-protected PDFs are not
    # supported. Scanned pages without real text get no text tags; run an OCR action first.
    # @KA:problem "Input and output file must be PDF documents." (error 12)
    # @KA:solution Use files with the `.pdf` extension for both input and output.
    #
    # @KA:param output_pdf
    # @KA:desc Where the tagged PDF is saved. The folder must already exist; an existing file with
    # the same name is overwritten.
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
