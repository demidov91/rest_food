import logging
import os


logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


BASE_DIR = os.path.dirname(__file__)


def env_var(var_name: str, default=None):
    if var_name not in os.environ:
        logger.warning('%s env variable was not found.', var_name)
        return default

    return os.environ[var_name]


TELEGRAM_TOKEN_SUPPLY = env_var('TELEGRAM_TOKEN_SUPPLY')
TELEGRAM_TOKEN_DEMAND = env_var('TELEGRAM_TOKEN_DEMAND')
YANDEX_API_KEY = env_var('YANDEX_API_KEY', None)
GOOGLE_API_KEY = env_var('GOOGLE_API_KEY', None)
BOT_PATH_KEY = env_var('BOT_PATH_KEY')
DB_CONNECTION_STRING = env_var('DB_CONNECTION_STRING')
DB_NAME = env_var('DB_NAME')
DEFAULT_LANGUAGE = env_var('DEFAULT_LANGUAGE')
STAGE = env_var('STAGE')

# Mon, Mon, Dz, G, I, Dz(add)
TEST_TG_CHAT_ID = env_var('TEST_TG_CHAT_ID', '').split(',')
TEST_TG_CHAT_ID.extend([int(x) for x in TEST_TG_CHAT_ID if x])

FEEDBACK_TG_BOT = '@foodsharingsupportbot'