# Project: Value Stream Mapping & Cycle-Time Analysis — Emergency Department Patient Flow

**Prepared by:** Nicholas Steven
**Target Role:** Analyst — Michael Garron Hospital / Toronto East Health Network (TEHN)
**GitHub Repo:** https://github.com/nicholasstevenr/MichaelGarronHospital-health-data-project
**Looker Studio Link:** [Pending publish — TEHN Operations Dashboard]

---

## Problem Statement

Community hospitals like Michael Garron operate under significant capacity pressure, with ED throughput and patient flow efficiency directly impacting patient outcomes and staff workload. Operational analysts need to identify where process waste accumulates — delays, rework, handoff failures — before recommending targeted improvements. This project applies value stream mapping (VSM) principles to a synthetic community hospital ED, combining qualitative process mapping with Python-based quantitative cycle-time analysis to pinpoint improvement opportunities.

---

## Approach

1. **Value Stream Map (as-is):** Documented the full ED patient journey from triage to disposition across 7 process steps, capturing: cycle time, wait time, data handoffs, and process actors at each stage. Structured as a VSM with process boxes, push/pull arrows, data flows, and a time ladder.
2. **Data collection:** Extracted cycle-time data from 8,000 synthetic ED visit records spanning 12 months. Segmented by CTAS level (1-5), day-of-week, hour-of-arrival, and patient disposition (admitted vs. discharged).
3. **Waste identification:** Applied VSM waste categories to quantify: waiting (idle time between steps), over-processing (duplicate assessments), and defects (repeat triage reclassifications).
4. **To-be design:** Proposed a future-state VSM with 3 targeted improvements: fast-track stream for CTAS 4–5, nurse-initiated orders protocol, and bed assignment automation.
5. **Impact quantification:** Modelled projected cycle-time reductions from each improvement using historical data distributions.

---

## Tools Used

- **Python (pandas, numpy, scipy):** Cycle-time analysis, waste quantification, simulation of improvement scenarios
- **VSM methodology:** Value stream mapping (Lean healthcare), process boxes, time ladder, push/pull notation
- **Looker Studio:** Operational dashboard — ED throughput, wait times by step, CTAS breakdown
- **Excel:** Summary output formatted for TEHN management reporting

---

## Measurable Outcome / Impact

- VSM identified that 67% of total ED time was wait time (non-value-add) vs. 33% active care time — a high-leverage finding for process redesign
- Fast-track stream proposal projected a 41% reduction in CTAS 4–5 median LOS (from 3.2 hrs to 1.9 hrs), supported by historical sub-population data
- Nurse-initiated orders protocol modelled to eliminate 28-minute average physician order delay for the most common presenting complaints
- Waste quantification approach aligns with TEHN's community hospital context and Ontario Health patient-flow improvement framework
