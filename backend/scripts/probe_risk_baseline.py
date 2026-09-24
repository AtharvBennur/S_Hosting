"""Probe risk distribution with pipeline fixes applied."""
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.ml.integration import integrate_files
from app.ml.pipeline import run_inference_pipeline, train_pipeline

paths = [Path(settings.demo_data_dir) / name for name in settings.default_demo_files]
unified, summary = integrate_files(paths)
print("projects:", len(unified), "matched_exp:", summary["matched_expenditure"])

unified["sanction_amount"] = pd.to_numeric(unified.get("sanction_amount"), errors="coerce")
unified["expenditure"] = pd.to_numeric(unified.get("expenditure"), errors="coerce")
unified["utilization_ratio"] = unified["expenditure"] / unified["sanction_amount"].replace(0, pd.NA)
unified["duplicate_flag"] = unified.duplicated(subset=["project_name", "state", "district"], keep=False)

# data quality candidates
candidates = {
    "missing_sanction": unified["sanction_amount"].isna() | (unified["sanction_amount"] <= 0),
    "missing_expenditure": unified["expenditure"].isna(),
    "no_completed_or_exp": ~unified["source_datasets"].apply(
        lambda s: "COMPLETED_WORKS" in s or "EXPENDITURE" in s
    ),
    "only_sanctioned": unified["source_datasets"].apply(lambda s: s == ["SANCTIONED_WORKS"]),
    "missing_model_inputs_proxy": unified["sanction_amount"].isna() | unified["expenditure"].isna(),
}
for name, mask in candidates.items():
    print(f"{name}: {int(mask.sum())}")

train_pipeline(unified)
results = run_inference_pipeline(unified)
print("\nRisk distribution (current engine):")
print(results["risk_level"].value_counts())
print("\nML anomaly flags:", int(results["ml_anomaly_flag"].sum()))
print("Normalized ML > 0.95:", int((results["normalized_ml_score"] > 0.95).sum()))
