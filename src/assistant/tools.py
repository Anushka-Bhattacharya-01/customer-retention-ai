"""Tools the LLM can call. Each tool has a JSON schema (what the LLM sees) and a Python function (what runs)."""
from typing import Callable

from src.assistant import db

TOOL_SPECS = [
    {
        "toolSpec": {
            "name": "get_customer",
            "description": "Look up a customer's account details by customer ID (for example C0007).",
            "inputSchema": {"json": {
                "type": "object",
                "properties": {"customer_id": {"type": "string", "description": "Customer ID like C0007"}},
                "required": ["customer_id"],
            }},
        }
    },
    {
        "toolSpec": {
            "name": "predict_churn",
            "description": "Run the churn ML model for a customer ID. Returns the probability (0-1) that the customer will leave.",
            "inputSchema": {"json": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            }},
        }
    },
    {
        "toolSpec": {
            "name": "suggest_retention_offer",
            "description": "Suggest a retention offer based on churn probability and contract type.",
            "inputSchema": {"json": {
                "type": "object",
                "properties": {
                    "churn_probability": {"type": "number"},
                    "contract": {"type": "string", "enum": ["month-to-month", "one-year", "two-year"]},
                },
                "required": ["churn_probability", "contract"],
            }},
        }
    },
]

MODEL_FEATURES = ["tenure", "monthly_charges", "total_charges", "contract",
                  "internet_service", "support_calls", "paperless_billing"]


def suggest_retention_offer(churn_probability: float, contract: str) -> dict:
    """Simple business rules, kept outside the LLM so offers are predictable and auditable."""
    if churn_probability >= 0.7:
        offer = "20% discount for 6 months if they move to a one-year contract" if contract == "month-to-month" \
            else "Priority support and a free plan upgrade for 3 months"
        priority = "high"
    elif churn_probability >= 0.4:
        offer = "10% loyalty discount and a check-in call from the support team"
        priority = "medium"
    else:
        offer = "No offer needed; include in the regular satisfaction survey"
        priority = "low"
    return {"priority": priority, "offer": offer}


def run_tool(name: str, args: dict, predict_fn: Callable[[dict], float]) -> dict:
    """Execute a tool call from the LLM. Errors are returned to the LLM instead of crashing the request."""
    if name == "get_customer":
        customer = db.get_customer(str(args.get("customer_id", "")).upper())
        return customer or {"error": f"Customer {args.get('customer_id')} not found"}

    if name == "predict_churn":
        customer = db.get_customer(str(args.get("customer_id", "")).upper())
        if not customer:
            return {"error": f"Customer {args.get('customer_id')} not found"}
        prob = predict_fn({k: customer[k] for k in MODEL_FEATURES})
        return {"customer_id": customer["customer_id"], "churn_probability": round(prob, 4)}

    if name == "suggest_retention_offer":
        return suggest_retention_offer(float(args["churn_probability"]), args["contract"])

    return {"error": f"Unknown tool {name}"}
