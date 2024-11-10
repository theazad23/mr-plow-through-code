import logging
import logging.config

def setup_logger(name: str = "app_logger", level: int = logging.DEBUG) -> logging.Logger:
    """Sets up a logger with a specified name and log level."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=level, format=log_format)
    logger = logging.getLogger(name)
    return logger
