import argparse
import sys
from rest_food.handlers import set_tg_webhook
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
parser.add_argument('url')

args = parser.parse_args()


def _set_supply(url: str):
    set_tg_webhook(url + '/tg/supply/path-key/', workflow=Workflow.SUPPLY)


def _set_demand(url: str):
    set_tg_webhook(url + '/tg/demand/path-key/', workflow=Workflow.DEMAND)


if __name__ == '__main__':
    if args.is_supply:
        _set_supply(args.url)
    elif args.is_demand:
        _set_demand(args.url)
    elif args.set_both:
        _set_demand(args.url)
        _set_supply(args.url)
    else:
        raise ValueError('Specify either -s for supply or -d for demand or --both.')
