# Project: Community Health Indicator Dashboard — TEHN Catchment Area Analysis

**Prepared by:** Nicholas Steven
**Target Role:** Analyst — Michael Garron Hospital / Toronto East Health Network (TEHN)
**GitHub Repo:** https://github.com/nicholasstevenr/MichaelGarronHospital-health-data-project
**Looker Studio Link:** [Pending publish — TEHN Community Health Dashboard]

---

## Problem Statement

Michael Garron Hospital serves a diverse, high-density urban catchment area spanning East Toronto neighbourhoods with significant socioeconomic variation — from Riverdale to Scarborough borders — where social determinants of health directly shape ED utilization and inpatient demand. Community health analysts at TEHN need neighbourhood-level indicator dashboards to support community benefit reporting, identify high-need populations for outreach programs, and align hospital capacity planning with population health trends. This project builds a community health indicator dashboard for the TEHN catchment area, linking hospitalization data with neighbourhood-level social determinants.

---

## Approach

1. **Catchment definition:** Mapped TEHN service area to Toronto Forward Sortation Areas (FSAs: M4E, M4J, M4K, M4L, M4M, M4N, M4P, M4C, M4B) using synthetic patient postal code data; applied 80% catchment rule (FSAs where ≥80% of patients originate).
2. **Indicator computation:** Calculated 5 community health indicators at FSA level:
   - **Avoidable ED visits:** CTAS 4–5 visits as % of total — proxy for primary care gaps
   - **Chronic disease hospitalization rate:** ACSC conditions per 1,000 catchment population
   - **Social complexity index:** Proportion of encounters with ≥1 social determinant flag (housing instability, food insecurity, language barrier, transportation barrier)
   - **30-day readmission rate by postal code:** Identifies high-burden neighbourhood clusters
   - **Mental health crisis presentation rate:** MH-flagged ED visits per 1,000 population
3. **Social determinants linkage:** Joined patient encounter data to Toronto Neighbourhood Equity Index (NEI) quintiles for each FSA to overlay equity analysis.
4. **Trend analysis:** Computed 3-year trend slopes for each indicator using linear regression (fiscal years 2022–2024), identifying neighbourhoods with deteriorating vs. improving health trajectories.
5. **Dashboard design:** Looker Studio choropleth map of TEHN FSAs + indicator scorecard per neighbourhood + trend sparklines + NEI quintile overlay.

---

## Tools Used

- **Python (pandas, numpy, scipy, geopandas):** Indicator computation, FSA spatial joins, NEI quintile merge, trend regression
- **Toronto Open Data:** Neighbourhood Equity Index quintile data (public dataset)
- **Looker Studio:** Choropleth map, FSA-level drill-down scorecard, trend charts
- **Excel:** Management summary formatted for TEHN community benefit reporting template

---

## Measurable Outcome / Impact

- Avoidable ED visit analysis identified 3 FSAs with CTAS 4–5 rates >40% — pointing to primary care access gaps in specific East Toronto neighbourhoods, actionable for TEHN's community health centre partnerships
- Social complexity index showed highest-quintile NEI neighbourhoods had 2.1× higher social flag rate than lowest-quintile — quantifying the social determinant burden for community investment prioritization
- 30-day readmission clustering identified a 2-FSA corridor with rates 34% above the TEHN average, supporting targeted post-discharge follow-up program design
- Trend analysis flagged 2 neighbourhoods with statistically significant 3-year increases in MH crisis presentations (slope > 5 visits/1,000/year, p < 0.05) — informing TEHN's mental health navigation investment case
