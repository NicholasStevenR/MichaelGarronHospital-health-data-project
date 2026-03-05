"""
TEHN Community Health Indicator Dashboard — Catchment Area Analysis
Author: Nicholas Steven
Target Role: Analyst — Michael Garron Hospital / TEHN
Repo: github.com/nicholasstevenr/MichaelGarronHospital-health-data-project

Computes 5 community health indicators at FSA level for TEHN catchment,
overlaid with Neighbourhood Equity Index quintiles and 3-year trend analysis.
"""

import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

# ── TEHN Catchment FSAs ───────────────────────────────────────────────────────

TEHN_FSAS = ["M4E", "M4J", "M4K", "M4L", "M4M", "M4N", "M4P", "M4C", "M4B"]

ACSC_CODES = {
    "J45", "J46",          # Asthma
    "E10", "E11", "E14",   # Diabetes
    "I50",                 # Heart failure
    "J22", "J06", "J02",   # Resp infections
    "N10", "N12",          # UTI
}

MH_CODES = {"F20", "F23", "F32", "F33", "F41", "F43", "X60", "X84"}

SOCIAL_FLAGS = [
    "flag_housing_instability",
    "flag_food_insecurity",
    "flag_language_barrier",
    "flag_transportation_barrier",
]


# ── Load ──────────────────────────────────────────────────────────────────────

def load(ed_path: str, hosp_path: str, pop_path: str, nei_path: str):
    ed   = pd.read_csv(ed_path,   parse_dates=["arrival_ts", "departure_ts", "admission_ts"])
    hosp = pd.read_csv(hosp_path, parse_dates=["admission_date", "discharge_date"])
    pop  = pd.read_csv(pop_path)   # columns: fsa, fiscal_year, population
    nei  = pd.read_csv(nei_path)   # columns: fsa, nei_quintile (1=most equity, 5=least)

    # Filter to TEHN catchment
    ed   = ed[ed["patient_fsa"].isin(TEHN_FSAS)].copy()
    hosp = hosp[hosp["patient_fsa"].isin(TEHN_FSAS)].copy()
    pop  = pop[pop["fsa"].isin(TEHN_FSAS)].copy()
    print(f"ED visits in catchment: {len(ed):,}  |  Inpatient: {len(hosp):,}")
    return ed, hosp, pop, nei


# ── 1. Avoidable ED Visits (CTAS 4-5 rate) ───────────────────────────────────

def avoidable_ed_visits(ed: pd.DataFrame) -> pd.DataFrame:
    result = (
        ed.groupby(["patient_fsa", "fiscal_year"])
        .apply(lambda g: pd.Series({
            "total_ed_visits":    len(g),
            "avoidable_visits":   (g["ctas_level"].isin([4, 5])).sum(),
            "avoidable_pct":      round((g["ctas_level"].isin([4, 5])).mean() * 100, 1),
        }))
        .reset_index()
    )
    return result


# ── 2. Chronic Disease Hospitalization Rate ───────────────────────────────────

def chronic_hosp_rate(hosp: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    hosp["is_acsc"] = hosp["primary_dx_icd10"].str[:3].isin(ACSC_CODES)
    acsc = (
        hosp.groupby(["patient_fsa", "fiscal_year"])
        .agg(acsc_admissions=("is_acsc", "sum"))
        .reset_index()
        .merge(pop.rename(columns={"fsa": "patient_fsa"}),
               on=["patient_fsa", "fiscal_year"], how="left")
    )
    acsc["acsc_rate_per_1000"] = (
        acsc["acsc_admissions"] / acsc["population"] * 1_000
    ).round(2)
    return acsc


# ── 3. Social Complexity Index ────────────────────────────────────────────────

def social_complexity_index(ed: pd.DataFrame) -> pd.DataFrame:
    available_flags = [f for f in SOCIAL_FLAGS if f in ed.columns]
    if not available_flags:
        ed["_any_social_flag"] = 0
    else:
        ed["_any_social_flag"] = (ed[available_flags].sum(axis=1) > 0).astype(int)

    sci = (
        ed.groupby(["patient_fsa", "fiscal_year"])
        .agg(
            encounters_with_social_flag  = ("_any_social_flag", "sum"),
            total_encounters             = ("_any_social_flag", "count"),
        )
        .reset_index()
    )
    sci["social_complexity_pct"] = (
        sci["encounters_with_social_flag"] / sci["total_encounters"] * 100
    ).round(1)
    return sci


# ── 4. 30-Day Readmission Rate by FSA ────────────────────────────────────────

def readmission_by_fsa(hosp: pd.DataFrame) -> pd.DataFrame:
    hosp = hosp.sort_values(["patient_id", "admission_date"])
    hosp["prev_discharge"] = hosp.groupby("patient_id")["discharge_date"].shift(1)
    hosp["days_since_discharge"] = (
        pd.to_datetime(hosp["admission_date"]) - pd.to_datetime(hosp["prev_discharge"])
    ).dt.days
    hosp["is_readmission_30d"] = hosp["days_since_discharge"].between(1, 30)

    readmit = (
        hosp.groupby(["patient_fsa", "fiscal_year"])
        .agg(
            index_admissions = ("is_readmission_30d", "count"),
            readmissions_30d = ("is_readmission_30d", "sum"),
        )
        .reset_index()
    )
    readmit["readmission_rate_pct"] = (
        readmit["readmissions_30d"] / readmit["index_admissions"] * 100
    ).round(2)
    return readmit


# ── 5. Mental Health Crisis Rate ──────────────────────────────────────────────

def mh_crisis_rate(ed: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    ed["is_mh"] = ed["chief_complaint_icd10"].str[:3].isin(MH_CODES)
    mh = (
        ed.groupby(["patient_fsa", "fiscal_year"])
        .agg(mh_presentations=("is_mh", "sum"), total_visits=("is_mh", "count"))
        .reset_index()
        .merge(pop.rename(columns={"fsa": "patient_fsa"}),
               on=["patient_fsa", "fiscal_year"], how="left")
    )
    mh["mh_rate_per_1000"] = (
        mh["mh_presentations"] / mh["population"] * 1_000
    ).round(2)
    return mh


# ── 6. Trend Analysis (Linear Regression by FSA, 3-Year) ─────────────────────

def compute_trend(df: pd.DataFrame, value_col: str, group_col: str = "patient_fsa") -> pd.DataFrame:
    """Returns slope and significance for each FSA over fiscal years."""
    def _slope(grp):
        if len(grp) < 3:
            return pd.Series({"slope": np.nan, "p_value": np.nan, "significant": False})
        x = np.arange(len(grp))
        slope, _, _, pval, _ = stats.linregress(x, grp[value_col].fillna(0))
        return pd.Series({
            "slope":       round(slope, 3),
            "p_value":     round(pval, 4),
            "significant": pval < 0.05,
        })
    trends = df.groupby(group_col).apply(_slope).reset_index()
    trends.columns = [group_col, "slope", "p_value", "significant"]
    return trends


# ── 7. NEI Equity Overlay ─────────────────────────────────────────────────────

def equity_overlay(indicator_df: pd.DataFrame, nei: pd.DataFrame,
                   value_col: str, fsa_col: str = "patient_fsa") -> pd.DataFrame:
    """Merge NEI quintiles and compute mean indicator by equity quintile."""
    merged = indicator_df.merge(nei[[fsa_col.replace("patient_", ""), "nei_quintile"]]
                                .rename(columns={fsa_col.replace("patient_", ""): fsa_col}),
                                on=fsa_col, how="left")
    equity_summary = (
        merged.groupby("nei_quintile")[value_col]
        .agg(["mean", "median", "count"])
        .round(2)
        .reset_index()
    )
    equity_summary.columns = ["nei_quintile", f"mean_{value_col}", f"median_{value_col}", "fsa_count"]
    return equity_summary


# ── Export ────────────────────────────────────────────────────────────────────

def export_all(results: dict, outdir: str = "output") -> None:
    import os; os.makedirs(outdir, exist_ok=True)
    for name, df in results.items():
        if isinstance(df, pd.DataFrame):
            path = f"{outdir}/{name}.csv"
            df.to_csv(path, index=False)
            print(f"  Exported {len(df)} rows → {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ed, hosp, pop, nei = load(
        "data/ed_visits_synthetic.csv",
        "data/hospitalizations_synthetic.csv",
        "data/tehn_fsa_population.csv",
        "data/toronto_nei_quintiles.csv",
    )

    avoidable  = avoidable_ed_visits(ed)
    chronic    = chronic_hosp_rate(hosp, pop)
    social     = social_complexity_index(ed)
    readmit    = readmission_by_fsa(hosp)
    mh         = mh_crisis_rate(ed, pop)

    # Trend analysis
    avoidable_trend = compute_trend(avoidable, "avoidable_pct")
    mh_trend        = compute_trend(mh, "mh_rate_per_1000")

    # Equity overlay
    social_equity   = equity_overlay(social, nei, "social_complexity_pct")
    readmit_equity  = equity_overlay(readmit, nei, "readmission_rate_pct")

    print("\n── Avoidable ED Visit Rate by FSA (latest year) ──")
    latest = avoidable[avoidable["fiscal_year"] == avoidable["fiscal_year"].max()]
    print(latest.sort_values("avoidable_pct", ascending=False)
              [["patient_fsa", "avoidable_pct"]].to_string(index=False))

    print("\n── Social Complexity by NEI Quintile ──")
    print(social_equity.to_string(index=False))

    export_all({
        "avoidable_ed_visits":     avoidable,
        "chronic_hosp_rate":       chronic,
        "social_complexity_index": social,
        "readmission_by_fsa":      readmit,
        "mh_crisis_rate":          mh,
        "avoidable_ed_trend":      avoidable_trend,
        "mh_trend":                mh_trend,
        "social_equity_overlay":   social_equity,
        "readmit_equity_overlay":  readmit_equity,
    })
