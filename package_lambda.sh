#!/bin/bash
set -e

OUTPUT_ZIP="inboxflow-infrastructure/lambda_package.zip"

echo "Packaging Lambda function in an Amazon Linux environment..."

# Create a package directory inside the inboxflow-imap-sync folder
mkdir -p inboxflow-imap-sync/package

# Use the AWS SAM build image for Python 3.9 to install dependencies into the package directory
docker run --rm --platform linux/amd64 -v "$PWD":/var/task public.ecr.aws/sam/build-python3.9 \
  pip install --no-cache-dir --only-binary=:all: --target /var/task/inboxflow-imap-sync/package -r inboxflow-imap-sync/requirements.txt

# Copy your Lambda code into the package directory
cp -r inboxflow-imap-sync/*.py inboxflow-imap-sync/package/

# Change directory to the package folder and create the zip file
cd inboxflow-imap-sync/package
zip -r9 ../../${OUTPUT_ZIP} .
cd ../../

# Clean up the package directory
rm -rf inboxflow-imap-sync/package

echo "Lambda package created: $(pwd)/${OUTPUT_ZIP}"