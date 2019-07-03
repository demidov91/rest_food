from rest_food.handlers import tg_supply, tg_demand


def telegram_supply_handler(event: dict, context):
    tg_supply(event)


def telegram_demand_handler(event: dict, context):
    tg_demand(event)
