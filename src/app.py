"""FastAPI service: churn ML model + AI retention assistant.

Endpoints:
  GET  /health            -> liveness/readiness check (used by Docker/Kubernetes)
  GET  /model             -> which model version is loaded and its metrics
  POST /predict           -> churn prediction for one customer (ML model)
  POST /assistant/ask     -> ask the AI assistant in plain English (LLM + tool calling)
  GET  /assistant/usage   -> total tokens, cost and latency from the llm_usage table
  GET  /metrics           -> Prometheus metrics
"""
import json
import os
import time
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

from src import config, s3_utils
from src.assistant import agent, db
from src.assistant.llm import get_llm

app = FastAPI(title="Customer Retention AI API", version="2.0.0")

REQUESTS = Counter("predict_requests_total", "Total prediction requests", ["status"])
LATENCY = Histogram("predict_latency_seconds", "Prediction latency in seconds")
PREDICTIONS = Counter("predictions_total", "Predictions by outcome", ["outcome"])
ASSISTANT_REQUESTS = Counter("assistant_requests_total", "Assistant requests", ["status"])
LLM_TOKENS = Counter("llm_tokens_total", "LLM tokens used", ["type"])
LLM_COST = Counter("llm_cost_usd_total", "LLM cost in USD")
ASSISTANT_LATENCY = Histogram("assistant_latency_seconds", "End-to-end assistant latency",
                              buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30))

_model = None
_model_info: dict = {}
_llm = None


class Question(BaseModel):
    question: str = Field(..., min_length=3, max_length=500, examples=["Will customer C0007 leave? What should we offer?"])


class Customer(BaseModel):
    tenure: int = Field(..., ge=0, le=100, description="Months with the company")
    monthly_charges: float = Field(..., ge=0)
    total_charges: float = Field(..., ge=0)
    contract: Literal["month-to-month", "one-year", "two-year"]
    internet_service: Literal["dsl", "fiber", "none"]
    support_calls: int = Field(..., ge=0)
    paperless_billing: Literal[0, 1]


def load_model():
    global _model, _model_info
    if config.MODEL_S3_URI:
        # On EKS the pod reads the model from S3 using its IRSA role
        os.makedirs(config.MODEL_DIR, exist_ok=True)
        s3_utils.download(config.MODEL_S3_URI, config.MODEL_PATH)
        if config.METRICS_S3_URI:
            s3_utils.download(config.METRICS_S3_URI, config.METRICS_PATH)
    if not os.path.exists(config.MODEL_PATH):
        raise RuntimeError(f"Model not found at {config.MODEL_PATH}. Run training first.")
    _model = joblib.load(config.MODEL_PATH)
    if os.path.exists(config.METRICS_PATH):
        with open(config.METRICS_PATH) as f:
            _model_info = json.load(f)


def predict_probability(features: dict) -> float:
    return float(_model.predict_proba(pd.DataFrame([features]))[0][1])


@app.on_event("startup")
def startup():
    global _llm
    load_model()
    db.init_db()
    _llm = get_llm()


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None, "llm_provider": config.LLM_PROVIDER}


@app.get("/model")
def model_info():
    return _model_info


@app.post("/predict")
def predict(customer: Customer):
    start = time.perf_counter()
    try:
        df = pd.DataFrame([customer.model_dump()])
        prob = float(_model.predict_proba(df)[0][1])
        will_churn = prob >= 0.5
        PREDICTIONS.labels(outcome="churn" if will_churn else "stay").inc()
        REQUESTS.labels(status="success").inc()
        return {"churn_probability": round(prob, 4), "will_churn": will_churn}
    except Exception as exc:  # keep the API up, record the failure
        REQUESTS.labels(status="error").inc()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        LATENCY.observe(time.perf_counter() - start)


@app.post("/assistant/ask")
def assistant_ask(body: Question):
    start = time.perf_counter()
    result = agent.ask(body.question, _llm, predict_probability)
    ASSISTANT_LATENCY.observe(time.perf_counter() - start)
    ASSISTANT_REQUESTS.labels(status=result["status"]).inc()
    LLM_TOKENS.labels(type="input").inc(result["usage"]["input_tokens"])
    LLM_TOKENS.labels(type="output").inc(result["usage"]["output_tokens"])
    LLM_COST.inc(result["usage"]["cost_usd"])
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result)
    return result


@app.get("/assistant/usage")
def assistant_usage():
    return {"llm_provider": config.LLM_PROVIDER, "model_id": _llm.model_id, **db.usage_summary()}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
