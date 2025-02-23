#!/bin/bash
echo "Running all tests..."
pytest inboxflow_dispatcher/tests/
pytest inboxflow-imap-sync/tests/
pytest inboxflow-api/tests/
pytest inboxflow-flows/tests/
cd inboxflow-frontend && npm test
