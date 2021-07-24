from logging import CRITICAL, DEBUG, Logger, LoggerAdapter, basicConfig, getLogger
from typing import Any, Optional, Tuple


def configure_logging(filename: Optional[str]) -> None:
    basicConfig(
        level=DEBUG,
        format="%(asctime)-15s %(threadName)s %(levelname)s %(name)s %(message)s",
        filename=filename,
    )

    # tell noisy loggers to be quiet
    getLogger("urllib3.connectionpool").propagate = False


def get_silent_logger() -> Logger:
    logger = Logger(name="blackhole", level=CRITICAL)
    logger.propagate = False
    return logger


class CtxLogger(LoggerAdapter):
    def __init__(self, logger: Logger, extra: Tuple[Any], prefix: str) -> None:
        super().__init__(logger, extra)

        self.prefix = prefix

    def process(self, msg, kwargs):
        prefix = self.prefix % self.extra

        msg = f"{prefix}{msg}"
        return msg, kwargs
