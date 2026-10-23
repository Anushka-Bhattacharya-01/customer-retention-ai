"""Database tables for the assistant.

customers      -> customer records the assistant can look up (tool: get_customer)
conversations  -> every question and answer (audit trail)
llm_usage      -> tokens, cost and latency for every LLM call
"""
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, MetaData, String, Table, Text,
                        create_engine, func, insert, select)

from src import config

metadata = MetaData()

customers = Table(
    "customers", metadata,
    Column("customer_id", String(20), primary_key=True),
    Column("tenure", Integer, nullable=False),
    Column("monthly_charges", Float, nullable=False),
    Column("total_charges", Float, nullable=False),
    Column("contract", String(20), nullable=False),
    Column("internet_service", String(10), nullable=False),
    Column("support_calls", Integer, nullable=False),
    Column("paperless_billing", Integer, nullable=False),
)

conversations = Table(
    "conversations", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("question", Text, nullable=False),
    Column("answer", Text),
    Column("status", String(20), nullable=False),          # success / error
    Column("tool_calls", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

llm_usage = Table(
    "llm_usage", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("conversation_id", Integer, ForeignKey("conversations.id"), nullable=False),
    Column("model_id", String(100), nullable=False),
    Column("input_tokens", Integer, nullable=False),
    Column("output_tokens", Integer, nullable=False),
    Column("cost_usd", Float, nullable=False),
    Column("latency_ms", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    return _engine


def now():
    return datetime.now(timezone.utc)


def init_db(seed_rows: int = 50) -> None:
    """Create tables and load sample customers (C0001 ... C0050) if the table is empty."""
    metadata.create_all(engine())
    with engine().begin() as conn:
        if conn.execute(select(func.count()).select_from(customers)).scalar():
            return
        from data.generate_data import generate
        df = generate(seed_rows, seed=7).drop(columns=["churn"])
        df.insert(0, "customer_id", [f"C{i:04d}" for i in range(1, len(df) + 1)])
        conn.execute(insert(customers), df.to_dict(orient="records"))


def get_customer(customer_id: str) -> dict | None:
    with engine().connect() as conn:
        row = conn.execute(select(customers).where(customers.c.customer_id == customer_id)).mappings().first()
        return dict(row) if row else None


def save_conversation(question: str, answer: str, status: str, tool_calls: int, usage: list[dict]) -> int:
    with engine().begin() as conn:
        conv_id = conn.execute(insert(conversations).values(
            question=question, answer=answer, status=status, tool_calls=tool_calls, created_at=now()
        )).inserted_primary_key[0]
        for u in usage:
            conn.execute(insert(llm_usage).values(conversation_id=conv_id, created_at=now(), **u))
        return conv_id


def usage_summary() -> dict:
    with engine().connect() as conn:
        row = conn.execute(select(
            func.count(func.distinct(llm_usage.c.conversation_id)),
            func.count(),
            func.coalesce(func.sum(llm_usage.c.input_tokens), 0),
            func.coalesce(func.sum(llm_usage.c.output_tokens), 0),
            func.coalesce(func.sum(llm_usage.c.cost_usd), 0.0),
            func.coalesce(func.avg(llm_usage.c.latency_ms), 0.0),
        )).first()
    return {
        "conversations": row[0],
        "llm_calls": row[1],
        "input_tokens": int(row[2]),
        "output_tokens": int(row[3]),
        "total_cost_usd": round(float(row[4]), 6),
        "avg_latency_ms": round(float(row[5]), 1),
    }
