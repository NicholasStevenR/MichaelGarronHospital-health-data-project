"""
ED Patient Flow — Value Stream Mapping & Cycle-Time Analysis
Author: Nicholas Steven
Target Role: Analyst — Michael Garron Hospital / TEHN
Repo: github.com/nicholasstevenr/MichaelGarronHospital-health-data-project

Quantifies process waste across 7 ED steps using VSM methodology:
cycle time, wait time, value-add ratio, bottleneck identification,
CTAS-stratified LOS, and to-be scenario modelling.
"""

import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

# ── Constants ─────────────────────────────────────────────────────────────────

ED_STEPS = [
    "triage",
    "registration",
    "waiting_room",
    "initial_assessment",
    "investigations",      # labs/imaging
    "physician_review",
    "disposition",
]

# Value-add classification per VSM: only direct care steps are value-add
VALUE_ADD_STEPS = {"initial_assessment", "investigations", "physician_review"}

CTAS_LABELS = {1: "Resuscitation", 2: "Emergent", 3: "Urgent",
               4: "Less-Urgent", 5: "Non-Urgent"}


# ── Load ──────────────────────────────────────────────────────────────────────

def load(ed_path: str) -> pd.DataFrame:
    df = pd.read_csv(ed_path, parse_dates=["arrival_ts", "departure_ts"])
    for step in ED_STEPS:
        df[f"{step}_start_ts"] = pd.to_datetime(df[f"{step}_start_ts"])
        df[f"{step}_end_ts"]   = pd.to_datetime(df[f"{step}_end_ts"])
    print(f"Loaded {len(df):,} ED visits")
    return df


# ── 1. Step-Level Cycle Time & Wait Time ─────────────────────────────────────

def compute_step_times(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each step: cycle_time = end - start (active processing).
    Wait time = gap between previous step end and this step start.
    """
    records = []
    for i, step in enumerate(ED_STEPS):
        ct = (df[f"{step}_end_ts"] - df[f"{step}_start_ts"]).dt.total_seconds() / 60
        if i == 0:
            wt = pd.Series(np.zeros(len(df)), index=df.index)  # no wait before triage
        else:
            prev = ED_STEPS[i - 1]
            wt = (df[f"{step}_start_ts"] - df[f"{prev}_end_ts"]).dt.total_seconds() / 60
            wt = wt.clip(lower=0)

        records.append({
            "step": step,
            "is_value_add": step in VALUE_ADD_STEPS,
            "median_cycle_min":  round(ct.median(), 1),
            "p90_cycle_min":     round(ct.quantile(0.90), 1),
            "median_wait_min":   round(wt.median(), 1),
            "p90_wait_min":      round(wt.quantile(0.90), 1),
            "n_encounters":      len(ct.dropna()),
        })
    return pd.DataFrame(records)


# ── 2. Value-Add vs Non-Value-Add Ratio ───────────────────────────────────────

def value_add_ratio(step_summary: pd.DataFrame) -> dict:
    va  = step_summary[step_summary["is_value_add"]]["median_cycle_min"].sum()
    nva = step_summary[~step_summary["is_value_add"]]["median_cycle_min"].sum()
    total_wait = step_summary["median_wait_min"].sum()
    total_time = va + nva + total_wait

    return {
        "value_add_min":     round(va, 1),
        "non_value_add_min": round(nva, 1),
        "total_wait_min":    round(total_wait, 1),
        "total_ed_time_min": round(total_time, 1),
        "va_ratio_pct":      round(va / total_time * 100, 1),
        "wait_ratio_pct":    round(total_wait / total_time * 100, 1),
    }


# ── 3. CTAS-Stratified LOS & Bottleneck Analysis ─────────────────────────────

def ctas_los_analysis(df: pd.DataFrame) -> pd.DataFrame:
    df["total_los_min"] = (
        df["departure_ts"] - df["arrival_ts"]
    ).dt.total_seconds() / 60

    ctas_summary = (
        df.groupby(["ctas_level", "disposition"])
        .agg(
            n                 = ("total_los_min", "count"),
            median_los_min    = ("total_los_min", "median"),
            p90_los_min       = ("total_los_min", lambda x: x.quantile(0.90)),
            mean_los_min      = ("total_los_min", "mean"),
        )
        .reset_index()
        .round(1)
    )
    ctas_summary["ctas_label"] = ctas_summary["ctas_level"].map(CTAS_LABELS)
    return ctas_summary


def bottleneck_detection(step_summary: pd.DataFrame) -> pd.DataFrame:
    """
    Bottleneck = steps with wait_time > 1.5× median wait across all steps
    and/or P90/P50 ratio > 3 (high variability = unstable capacity).
    """
    median_wait = step_summary["median_wait_min"].median()
    step_summary["wait_vs_median_ratio"] = (
        step_summary["median_wait_min"] / median_wait
    ).round(2)
    step_summary["p90_p50_ratio"] = (
        step_summary["p90_cycle_min"] / step_summary["median_cycle_min"].replace(0, np.nan)
    ).round(2)
    step_summary["is_bottleneck"] = (
        (step_summary["wait_vs_median_ratio"] > 1.5) |
        (step_summary["p90_p50_ratio"] > 3.0)
    )
    return step_summary


# ── 4. Waste Quantification (VSM Categories) ──────────────────────────────────

def quantify_waste(df: pd.DataFrame, step_summary: pd.DataFrame) -> pd.DataFrame:
    """
    VSM waste categories:
    - Waiting: idle time between steps
    - Over-processing: repeat triage reclassifications (triage_reclassified flag)
    - Defects: orders placed then cancelled (order_cancelled flag)
    """
    waste = []

    # Waiting waste — total wait per visit
    total_wait = step_summary["median_wait_min"].sum()
    waste.append({"waste_category": "Waiting", "metric": "Median total inter-step wait (min)",
                  "value": round(total_wait, 1), "pct_of_total_los": None})

    # Over-processing — triage reclassification rate
    if "triage_reclassified" in df.columns:
        reclassify_rate = df["triage_reclassified"].mean() * 100
        reclassify_n    = df["triage_reclassified"].sum()
        waste.append({"waste_category": "Over-processing",
                      "metric": "Triage reclassification rate (%)",
                      "value": round(reclassify_rate, 1),
                      "pct_of_total_los": None})
        waste.append({"waste_category": "Over-processing",
                      "metric": "Triage reclassification count",
                      "value": int(reclassify_n),
                      "pct_of_total_los": None})

    # Defects — cancelled orders
    if "orders_cancelled" in df.columns:
        cancel_rate = (df["orders_cancelled"] > 0).mean() * 100
        waste.append({"waste_category": "Defects",
                      "metric": "Encounters with ≥1 cancelled order (%)",
                      "value": round(cancel_rate, 1),
                      "pct_of_total_los": None})

    return pd.DataFrame(waste)


# ── 5. To-Be Scenario Modelling ───────────────────────────────────────────────

def model_improvements(df: pd.DataFrame) -> pd.DataFrame:
    """
    Three to-be improvements from VSM future-state design:
    1. Fast-track stream: CTAS 4-5 bypass waiting room → investigations
    2. Nurse-initiated orders: reduce physician_review wait by 28 min
    3. Bed assignment automation: reduce disposition wait by 15 min
    """
    df["total_los_min"] = (
        df["departure_ts"] - df["arrival_ts"]
    ).dt.total_seconds() / 60

    scenarios = []

    # Baseline
    baseline_median = df["total_los_min"].median()
    ctas45_median   = df[df["ctas_level"].isin([4, 5])]["total_los_min"].median()
    scenarios.append({"scenario": "As-Is (Baseline)",
                      "all_patients_median_los_min": round(baseline_median, 1),
                      "ctas45_median_los_min": round(ctas45_median, 1),
                      "improvement_vs_baseline_pct": 0.0})

    # Scenario 1: Fast-track CTAS 4-5 (41% LOS reduction for CTAS 4-5)
    fast_track_reduction = 0.41
    ctas45_mask = df["ctas_level"].isin([4, 5])
    los_scenario1 = df["total_los_min"].copy()
    los_scenario1[ctas45_mask] *= (1 - fast_track_reduction)
    scenarios.append({"scenario": "1 — Fast-track CTAS 4-5",
                      "all_patients_median_los_min": round(los_scenario1.median(), 1),
                      "ctas45_median_los_min": round(los_scenario1[ctas45_mask].median(), 1),
                      "improvement_vs_baseline_pct": round(
                          (1 - los_scenario1.median() / baseline_median) * 100, 1)})

    # Scenario 2: Fast-track + nurse-initiated orders (28 min saved for common complaints)
    # Assume 60% of visits have common presenting complaints eligible
    los_scenario2 = los_scenario1.copy()
    eligible = df["total_los_min"] > 120  # proxy for non-resus visits
    los_scenario2[eligible] = (los_scenario2[eligible] - 28).clip(lower=30)
    scenarios.append({"scenario": "2 — + Nurse-initiated orders",
                      "all_patients_median_los_min": round(los_scenario2.median(), 1),
                      "ctas45_median_los_min": round(los_scenario2[ctas45_mask].median(), 1),
                      "improvement_vs_baseline_pct": round(
                          (1 - los_scenario2.median() / baseline_median) * 100, 1)})

    # Scenario 3: All three improvements including bed assignment automation
    los_scenario3 = los_scenario2.copy()
    admitted_proxy = df.get("admitted", pd.Series(np.zeros(len(df)), dtype=bool)).astype(bool)
    los_scenario3[admitted_proxy] = (los_scenario3[admitted_proxy] - 15).clip(lower=30)
    scenarios.append({"scenario": "3 — + Bed assignment automation",
                      "all_patients_median_los_min": round(los_scenario3.median(), 1),
                      "ctas45_median_los_min": round(los_scenario3[ctas45_mask].median(), 1),
                      "improvement_vs_baseline_pct": round(
                          (1 - los_scenario3.median() / baseline_median) * 100, 1)})

    return pd.DataFrame(scenarios)


# ── Export ────────────────────────────────────────────────────────────────────

def export_all(results: dict, outdir: str = "output") -> None:
    import os; os.makedirs(outdir, exist_ok=True)
    for name, data in results.items():
        if isinstance(data, pd.DataFrame):
            path = f"{outdir}/{name}.csv"
            data.to_csv(path, index=False)
            print(f"  Exported {len(data)} rows → {path}")
        elif isinstance(data, dict):
            path = f"{outdir}/{name}.csv"
            pd.DataFrame([data]).to_csv(path, index=False)
            print(f"  Exported summary → {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df = load("data/ed_visits_synthetic.csv")

    step_times    = compute_step_times(df)
    step_times    = bottleneck_detection(step_times)
    va_summary    = value_add_ratio(step_times)
    ctas_los      = ctas_los_analysis(df)
    waste_tbl     = quantify_waste(df, step_times)
    scenarios_tbl = model_improvements(df)

    print("\n── Step-Level Summary ──")
    print(step_times[["step","median_cycle_min","median_wait_min","is_bottleneck"]].to_string(index=False))

    print(f"\n── Value-Add Ratio ──")
    print(f"  Value-add: {va_summary['value_add_min']} min ({va_summary['va_ratio_pct']}%)")
    print(f"  Wait time: {va_summary['total_wait_min']} min ({va_summary['wait_ratio_pct']}%)")
    print(f"  Total ED time (median): {va_summary['total_ed_time_min']} min")

    print("\n── Improvement Scenarios ──")
    print(scenarios_tbl.to_string(index=False))

    export_all({
        "vsm_step_times":         step_times,
        "value_add_summary":      va_summary,
        "ctas_los_analysis":      ctas_los,
        "waste_quantification":   waste_tbl,
        "improvement_scenarios":  scenarios_tbl,
    })
