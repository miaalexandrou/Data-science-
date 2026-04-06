"""Simple runner script to score one property with the saved XGBoost model.

Skeleton style:
- main workflow at the top
- helper functions at the bottom
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np


DEFAULT_MODEL_PATH = Path(__file__).with_name("xgboost_deal_model.pkl")
DEFAULT_INPUT_JSON_PATH = Path(__file__).with_name("predict_input.json")


def main() -> None:
    args = parse_args()

    user_property = load_input_json(args.input_json_path)
    bundle = load_model_bundle(args.model_path)
    result = score_property_deal(
        model=bundle["model"],
        feature_columns=bundle["feature_columns"],
        user_property=user_property,
        decision_threshold=args.decision_threshold,
    )

    print_result(result)

    if args.output_json:
        print(json.dumps(result, indent=2))


# -----------------------------
# Helper functions (below)
# -----------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call saved XGBoost model with input JSON and return deal score.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Path to saved model bundle (.pkl).",
    )
    parser.add_argument(
        "--input-json-path",
        type=Path,
        default=DEFAULT_INPUT_JSON_PATH,
        help="Path to input JSON (single property object).",
    )
    parser.add_argument(
        "--decision-threshold",
        type=float,
        default=0.5,
        help="Threshold for True/False good deal decision.",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Also print full result as JSON.",
    )
    return parser.parse_args()


def load_input_json(input_json_path: Path) -> dict[str, Any]:
    if not input_json_path.exists():
        raise FileNotFoundError(f"Input JSON not found: {input_json_path}")

    with input_json_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ValueError("Input JSON must be a single object.")

    return payload


def load_model_bundle(model_path: Path) -> dict[str, Any]:
    if not model_path.exists():
        raise FileNotFoundError(f"Saved model not found: {model_path}")

    with model_path.open("rb") as f:
        bundle = pickle.load(f)

    if "model" not in bundle or "feature_columns" not in bundle:
        raise ValueError("Invalid model bundle format.")

    return bundle


def score_property_deal(
    model: Any,
    feature_columns: list[str],
    user_property: dict[str, Any],
    decision_threshold: float = 0.5,
) -> dict[str, Any]:
    user_df = normalize_user_input(user_property, feature_columns)

    asking_price = float(user_df["price"].iloc[0])
    X_user = user_df.drop(columns=["price"], errors="ignore")

    predicted_fair_price = float(model.predict(X_user)[0])
    relative_gap = (predicted_fair_price - asking_price) / max(predicted_fair_price, 1.0)
    deal_mark = float(1.0 / (1.0 + np.exp(-6.0 * relative_gap)))

    return {
        "asking_price": asking_price,
        "predicted_fair_price": predicted_fair_price,
        "deal_mark": deal_mark,
        "is_good_deal": deal_mark >= decision_threshold,
    }


def normalize_user_input(user_property: dict[str, Any], feature_columns: list[str]) -> pd.DataFrame:
    normalized: dict[str, Any] = {col: 0 for col in feature_columns}
    normalized["price"] = user_property.get("price", 0)

    for key, value in user_property.items():
        if key in normalized:
            normalized[key] = value

    return pd.DataFrame([normalized])


def print_result(result: dict[str, Any]) -> None:
    print("\n=== Prediction Result ===")
    print(f"Deal mark (0-1): {result['deal_mark']:.4f}")
    print(f"Good deal:       {result['is_good_deal']}")
    print(f"Asking price:    {result['asking_price']:.2f}")
    print(f"Fair price:      {result['predicted_fair_price']:.2f}")


if __name__ == "__main__":
    main()
