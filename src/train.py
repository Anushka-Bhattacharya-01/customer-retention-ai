"""Train the churn model, track it in MLflow and apply a quality gate.

Steps:
1. Load data and split into train (80%) and test (20%)
2. Build a scikit-learn pipeline (preprocessing + logistic regression)
3. Log parameters, metrics and the model to MLflow
4. If metrics pass the quality gate -> register the model and save it for the API
   Otherwise -> exit with code 1 so the CI pipeline stops
"""
import argparse
import json
import os
import sys

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src import config, s3_utils


def build_pipeline(c: float) -> Pipeline:
    # Numbers are scaled, text columns (contract, internet_service) are one-hot encoded
    preprocess = ColumnTransformer([
        ("num", StandardScaler(), config.NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), config.CATEGORICAL_FEATURES),
    ])
    model = LogisticRegression(C=c, max_iter=1000)
    return Pipeline([("preprocess", preprocess), ("model", model)])


def evaluate(pipeline: Pipeline, X_test, y_test) -> dict:
    preds = pipeline.predict(X_test)
    probs = pipeline.predict_proba(X_test)[:, 1]
    return {
        "accuracy": round(accuracy_score(y_test, preds), 4),
        "f1": round(f1_score(y_test, preds), 4),
        "roc_auc": round(roc_auc_score(y_test, probs), 4),
    }


def passes_quality_gate(metrics: dict) -> bool:
    return metrics["accuracy"] >= config.MIN_ACCURACY and metrics["roc_auc"] >= config.MIN_ROC_AUC


def main(c: float) -> int:
    df = pd.read_csv(config.DATA_PATH)
    X = df[config.NUMERIC_FEATURES + config.CATEGORICAL_FEATURES]
    y = df[config.TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(config.EXPERIMENT_NAME)

    with mlflow.start_run() as run:
        pipeline = build_pipeline(c)
        pipeline.fit(X_train, y_train)
        metrics = evaluate(pipeline, X_test, y_test)

        mlflow.log_params({"model": "logistic_regression", "C": c, "train_rows": len(X_train)})
        mlflow.log_metrics(metrics)
        print(f"Run {run.info.run_id}: {metrics}")

        if not passes_quality_gate(metrics):
            mlflow.set_tag("quality_gate", "failed")
            print(f"Quality gate FAILED (need accuracy >= {config.MIN_ACCURACY}, roc_auc >= {config.MIN_ROC_AUC})")
            return 1

        mlflow.set_tag("quality_gate", "passed")
        mlflow.sklearn.log_model(pipeline, name="model", registered_model_name=config.REGISTERED_MODEL_NAME)

        # Save a local copy for the API
        os.makedirs(config.MODEL_DIR, exist_ok=True)
        joblib.dump(pipeline, config.MODEL_PATH)
        with open(config.METRICS_PATH, "w") as f:
            json.dump({**metrics, "run_id": run.info.run_id, "C": c}, f, indent=2)

        # Optional: upload to S3 (bucket created by Terraform)
        if config.MODEL_S3_PREFIX:
            for folder in (run.info.run_id, "latest"):
                s3_utils.upload(config.MODEL_PATH, f"{config.MODEL_S3_PREFIX}/{folder}/model.joblib")
                s3_utils.upload(config.METRICS_PATH, f"{config.MODEL_S3_PREFIX}/{folder}/metrics.json")
            print(f"Uploaded model to {config.MODEL_S3_PREFIX}/latest/")

        print(f"Quality gate PASSED. Model registered as '{config.REGISTERED_MODEL_NAME}'")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--C", type=float, default=1.0, help="Regularisation strength (smaller = simpler model)")
    args = parser.parse_args()
    sys.exit(main(args.C))
