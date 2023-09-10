import argparse
import importlib


parser = argparse.ArgumentParser(description='Migrate mongodb.')
parser.add_argument(
    '-f',
    dest='is_forward',
    nargs='?',
    const=True,
    default=False,
    help='forward migration'
)
parser.add_argument(
    '-b',
    dest='is_backward',
    nargs='?',
    const=True,
    default=False,
    help='backward migration'
)
parser.add_argument('migration_number', type=int)

arguments = parser.parse_args()


def run(module_name, method: str):
    module = importlib.import_module(f'rest_food.migrations.{module_name}')
    getattr(module, method)()


if __name__ == '__main__':
    if arguments.is_forward:
        run(module_name=arguments.migration_number, method='forward')
    elif arguments.is_backward:
        run(module_name=arguments.migration_number, method='backward')

    else:
        raise ValueError('Specify either -b or -f')