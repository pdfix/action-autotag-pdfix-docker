EC_ARG_GENERAL: int = 10
EC_ARG_TEMPLATE_JSON: int = 11
EC_ARG_INPUT_PDF_OUTPUT_PDF: int = 12
EC_ARG_TEMPLATE_FILE_NOT_EXISTS: int = 13

EC_PDFIX_ERROR: int = 20
EC_TEMPLATE_JSON_INVALID: int = 21

MESSAGE_ARG_GENERAL: str = "Failed to parse arguments. Please check the usage and try again."
MESSAGE_ARG_TEMPLATE_JSON: str = "PDFix layout template was not provided."
MESSAGE_ARG_INPUT_PDF_OUTPUT_PDF: str = "Input and output file must be PDF documents."
MESSAGE_ARG_TEMPLATE_FILE_NOT_EXISTS: str = "PDFix layout template file does not exist."

MESSAGE_PDFIX_ERROR: str = "PDFix SDK failed to tag the document. See the log for more details."
MESSAGE_TEMPLATE_JSON_INVALID: str = "PDFix layout template is not a valid JSON file."


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


class ArgumentTemplateJsonException(ArgumentException):
    def __init__(self) -> None:
        super().__init__(MESSAGE_ARG_TEMPLATE_JSON, EC_ARG_TEMPLATE_JSON)


class ArgumentInputPdfOutputPdfException(ArgumentException):
    def __init__(self) -> None:
        super().__init__(MESSAGE_ARG_INPUT_PDF_OUTPUT_PDF, EC_ARG_INPUT_PDF_OUTPUT_PDF)


class ArgumentTemplateFileNotExistsException(ArgumentException):
    def __init__(self, path: str) -> None:
        super().__init__(f"{MESSAGE_ARG_TEMPLATE_FILE_NOT_EXISTS} {path}", EC_ARG_TEMPLATE_FILE_NOT_EXISTS)


class PdfixException(ExpectedException):
    def __init__(self, sdk_error: str = "") -> None:
        super().__init__(EC_PDFIX_ERROR)
        self._add_note(MESSAGE_PDFIX_ERROR)
        self.sdk_error = sdk_error


class TemplateJsonInvalidException(ExpectedException):
    def __init__(self) -> None:
        super().__init__(EC_TEMPLATE_JSON_INVALID)
        self._add_note(MESSAGE_TEMPLATE_JSON_INVALID)
