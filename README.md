# SbubbyBot
A bot that helps moderate r/sbubby. Does a bunch of things like flairing reminders and removing common reposts.

# Installation
You will need to add all the environment variables (see below) as well as create a bot on reddit. You will need to create a bot that has a client Id and secret, can be found on preferences page of reddit.com

## Running
Everything has been dockerized! This means the setup process is a million times easier, but still requires a couple steps:
1. Install docker and [docker-compose](https://docs.docker.com/compose/install/#install-compose).
2. Add a file into the src folder entitled `.env` (no file extension, just .env) and add the variables oulined below.
3. In the cloned repo's root folder, run `docker-compose up`

## Enviroment Vars Needed
The following variables should be put into a .env file in the root directory.

| Variables    | Explanation |
|--------------|-------------|
| `client_id`  | Client ID of reddit bot |
| `client_secret` | secret of reddit bot |
| `reddit_username` | the reddit username of account bot is set up under (will control that account) |
| `reddit_password` | password of above |
| `database_name` | Make this `sbubby` |
| `database_password` | Make this `dev` |
| `DATABASE_URL` | Make this `postgresql+psycopg2://sbubby:dev@db/sbubby` |
