"""
Remove unwanted fields from a JSON file.

Usage examples:
python src/DataCleaning/remove_json_fields.py \
  --file data/xgboost_training_data_final.json

python src/DataCleaning/remove_json_fields.py \
  --file data/xgboost_training_data_final.json \
  --output data/xgboost_training_data_final.cleaned.json
"""

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_FIELDS_TO_REMOVE = {
    "parking",
    "condition",
    "furnishing",
    "included",
    "air_conditioning",
    "energy_efficiency",
    "description",
}


def remove_fields_recursive(value: Any, fields_to_remove: set[str]) -> Any:
    """Recursively remove target keys from dicts in JSON-like structures."""
    if isinstance(value, dict):
        return {
            key: remove_fields_recursive(child, fields_to_remove)
            for key, child in value.items()
            if key not in fields_to_remove
        }

    if isinstance(value, list):
        return [remove_fields_recursive(item, fields_to_remove) for item in value]

    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove fields from a JSON file.")
    parser.add_argument(
        "--file",
        default=None,
        help="Path to input JSON file. If omitted, tries common project paths.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output path. If omitted, writes to <input>.cleaned.json.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite input file (disabled by default).",
    )
    parser.add_argument(
        "--fields",
        nargs="+",
        default=sorted(DEFAULT_FIELDS_TO_REMOVE),
        help="Field names to remove. Defaults to project target fields.",
    )

    args = parser.parse_args()

    if args.file:
        input_path = Path(args.file)
    else:
        cwd = Path.cwd()
        script_dir = Path(__file__).resolve().parent
        candidates = [
            cwd / "xgboost_training_data_final.json",
            cwd / "data" / "xgboost_training_data_final.json",
            script_dir / "xgboost_training_data_final.json",
            script_dir.parent.parent / "data" / "xgboost_training_data_final.json",
        ]
        input_path = next((p for p in candidates if p.exists()), candidates[-1])

    if args.in_place:
        output_path = input_path
    elif args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_name(f"{input_path.stem}.cleaned{input_path.suffix}")
    fields_to_remove = set(args.fields)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path == input_path and not args.in_place:
        raise ValueError("Refusing to overwrite input without --in-place.")

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned = remove_fields_recursive(data, fields_to_remove)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Updated JSON written to: {output_path}")
    print(f"Removed fields: {', '.join(sorted(fields_to_remove))}")


if __name__ == "__main__":
    main()
