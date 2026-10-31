# Disclosure statement (copy into the portal form)

**Team:** [name] **Brief:** 03 **Track:** 2 **Setting:** A

## What existed before October 30, 2026 (prior work)
- DemandRange code: simulated-data generator, quantile forecasting model with
  calibration, validation routines, productive-use and finance calculators,
  lender-memo writer, Streamlit app, automated tests.
- Tagged in Git as `pre-sprint` on October 29, 2026.
- Any footage recorded before Oct 30 is labelled as prior work in the videos.

## What we built during the 48-hour sprint
[List each item. Example:]
- Loaded real data from [source, number of sites/rows].
- Retrained and validated on held-out [sites/regions]. Result: [numbers].
- Replaced placeholder loan, cost and tariff inputs with sourced values.
- [Anything else], plus the demo video, pitch video, deck and summary.

## Data used
- Simulated villages generated from ranges stated in the Brief 03 text
  (demand of 5 to 35 kWh per customer per month; household energy spend of
  $5 to 20 per month; faster growth with business activity). Simulated data is
  not real measurements.
- [Real datasets used, with licence and link: Google Open Buildings, NOAA VIIRS,
  GridFinder, Energy Access Explorer, World Bank MTF surveys, operator data.]
- Load factor and cost-of-power curve calibrated to the ESMAP figures quoted in
  the brief (22% load factor, 40% with daytime business, 25% lower cost).

## Open-source software
Python, NumPy, pandas, scikit-learn, matplotlib, joblib, FastAPI, Uvicorn, Streamlit, requests, Leaflet, Chart.js, pytest.
Each is used under its own open-source licence.

## AI tools used
[Name the AI assistants you used, for example Claude, and what for: brainstorming,
code drafting, documentation. State that you reviewed and tested the code.]

## Limits we are upfront about
- Validation figures are from [real / simulated] data as stated on each slide.
- Money inputs in the lender memo are [sourced from ___ / placeholders].
