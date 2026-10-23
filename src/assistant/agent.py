"""The agent loop: send the question to the LLM, run any tools it asks for, repeat until it answers.

Every LLM call's tokens, cost and latency are recorded, and the conversation is saved for audit.
"""
import time
from typing import Callable

from src import config
from src.assistant import db
from src.assistant.tools import TOOL_SPECS, run_tool

SYSTEM_PROMPT = (
    "You are a customer retention assistant for a telecom company. "
    "Use the tools to look up the customer, get the churn probability from the ML model and suggest an offer. "
    "Never guess numbers: only use values returned by the tools. "
    "Answer in 2-3 short sentences: churn probability, main reasons, suggested action."
)


def cost_usd(input_tokens: int, output_tokens: int) -> float:
    return round(input_tokens / 1000 * config.PRICE_INPUT_PER_1K + output_tokens / 1000 * config.PRICE_OUTPUT_PER_1K, 8)


def ask(question: str, llm, predict_fn: Callable[[dict], float]) -> dict:
    messages = [{"role": "user", "content": [{"text": question}]}]
    usage, tool_calls, answer, status = [], [], None, "success"

    try:
        for _ in range(config.MAX_AGENT_STEPS):
            start = time.perf_counter()
            response = llm.converse(SYSTEM_PROMPT, messages, TOOL_SPECS)
            latency_ms = int((time.perf_counter() - start) * 1000)

            u = response["usage"]
            usage.append({
                "model_id": llm.model_id,
                "input_tokens": u["inputTokens"],
                "output_tokens": u["outputTokens"],
                "cost_usd": cost_usd(u["inputTokens"], u["outputTokens"]),
                "latency_ms": latency_ms,
            })

            message = response["output"]["message"]
            messages.append(message)

            if response["stopReason"] != "tool_use":
                answer = " ".join(b["text"] for b in message["content"] if "text" in b)
                break

            # Run every tool the LLM asked for and send the results back
            results = []
            for block in message["content"]:
                if "toolUse" in block:
                    call = block["toolUse"]
                    output = run_tool(call["name"], call["input"], predict_fn)
                    tool_calls.append({"name": call["name"], "input": call["input"], "output": output})
                    results.append({"toolResult": {
                        "toolUseId": call["toolUseId"],
                        "content": [{"json": output}],
                        "status": "error" if "error" in output else "success",
                    }})
            messages.append({"role": "user", "content": results})
        else:
            status = "error"
            answer = f"Stopped after {config.MAX_AGENT_STEPS} steps without a final answer."
    except Exception as exc:
        status = "error"
        answer = f"Assistant error: {exc}"

    conversation_id = db.save_conversation(question, answer, status, len(tool_calls), usage)
    return {
        "conversation_id": conversation_id,
        "answer": answer,
        "status": status,
        "tool_calls": tool_calls,
        "usage": {
            "llm_calls": len(usage),
            "input_tokens": sum(x["input_tokens"] for x in usage),
            "output_tokens": sum(x["output_tokens"] for x in usage),
            "cost_usd": round(sum(x["cost_usd"] for x in usage), 8),
        },
    }
