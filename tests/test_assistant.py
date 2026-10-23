"""Tests for the AI assistant: tools, agent loop, usage logging. Uses the mock LLM."""
from src.assistant import agent, db
from src.assistant.llm import MockLLM
from src.assistant.tools import run_tool, suggest_retention_offer


def fake_predict(features: dict) -> float:
    # High risk for month-to-month, low risk otherwise (keeps the test independent of the trained model)
    return 0.85 if features["contract"] == "month-to-month" else 0.15


def setup_module():
    db.init_db()


def test_customers_seeded():
    assert db.get_customer("C0001") is not None
    assert db.get_customer("C9999") is None


def test_offer_rules():
    assert suggest_retention_offer(0.9, "month-to-month")["priority"] == "high"
    assert suggest_retention_offer(0.5, "one-year")["priority"] == "medium"
    assert suggest_retention_offer(0.1, "two-year")["priority"] == "low"


def test_unknown_customer_returns_error_not_exception():
    assert "error" in run_tool("predict_churn", {"customer_id": "C9999"}, fake_predict)


def test_agent_calls_tools_in_order_and_answers():
    result = agent.ask("Will customer C0003 leave? What should we offer?", MockLLM(), fake_predict)
    assert result["status"] == "success"
    assert [t["name"] for t in result["tool_calls"]] == ["get_customer", "predict_churn", "suggest_retention_offer"]
    assert "C0003" in result["answer"] and "%" in result["answer"]
    assert result["usage"]["llm_calls"] == 4            # 3 tool-call turns + 1 final answer
    assert result["usage"]["cost_usd"] > 0


def test_agent_asks_for_id_when_missing():
    result = agent.ask("Which customers are happy?", MockLLM(), fake_predict)
    assert "customer ID" in result["answer"]
    assert result["tool_calls"] == []


def test_usage_is_recorded():
    before = db.usage_summary()["llm_calls"]
    agent.ask("Check C0010 please", MockLLM(), fake_predict)
    after = db.usage_summary()
    assert after["llm_calls"] == before + 4
    assert after["total_cost_usd"] > 0


def test_step_limit_stops_runaway_loop():
    class LoopingLLM(MockLLM):
        def converse(self, system, messages, tools):
            return self._tool("get_customer", {"customer_id": "C0001"}, messages)

    result = agent.ask("C0001", LoopingLLM(), fake_predict)
    assert result["status"] == "error"
    assert "Stopped after" in result["answer"]
