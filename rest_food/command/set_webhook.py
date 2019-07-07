import sys
from rest_food.handlers import set_tg_webhook


if __name__ == '__main__':
    set_tg_webhook(sys.argv[1])