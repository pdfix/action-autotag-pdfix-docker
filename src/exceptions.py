EC_ARG_GENERAL: int = 10
EC_ARG_OUTPUT_NOT_PDF: int = 11
EC_ARG_OUTPUT_FOLDER_NOT_EXISTS: int = 12
EC_ARG_INPUT_NOT_PDF: int = 13
EC_ARG_TEMPLATE_NOT_JSON: int = 14
EC_ARG_TEMPLATE_JSON_INVALID: int = 15

EC_PDFIX_FAILED_TO_TAG: int = 20

EC_PDF_PASSWORD: int = 30

MESSAGE_ARG_GENERAL: str = "Failed to parse arguments. Please check the usage and try again."
MESSAGE_ARG_OUTPUT_NOT_PDF: str = "Output file must be PDF document."
MESSAGE_ARG_OUTPUT_FOLDER_NOT_EXISTS: str = "Output folder does not exist."
MESSAGE_ARG_INPUT_NOT_PDF: str = "Input file must be an existing PDF document."
MESSAGE_ARG_TEMPLATE_NOT_JSON: str = "PDFix layout template must be an existing JSON file."
MESSAGE_ARG_TEMPLATE_JSON_INVALID: str = "PDFix layout template is not a valid JSON file."

MESSAGE_PDFIX_FAILED_TO_TAG: str = "Failed to tag PDF document."

MESSAGE_PDF_PASSWORD: str = "PDF document is password-protected. Remove the password with another action first."


class ExpectedException(BaseException):
    def __init__(self, error_code: int) -> None:
        self.error_code: int = error_code
        self.message: str = ""
        # Error text from PDFix SDK, logged on its own line after the message
        self.sdk_error: str = ""

    def _add_note(self, note: str) -> None:
        self.message = note


class ArgumentException(ExpectedException):
    def __init__(self, message: str = MESSAGE_ARG_GENERAL, error_code: int = EC_ARG_GENERAL) -> None:
        super().__init__(error_code)
        self._add_note(message)


class ArgumentOutputNotPdfException(ArgumentException):
    def __init__(self) -> None:
        super().__init__(MESSAGE_ARG_OUTPUT_NOT_PDF, EC_ARG_OUTPUT_NOT_PDF)


class ArgumentOutputFolderNotExistsException(ArgumentException):
    def __init__(self, path: str) -> None:
        super().__init__(f"{MESSAGE_ARG_OUTPUT_FOLDER_NOT_EXISTS} {path}", EC_ARG_OUTPUT_FOLDER_NOT_EXISTS)


class ArgumentInputNotPdfException(ArgumentException):
    def __init__(self, path: str) -> None:
        super().__init__(f"{MESSAGE_ARG_INPUT_NOT_PDF} {path}", EC_ARG_INPUT_NOT_PDF)


class ArgumentTemplateNotJsonException(ArgumentException):
    def __init__(self, path: str) -> None:
        super().__init__(f"{MESSAGE_ARG_TEMPLATE_NOT_JSON} {path}", EC_ARG_TEMPLATE_NOT_JSON)


class TemplateJsonInvalidException(ArgumentException):
    def __init__(self) -> None:
        super().__init__(MESSAGE_ARG_TEMPLATE_JSON_INVALID, EC_ARG_TEMPLATE_JSON_INVALID)


class PdfixException(ExpectedException):
    def __init__(self, sdk_error: str = "") -> None:
        super().__init__(EC_PDFIX_FAILED_TO_TAG)
        self._add_note(MESSAGE_PDFIX_FAILED_TO_TAG)
        self.sdk_error = sdk_error


class PdfPasswordException(ExpectedException):
    def __init__(self, path: str, sdk_error: str = "") -> None:
        super().__init__(EC_PDF_PASSWORD)
        self._add_note(f"{MESSAGE_PDF_PASSWORD} {path}")
        self.sdk_error = sdk_error
