import os

import pytest
from fastapi.testclient import TestClient

from src import config

pytestmark = pytest.mark.skipif(not os.path.exists(config.MODEL_PATH), reason="train the model first")

SAMPLE = {
    "tenure": 3,
    "monthly_charges": 95.5,
    "total_charges": 286.5,
    "contract": "month-to-month",
    "internet_service": "fiber",
    "support_calls": 4,
    "paperless_billing": 1,
}


@pytest.fixture(scope="module")
def client():
    from src.app import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["model_loaded"] is True


def test_predict_returns_probability(client):
    r = client.post("/predict", json=SAMPLE)
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["churn_probability"] <= 1
    assert isinstance(body["will_churn"], bool)


def test_high_risk_customer_scores_higher_than_loyal_one(client):
    loyal = {**SAMPLE, "tenure": 70, "contract": "two-year", "support_calls": 0,
             "internet_service": "dsl", "monthly_charges": 40, "total_charges": 2800}
    risky = client.post("/predict", json=SAMPLE).json()["churn_probability"]
    safe = client.post("/predict", json=loyal).json()["churn_probability"]
    assert risky > safe


def test_invalid_input_rejected(client):
    r = client.post("/predict", json={**SAMPLE, "contract": "weekly"})
    assert r.status_code == 422


def test_metrics_endpoint(client):
    client.post("/predict", json=SAMPLE)
    r = client.get("/metrics")
    assert "predict_requests_total" in r.text


def test_assistant_endpoint(client):
    r = client.post("/assistant/ask", json={"question": "Will customer C0005 leave?"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success" and len(body["tool_calls"]) == 3

    usage = client.get("/assistant/usage").json()
    assert usage["llm_calls"] >= 4 and usage["llm_provider"] == "mock"
    assert "llm_tokens_total" in client.get("/metrics").text
