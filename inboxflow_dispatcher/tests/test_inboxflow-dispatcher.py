import pytest
from inboxflow_dispatcher.dispatcher import fetch_unprocessed_emails

def test_fetch_unprocessed_emails():
    emails = fetch_unprocessed_emails()
    assert isinstance(emails, list)
