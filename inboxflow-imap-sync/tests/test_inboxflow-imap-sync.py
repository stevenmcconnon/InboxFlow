import pytest
from inboxflow_imap_sync.imap_sync import fetch_new_emails

def test_fetch_new_emails():
    assert fetch_new_emails() is None  # Just testing execution without errors
