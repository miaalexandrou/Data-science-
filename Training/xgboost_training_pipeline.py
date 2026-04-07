"""XGBoost property deal scorer skeleton.
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor


DEFAULT_DATA_PATH = Path(__file__).with_name("training_data.json")
DEFAULT_MODEL_PATH = Path(__file__).with_name("xgboost_deal_model.pkl")


def main() -> None:
    """Top-level entrypoint for training and saving the model."""
    args = parse_args()
    train_and_save_model(
        data_path=args.data_path,
        model_path=args.model_path,
    )


# -----------------------------
# Helper functions (below)
# -----------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train and save an XGBoost property value model.",
    )
    parser.add_argument(
        "--data-path",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to training JSON file.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Path to save/load trained model bundle.",
    )
    return parser.parse_args()


def train_and_save_model(data_path: Path, model_path: Path) -> dict[str, Any]:
    raw_df = load_training_json(data_path)
    model_df = prepare_training_dataframe(raw_df)

    X, y = split_features_target(model_df)

    expected_features = [c for c in model_df.columns if c != "price"]
    if set(X.columns) != set(expected_features):
        raise ValueError("Feature mismatch: not all non-target columns are being used.")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    model = build_training_pipeline(X_train)
    model.fit(X_train, y_train)
    evaluate_regression_model(model, X_test, y_test)

    bundle = {
        "model": model,
        "feature_columns": X.columns.tolist(),
    }
    save_model_bundle(bundle, model_path)
    print(f"\nSaved model bundle to: {model_path}")
    return bundle


def save_model_bundle(bundle: dict[str, Any], model_path: Path) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as f:
        pickle.dump(bundle, f)


def load_training_json(data_path: Path) -> pd.DataFrame:
    if not data_path.exists():
        raise FileNotFoundError(f"Training JSON not found: {data_path}")

    with data_path.open("r", encoding="utf-8") as f:
        rows: list[dict[str, Any]] = json.load(f)

    if not rows:
        raise ValueError("Training JSON is empty.")

    return pd.DataFrame(rows)


def prepare_training_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    required_columns = {"price"}

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in training data: {sorted(missing)}")

    cleaned = df.copy()
    cleaned = cleaned.drop(columns=["property_id"], errors="ignore")

    # Normalize typo variant and ensure only photovoltaic_panels is used as a feature.
    if "photovolta_panels" in cleaned.columns:
        if "photovoltaic_panels" not in cleaned.columns:
            cleaned["photovoltaic_panels"] = 0
        cleaned["photovoltaic_panels"] = (
            cleaned[["photovoltaic_panels", "photovolta_panels"]]
            .max(axis=1)
            .fillna(0)
        )
        cleaned = cleaned.drop(columns=["photovolta_panels"])

    cleaned = cleaned.dropna(subset=["price"])
    return cleaned


def split_features_target(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    target_col = "price"
    # Use every available column as a feature except the target.
    X = df.drop(columns=[target_col], errors="ignore")
    y = df[target_col]
    return X, y


def build_training_pipeline(sample_X: pd.DataFrame) -> Pipeline:
    categorical_cols = [
        col
        for col in ["city", "district", "property_type"]
        if col in sample_X.columns
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                categorical_cols,
            )
        ],
        remainder="passthrough",
    )

    regressor = XGBRegressor(
        n_estimators=400,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        objective="reg:squarederror",
    )

    return Pipeline(
        steps=[
            ("prep", preprocessor),
            ("xgb", regressor),
        ]
    )


def evaluate_regression_model(
    model: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> None:
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)
    print("\n=== Model Metrics ===")
    print(f"MAE: {mae:.2f}")
    print(f"R2:  {r2:.4f}")


if __name__ == "__main__":
    main()
