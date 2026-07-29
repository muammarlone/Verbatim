class StudioError(Exception):
    """Expected error safe to expose to the local UI."""

    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class NotFoundError(StudioError):
    def __init__(self, message: str = "The requested job was not found.") -> None:
        super().__init__("JOB_NOT_FOUND", message, http_status=404)


class BatchNotFoundError(StudioError):
    def __init__(self) -> None:
        super().__init__("BATCH_NOT_FOUND", "The requested batch was not found.", http_status=404)
