from telegram.update import Update


def tg_supply(data):
    update = Update.de_json(data, None)


def tg_demand(data):
    pass

