import logging
import os


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def env_var(var_name: str):
    if var_name not in os.environ:
        logger.warning('%s env variable was not found.', var_name)
        return None

    return os.environ[var_name]


TELEGRAM_TOKEN = env_var('TELEGRAM_TOKEN')