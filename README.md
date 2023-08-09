# Restaurant foodsharing bot.

## How to install python dependencies for local development

`pip install -r requirements/dev.txt`


## How to run it locally

`python -m rest_food.flask_start`

Bot server will run on port 5000


Update localization:
* `./createmessages.sh`
* Update messages in `rest_food/locale/`
* `./compilemessages.sh`


## Environment variables to be declared
```
TELEGRAM_TOKEN_SUPPLY
TELEGRAM_TOKEN_DEMAND
GOOGLE_API_KEY  -- required for geocoding when defining supplier's address
BOT_PATH_KEY -- key to be added into webhook url
DB_CONNECTION_STRING -- connection string including username and password if required
DB_NAME -- mongodb database name 
STAGE -- dev,staging,live
AWS_USER_ID -- required during amazon deployment only
TEST_TG_CHAT_ID -- comma-separated telegram ids to use on staging and dev. Other user messages will be silenced
DEFAULT_LANGUAGE -- be (for Belarusian) or ru (for Russian)
```

## How to configure webhooks

Update env variables

Local development (flask):

`python -m rest_food.command.set_webhook {public API (ngrok) address} -f`

Staging/live (lambda):

`python -m rest_food.command.set_webhook {lambda address} -l`


## How to deploy on staging/live

* Install `npm`
  * Install `serverless`

* Create sqs amazon queues (see `serverless.yaml`):
  * send_message_staging.fifo
  * super_send_staging.fifo
  * single_message_staging.fifo
  * send_message_live.fifo
  * super_send_live.fifo
  * single_message_live.fifo

* Update env variables

* Compile localization: `./compilemessages.sh`

* Run `serverless deploy` (`sls deploy`). 





