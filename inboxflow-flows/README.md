# InboxFlow Email Processing Flows

## Overview
This module manages user-defined email processing flows, allowing users to create custom automation for different email types.

## Example Flows
- **Recruiter Email Flow:** Determines if an email is a job opportunity and generates responses.
- **Real Estate Lead Flow:** Filters investment-related emails and prompts for property details.

## Managing Flows
### 1. Load an Existing Flow
```python
from flows_manager import load_flow
flow = load_flow("recruiter_flow")
print(flow)
```

### 2. Save a New Flow
```python
from flows_manager import save_flow
new_flow = {
  "name": "Sales Lead Flow",
  "conditions": {
    "subject_contains": ["lead", "customer inquiry"],
    "sender_contains": ["@sales.com"]
  },
  "actions": [{"if": "AI_confirms_sales_lead", "then": {"generate_response": "Follow-up with the lead."}}]
}
save_flow("sales_lead", new_flow)
```
