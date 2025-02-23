#!/bin/bash
set -e

echo "Building and deploying backend..."

docker build -t inboxflow-backend .

aws ecr get-login-password --region us-west-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-west-1.amazonaws.com

docker tag inboxflow-backend:latest 123456789012.dkr.ecr.us-west-1.amazonaws.com/inboxflow-backend:latest
docker push 123456789012.dkr.ecr.us-west-1.amazonaws.com/inboxflow-backend:latest

echo "Deployment complete."
