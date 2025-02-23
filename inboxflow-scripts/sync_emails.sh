#!/bin/bash
echo "Triggering manual email sync..."
curl -X POST http://localhost:8000/sync-emails
