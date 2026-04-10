"""Train an XGBoost regressor for property prices and save it as a pickle bundle.

This script:
- loads the JSON training data
- tunes the XGBoost params with Optuna
- saves the trained pipeline + expected feature columns
- exports a few simple evaluation plots
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
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline
import optuna
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor


DEFAULT_DATA_PATH = Path(__file__).with_name("training_data.json")
DEFAULT_MODEL_PATH = Path(__file__).with_name("xgboost_deal_model.pkl")


def main() -> None:
    """Train the model and write the saved bundle to disk."""
    args = parse_args()
    train_and_save_model(
        data_path=args.data_path,
        model_path=args.model_path,
    )


# -----------------------------
# Helpers
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

    base_model = build_training_pipeline(X_train)

    def objective(trial):
        params = {
            "xgb__n_estimators": trial.suggest_int("xgb__n_estimators", 400, 2000, step=100),
            "xgb__learning_rate": trial.suggest_float("xgb__learning_rate", 0.005, 0.05, log=True),
            "xgb__max_depth": trial.suggest_int("xgb__max_depth", 6, 12),
            "xgb__subsample": trial.suggest_float("xgb__subsample", 0.5, 1.0),
            "xgb__colsample_bytree": trial.suggest_float("xgb__colsample_bytree", 0.5, 1.0),
            "xgb__gamma": trial.suggest_float("xgb__gamma", 1e-8, 1.0, log=True),
            "xgb__min_child_weight": trial.suggest_int("xgb__min_child_weight", 1, 10),
            "xgb__reg_alpha": trial.suggest_float("xgb__reg_alpha", 1e-8, 10.0, log=True),
            "xgb__reg_lambda": trial.suggest_float("xgb__reg_lambda", 1e-8, 10.0, log=True),
        }
        base_model.set_params(**params)

        # 3-fold CV: use MAE (lower is better)
        scores = cross_val_score(
            base_model, X_train, y_train, 
            scoring="neg_mean_absolute_error", 
            cv=3, 
            n_jobs=-1
        )
        return -scores.mean()

    print("\nStarting Hyperparameter Tuning with Optuna...")
    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=150)
    
    print(f"\nBest parameters found by Optuna: {study.best_params}")

    best_model = base_model.set_params(**study.best_params)
    print("Training final model on full training set with best parameters...")
    best_model.fit(X_train, y_train)

    evaluate_regression_model(best_model, X_test, y_test, X)

    bundle = {
        "model": best_model,
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
    cleaned = cleaned.drop(columns=["price_per_sqm"], errors="ignore")

    # Handle a typo variant so we only keep one solar-panels column.
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
    # Everything except the target is a feature.
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
    X_full: pd.DataFrame = None,
) -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns

    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)
    print("\n=== Model Metrics ===")
    print(f"MAE: {mae:.2f}")
    print(f"R2:  {r2:.4f}")

    # Plot: actual vs predicted
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x=y_test, y=predictions, alpha=0.6)
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
    plt.title("Actual vs Predicted Price")
    plt.xlabel("Actual Price")
    plt.ylabel("Predicted Price")
    plt.tight_layout()
    plt.savefig("actual_vs_predicted.png")
    plt.close()
    print("\nSaved 'actual_vs_predicted.png'")

    # Plot: residuals
    residuals = y_test - predictions
    plt.figure(figsize=(10, 6))
    sns.histplot(residuals, kde=True)
    plt.title("Residuals Distribution")
    plt.xlabel("Residual (Actual - Predicted)")
    plt.tight_layout()
    plt.savefig("residuals.png")
    plt.close()
    print("Saved 'residuals.png'")

    # Plot: feature importances (top 20)
    xgb_step = model.named_steps.get("xgb")
    prep_step = model.named_steps.get("prep")
    
    if xgb_step and hasattr(xgb_step, "feature_importances_"):
        importances = xgb_step.feature_importances_
        if hasattr(prep_step, "get_feature_names_out"):
            feature_names = prep_step.get_feature_names_out()
        elif X_full is not None:
            feature_names = X_full.columns
        else:
            feature_names = [f"Feature {i}" for i in range(len(importances))]
            
        # Make sure names and importances line up
        if len(feature_names) == len(importances):
            feat_imp = pd.Series(importances, index=feature_names).sort_values(ascending=False)
            plt.figure(figsize=(12, 8))
            sns.barplot(x=feat_imp.head(20).values, y=feat_imp.head(20).index)
            plt.title("Top 20 Feature Importances")
            plt.xlabel("Relative Importance")
            plt.tight_layout()
            plt.savefig("feature_importances.png")
            plt.close()
            print("Saved 'feature_importances.png'")


if __name__ == "__main__":
    main()
