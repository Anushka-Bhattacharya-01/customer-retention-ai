"""Shared settings. Values can be overridden with environment variables."""
import os

DATA_PATH = os.getenv("DATA_PATH", "data/churn.csv")
MODEL_DIR = os.getenv("MODEL_DIR", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "model.joblib")
METRICS_PATH = os.path.join(MODEL_DIR, "metrics.json")

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
EXPERIMENT_NAME = os.getenv("EXPERIMENT_NAME", "churn-prediction")
REGISTERED_MODEL_NAME = os.getenv("REGISTERED_MODEL_NAME", "churn-model")

# Optional S3 locations (bucket created by Terraform). Empty = local files only.
# Training uploads to MODEL_S3_PREFIX; the API downloads from MODEL_S3_URI.
MODEL_S3_PREFIX = os.getenv("MODEL_S3_PREFIX", "")      # e.g. s3://<artifacts-bucket>/models
MODEL_S3_URI = os.getenv("MODEL_S3_URI", "")            # e.g. s3://<artifacts-bucket>/models/latest/model.joblib
METRICS_S3_URI = os.getenv("METRICS_S3_URI", "")

# Quality gate: a model below these scores is not promoted
MIN_ACCURACY = float(os.getenv("MIN_ACCURACY", "0.70"))
MIN_ROC_AUC = float(os.getenv("MIN_ROC_AUC", "0.75"))

NUMERIC_FEATURES = ["tenure", "monthly_charges", "total_charges", "support_calls", "paperless_billing"]
CATEGORICAL_FEATURES = ["contract", "internet_service"]
TARGET = "churn"

# ---- AI assistant (LLM) settings ----
# "mock" runs without AWS (for local runs and CI). "bedrock" calls Amazon Bedrock.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", os.getenv("AWS_REGION", "ap-south-1"))
# Price in USD per 1,000 tokens. Check the current Bedrock price for your model and region.
PRICE_INPUT_PER_1K = float(os.getenv("PRICE_INPUT_PER_1K", "0.00025"))
PRICE_OUTPUT_PER_1K = float(os.getenv("PRICE_OUTPUT_PER_1K", "0.00125"))
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "5"))     # stops endless tool-call loops
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "500"))

# Postgres in Docker/EKS, SQLite for local runs and tests
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///assistant.db")
