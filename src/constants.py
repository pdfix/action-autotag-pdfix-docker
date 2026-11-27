CONFIG_FILE: str = "config.json"
DOCKER_NAMESPACE: str = "pdfix"
DOCKER_REPOSITORY: str = "autotag-pdfix"
DOCKER_IMAGE: str = f"{DOCKER_NAMESPACE}/{DOCKER_REPOSITORY}"
LATEST_SDK_VERSION: str = "v8.8.0"
SDK_ERROR_INVALID_PASSWORD: int = 34  # PDFix SDK error type of OpenDoc with a missing or wrong password
