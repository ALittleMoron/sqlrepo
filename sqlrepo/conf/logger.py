import warnings
from typing import Any


class RepositoryModelClassIncorrectUseWarning(Warning):
    """Warning about Repository model_class attribute incorrect usage."""


class WarningWrapperLogger:
    def log_warn(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """Wrapper for warn function."""
        warnings.warn(msg, stacklevel=2)

    def log_print(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """Wrapper for print function."""
        print(msg)  # noqa: T201

    warn = warning = error = exception = critical = fatal = log_warn
    debug = info = log_print


default_logger = WarningWrapperLogger()
