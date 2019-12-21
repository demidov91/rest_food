import argparse
from rest_food.handlers import set_tg_webhook
from rest_food.settings import BOT_PATH_KEY
from rest_food.entities import Workflow


parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument(
    '-s',
    dest='is_supply',
    nargs='?',
    const=True,
    default=False,
    help='is supply bot'
)
parser.add_argument(
    '-d',
    dest='is_demand',
    nargs='?',
    const=True,
    default=False,
    help='is demand bot'
)
parser.add_argument(
    '--both',
    dest='set_both',
    nargs='?',
    const=True,
    default=False,
    help='both bots'
)
parser.add_argument(
    '--full',
    dest='is_full_url',
    nargs='?',
    const=True,
    default=False,
    help='full url was provided'
)
parser.add_argument('url')

args = parser.parse_args()


def _set_supply(url: str, is_full_url: bool):
    if not is_full_url:
        url = f'{url}/tg/supply/{BOT_PATH_KEY}/'

    set_tg_webhook(url, workflow=Workflow.SUPPLY)


def _set_demand(url: str, is_full_url: bool):
    if not is_full_url:
        url = f'{url}/tg/demand/{BOT_PATH_KEY}/'

    set_tg_webhook(url, workflow=Workflow.DEMAND)


if __name__ == '__main__':
    if args.is_supply:
        _set_supply(args.url, args.is_full_url)
    elif args.is_demand:
        _set_demand(args.url, args.is_full_url)
    elif args.set_both:
        _set_demand(args.url, args.is_full_url)
        _set_supply(args.url, args.is_full_url)
    else:
        raise ValueError('Specify either -s for supply or -d for demand or --both.')
