import pandas as pd

from data.generate_data import generate
from src import config
from src.train import build_pipeline, evaluate, passes_quality_gate


def test_generated_data_has_expected_columns():
    df = generate(500)
    expected = set(config.NUMERIC_FEATURES + config.CATEGORICAL_FEATURES + [config.TARGET])
    assert expected.issubset(df.columns)
    assert df.isnull().sum().sum() == 0
    assert 0.1 < df[config.TARGET].mean() < 0.6


def test_pipeline_trains_and_beats_quality_gate():
    df = generate(3000)
    X = df[config.NUMERIC_FEATURES + config.CATEGORICAL_FEATURES]
    y = df[config.TARGET]
    pipe = build_pipeline(1.0)
    pipe.fit(X[:2400], y[:2400])
    metrics = evaluate(pipe, X[2400:], y[2400:])
    assert passes_quality_gate(metrics), metrics


def test_quality_gate_rejects_weak_model():
    assert not passes_quality_gate({"accuracy": 0.5, "roc_auc": 0.5, "f1": 0.3})


def test_s3_uri_parsing():
    import pytest
    from src.s3_utils import _split
    assert _split("s3://my-bucket/models/latest/model.joblib") == ("my-bucket", "models/latest/model.joblib")
    with pytest.raises(ValueError):
        _split("https://example.com/model.joblib")
