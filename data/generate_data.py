"""Generate a synthetic customer churn dataset.

Synthetic data keeps the project self-contained (no download, no licence issues).
Churn probability depends on contract type, tenure, monthly charges and support
calls, so the model has real patterns to learn.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def generate(n_rows: int = 5000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    tenure = rng.integers(1, 73, n_rows)                       # months with company
    monthly_charges = rng.uniform(20, 120, n_rows).round(2)
    contract = rng.choice(["month-to-month", "one-year", "two-year"], n_rows, p=[0.55, 0.25, 0.20])
    internet = rng.choice(["dsl", "fiber", "none"], n_rows, p=[0.35, 0.45, 0.20])
    support_calls = rng.poisson(1.5, n_rows)
    paperless = rng.choice([0, 1], n_rows, p=[0.4, 0.6])

    # Log-odds of churn: built so the relationships are realistic
    logit = (
        -1.5
        + 1.6 * (contract == "month-to-month")
        - 1.2 * (contract == "two-year")
        - 0.04 * tenure
        + 0.02 * (monthly_charges - 70)
        + 0.45 * support_calls
        + 0.5 * (internet == "fiber")
        + 0.3 * paperless
    )
    prob = 1 / (1 + np.exp(-logit))
    churn = rng.binomial(1, prob)

    return pd.DataFrame({
        "tenure": tenure,
        "monthly_charges": monthly_charges,
        "total_charges": (tenure * monthly_charges).round(2),
        "contract": contract,
        "internet_service": internet,
        "support_calls": support_calls,
        "paperless_billing": paperless,
        "churn": churn,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--out", default="data/churn.csv")
    args = parser.parse_args()

    df = generate(args.rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows to {args.out} (churn rate {df.churn.mean():.1%})")
