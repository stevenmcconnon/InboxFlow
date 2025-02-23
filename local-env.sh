#!/bin/bash
# local-env.sh: Automatically load environment variables from .env

if [ -f .env ]; then
  set -a
  source .env
  set +a
  echo "Local environment variables loaded from .env"
else
  echo ".env file not found!"
fi