from .main import generate_context
__version__ = '1.0.0'
__all__ = ['generate_context']

from logging_config import setup_logger
logger = setup_logger(__name__)
logger.info("Module initialized")