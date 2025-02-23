import json
import os

FLOW_DIR = "flows/"

def load_flow(flow_name):
    """Load a flow by name."""
    flow_path = os.path.join(FLOW_DIR, f"{flow_name}.json")
    if not os.path.exists(flow_path):
        return None
    with open(flow_path, "r") as f:
        return json.load(f)

def save_flow(flow_name, flow_data):
    """Save a flow to JSON."""
    os.makedirs(FLOW_DIR, exist_ok=True)
    flow_path = os.path.join(FLOW_DIR, f"{flow_name}.json")
    with open(flow_path, "w") as f:
        json.dump(flow_data, f, indent=2)
    return True
