#!/usr/bin/env python3
"""
Evaluate inference results against ground truth.
Adapted from Dude-Coders for Helio Yajna pipeline.

Ground truth assumption:
  - Samples 1-2500  → has_solar = True
  - Samples 2501+   → has_solar = False
"""
import json
import argparse
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix


def evaluate_results(results_path="output_data/prediction_files/test/results.json"):
    print(f"Loading results from: {results_path}")
    with open(results_path) as f:
        results = json.load(f)

    df = pd.DataFrame(results)
    df["sample_id_int"] = df["sample_id"].apply(
        lambda x: int(float(str(x).replace(".0", "")))
    )

    # Ground truth: first 2500 have solar
    df["gt_has_solar"] = df["sample_id_int"].apply(lambda x: x <= 2500)

    y_true = df["gt_has_solar"].values
    y_pred = df["has_solar"].values

    print("=" * 60)
    print("CLASSIFICATION REPORT")
    print("=" * 60)
    print(classification_report(y_true, y_pred,
                                 target_names=["No Solar", "Solar"],
                                 digits=4))

    print("=" * 60)
    print("CONFUSION MATRIX")
    print("=" * 60)
    cm = confusion_matrix(y_true, y_pred)
    print(f"                  Predicted")
    print(f"                  No Solar  Solar")
    print(f"Actual No Solar    {cm[0][0]:5d}    {cm[0][1]:5d}")
    print(f"Actual Solar       {cm[1][0]:5d}    {cm[1][1]:5d}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Helio inference results")
    parser.add_argument("--results", type=str,
                        default="output_data/prediction_files/test/results.json",
                        help="Path to results.json")
    args = parser.parse_args()
    evaluate_results(args.results)
