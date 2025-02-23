import pytest
from fastapi.testclient import TestClient
from inboxflow_api.api import app

client = TestClient(app)

def test_get_emails():
    response = client.get("/emails")
    assert response.status_code == 200
