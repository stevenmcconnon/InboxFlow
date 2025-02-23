#!/bin/bash
set -e

echo "Building and deploying frontend..."

npm run build

aws s3 sync build/ s3://inboxflow-frontend --delete

echo "Deployment complete."
