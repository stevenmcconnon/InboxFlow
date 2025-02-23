import pytest
from inboxflow_flows.flows_manager import load_flow

def test_load_recruiter_flow():
    flow = load_flow("recruiter_flow")
    assert flow is not None
