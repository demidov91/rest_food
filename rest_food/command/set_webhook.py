import argparse
from enum import Enum

from rest_food.handlers import set_tg_webhook
from rest_food.settings import BOT_PATH_KEY, STAGE
from rest_food.entities import Workflow


class Server(Enum):
    AMAZON = 0
    FLASK = 1


parser = argparse.ArgumentParser(description='Set bot webhooks.')
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
    '-l',
    dest='server',
    nargs='?',
    const=Server.AMAZON,
    help='amazon lambda as a server'
)
parser.add_argument(
    '-f',
    dest='server',
    nargs='?',
    const=Server.FLASK,
    help='flask as a server'
)
parser.add_argument('url')

args = parser.parse_args()


WORKFLOW_PREFIX = {
    Workflow.DEMAND: 'demand',
    Workflow.SUPPLY: 'supply',
}


def _get_prefix_by_server(server: Server) -> str:
    if server == Server.FLASK:
        return 'tg'

    if server != Server.AMAZON:
        raise ValueError(server)

    return STAGE


def _set_webhook(*, url: str, server: Server, workflow: Workflow):
    if BOT_PATH_KEY is None:
        raise ValueError('Set BOT_PATH_KEY env variable.')

    url = f'{url}/{_get_prefix_by_server(server)}/{WORKFLOW_PREFIX[workflow]}/{BOT_PATH_KEY}/'
    set_tg_webhook(url, workflow=workflow)


if __name__ == '__main__':
    if args.server is None:
        raise ValueError('Please, provide either -l (amazon lambda) or -f (flask) key. ')

    if args.is_supply:
        _set_webhook(url=args.url, server=args.server, workflow=Workflow.SUPPLY)
    elif args.is_demand:
        _set_webhook(url=args.url, server=args.server, workflow=Workflow.DEMAND)
    else:
        _set_webhook(url=args.url, server=args.server, workflow=Workflow.SUPPLY)
        _set_webhook(url=args.url, server=args.server, workflow=Workflow.DEMAND)
