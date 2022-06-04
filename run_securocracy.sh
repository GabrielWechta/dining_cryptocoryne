#!/bin/bash

# Clean-up all leftovers
docker-compose down --remove-orphans

# Start the server
docker-compose up --build --detach server-service || { echo "Composing server service failed" && exit 1; }
# Start the client
#docker-compose up --build --detach yes-client-service || { echo "Composing echo service failed" && docker-compose down && exit 1; }

echo "!!!Setting up local environment..."
set -a
. ./.env
set +a

# Overwrite the hostname with localhost
export SERVER_HOSTNAME=localhost

pip install -e client
echo "!!!Running local client..."
python -m client
#
#docker-compose down
