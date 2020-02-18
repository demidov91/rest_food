# Restaurant foodsharing bot.

## How to install python dependencies for local development

`pip install -r requirements/dev.txt`


## How to run it locally

`python -m rest_food.flask`

Bot server will run on port 5000


## Environment variables to be declared
```
TELEGRAM_TOKEN_SUPPLY
TELEGRAM_TOKEN_DEMAND
YANDEX_API_KEY
BOT_PATH_KEY -- key to be added into webhook url
DB_CONNECTION_STRING 
DB_NAME 
STAGE -- dev, staging,live
```

## How to configure webhooks

Local development (flask):

`python -m rest_food.command.set_webhook -f`

Staging/live (lambda):

`python -m rest_food.command.set_webhook -l`


## How to deploy on staging/live

`npm` should be installed.

Update env variables

Run `serverless deploy` (`sls deploy`). 





