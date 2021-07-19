import logging


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)-15s %(threadName)s %(levelname)s %(name)s %(message)s",
    )

    # tell noisy loggers to be quiet
    logging.getLogger("urllib3.connectionpool").propagate = False


def get_silent_logger() -> logging.Logger:
    logger = logging.Logger(name="blackhole", level=logging.CRITICAL)
    logger.propagate = False
    return logger
