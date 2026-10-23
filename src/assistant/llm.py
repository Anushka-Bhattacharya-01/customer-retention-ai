"""LLM clients. Both use the Amazon Bedrock Converse API message format.

BedrockLLM -> real model on Amazon Bedrock (needs AWS credentials and model access)
MockLLM    -> deterministic stand-in that follows the same tool-calling flow, so the
              app, tests and CI run without AWS and without paying for tokens
"""
import json
import re

from src import config


class BedrockLLM:
    def __init__(self):
        import boto3
        self.client = boto3.client("bedrock-runtime", region_name=config.BEDROCK_REGION)
        self.model_id = config.BEDROCK_MODEL_ID

    def converse(self, system: str, messages: list, tools: list) -> dict:
        return self.client.converse(
            modelId=self.model_id,
            system=[{"text": system}],
            messages=messages,
            toolConfig={"tools": tools},
            inferenceConfig={"maxTokens": config.MAX_OUTPUT_TOKENS, "temperature": 0},
        )


class MockLLM:
    """Plays the role of the LLM: decides which tool to call next, then writes the answer."""
    model_id = "mock-llm"

    def converse(self, system: str, messages: list, tools: list) -> dict:
        question = messages[0]["content"][0]["text"]
        results = {}  # tool name -> result, collected from earlier turns
        tool_names = {}
        for msg in messages:
            for block in msg["content"]:
                if "toolUse" in block:
                    tool_names[block["toolUse"]["toolUseId"]] = block["toolUse"]["name"]
                if "toolResult" in block:
                    name = tool_names[block["toolResult"]["toolUseId"]]
                    results[name] = block["toolResult"]["content"][0]["json"]

        match = re.search(r"\bC\d{4}\b", question.upper())
        if not match:
            return self._text("Please share a customer ID (for example C0007) so I can check their churn risk.", messages)
        cid = match.group(0)

        if "get_customer" not in results:
            return self._tool("get_customer", {"customer_id": cid}, messages)
        if "error" in results["get_customer"]:
            return self._text(f"I could not find customer {cid}.", messages)
        if "predict_churn" not in results:
            return self._tool("predict_churn", {"customer_id": cid}, messages)
        if "suggest_retention_offer" not in results:
            return self._tool("suggest_retention_offer", {
                "churn_probability": results["predict_churn"]["churn_probability"],
                "contract": results["get_customer"]["contract"],
            }, messages)

        c, p, o = results["get_customer"], results["predict_churn"]["churn_probability"], results["suggest_retention_offer"]
        reasons = []
        if c["contract"] == "month-to-month":
            reasons.append("is on a month-to-month contract")
        if c["support_calls"] >= 3:
            reasons.append(f"has made {c['support_calls']} support calls")
        if c["tenure"] < 12:
            reasons.append(f"joined only {c['tenure']} month{'s' if c['tenure'] != 1 else ''} ago")
        if c["monthly_charges"] > 90:
            reasons.append(f"pays a high monthly bill ({c['monthly_charges']})")
        why = ", ".join(reasons) if reasons else "has a stable profile"
        return self._text(
            f"Customer {cid} has a {p:.0%} chance of leaving ({o['priority']} priority). "
            f"Main reasons: the customer {why}. Suggested action: {o['offer']}.", messages)

    # --- helpers that build a Bedrock-style response with an estimated token count ---
    @staticmethod
    def _tokens(messages, output: str) -> dict:
        input_tokens = len(json.dumps(messages)) // 4      # rough estimate: ~4 characters per token
        output_tokens = max(1, len(output) // 4)
        return {"inputTokens": input_tokens, "outputTokens": output_tokens, "totalTokens": input_tokens + output_tokens}

    def _tool(self, name, args, messages):
        n = sum(1 for m in messages for b in m["content"] if "toolUse" in b)
        return {
            "output": {"message": {"role": "assistant", "content": [
                {"toolUse": {"toolUseId": f"tool-{n + 1}", "name": name, "input": args}}]}},
            "stopReason": "tool_use",
            "usage": self._tokens(messages, json.dumps(args)),
        }

    def _text(self, text, messages):
        return {
            "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
            "stopReason": "end_turn",
            "usage": self._tokens(messages, text),
        }


def get_llm():
    return BedrockLLM() if config.LLM_PROVIDER == "bedrock" else MockLLM()
