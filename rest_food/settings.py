import logging
import os


logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


BASE_DIR = os.path.dirname(__file__)


def env_var(var_name: str):
    if var_name not in os.environ:
        logger.warning('%s env variable was not found.', var_name)
        return None

    return os.environ[var_name]


TELEGRAM_TOKEN_SUPPLY = env_var('TELEGRAM_TOKEN_SUPPLY')
TELEGRAM_TOKEN_DEMAND = env_var('TELEGRAM_TOKEN_DEMAND')
YANDEX_API_KEY = env_var('YANDEX_API_KEY')
BOT_PATH_KEY = env_var('BOT_PATH_KEY')
DB_CONNECTION_STRING = env_var('DB_CONNECTION_STRING')
DB_NAME = env_var('DB_NAME')
STAGE = env_var('STAGE')

# Mon, G, Dz, I, Mon, Dz(add)
TEST_TG_CHAT_ID = (1020027359, 793014155, 274229718, 524816100, 121866003, 1038927235)
TEST_TG_CHAT_ID = TEST_TG_CHAT_ID + tuple(str(x) for x in TEST_TG_CHAT_ID)

FEEDBACK_TG_BOT = '@foodsharingsupportbot'