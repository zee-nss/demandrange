# DemandRange

Open mini-grid demand forecasts with honest ranges, built for the Global Energy
Hackathon 2026, **Brief 03: Predict mini-grid demand before building**.

Give it a **map coordinate** (or a village description). It reads free
OpenStreetMap data around that point, then returns:

- a demand **range** (low, middle, high case) in kWh per customer per month
- a **growth curve** for years 0 to 4 after connection
- a **daytime-business estimate** (load factor and cost of power)
- a **system size** (solar kW, battery kWh) and the **cost of being wrong**, using free NASA sunshine data
- a plain-language **lender memo** with the chance the site covers its loan
- **validation** on villages (and a whole region) the model has never seen
- a **demand heatmap** over an area, exportable as CSV, GeoJSON or PDF
- a **web API** (FastAPI) for a Lovable or Bolt front end

> **Honest limits:** the prototype trains on *simulated* villages built from
> ranges in the brief, and the API says so in every response until you train
> on real data (`docs/REAL_DATA_GUIDE.md`). Map lookups use OpenStreetMap, which
> is incomplete in some rural areas. Say both in your disclosure statement.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_pipeline.py           # makes data, validates, trains, writes a memo
pytest -q                        # all tests should pass
streamlit run app.py             # opens the app in your browser
```

Run the web API (for Lovable, Bolt, or the reference page):

```bash
export GEO_CONTACT=you@example.com     # your email, for the free map services
uvicorn api.main:app --port 8000       # docs at http://localhost:8000/docs
# then open frontend/reference/index.html in your browser
```

New to all this? Follow `docs/STEP_BY_STEP_GUIDE.md`, then
`docs/REAL_DATA_GUIDE.md` and `docs/DEPLOY_GUIDE.md`.

## Folder map

```
demandrange/
├── README.md                     this file
├── CHANGELOG.md                  what you built during the 48 hours (update it!)
├── requirements.txt              the Python packages needed
├── .gitignore
├── .streamlit/config.toml        app colours
├── app.py                        the web app (Streamlit)
├── run_pipeline.py               one command: data -> validate -> train -> memo
├── Dockerfile · render.yaml      deploy the API (Hugging Face Spaces or Render)
├── requirements-api.txt          lighter package list for deployment
├── api/main.py                   the web API: /forecast /heatmap /geocode /export ...
├── frontend/reference/index.html a working map front end (backup to Lovable/Bolt)
├── scripts/
│   ├── build_training_table.py   operator CSV + coordinates -> training table
│   ├── geojson_to_csv.py         point GeoJSON -> name,lat,lon CSV
│   ├── compare_to_published.py   forecasts vs real published DRC averages (free)
│   ├── prepare_connection_data.py  customer-level meter records -> site-level file
│   ├── precompute_heatmap.py     build a heatmap ahead of the demo
│   └── sanity_check_known_sites.py  plausibility check on real mini-grid locations
├── deploy/huggingface_space_README.md
├── demandrange/                  the code
│   ├── config.py                 settings, feature names, plain-language labels
│   ├── data.py                   simulated data + loader for your real CSV
│   ├── model.py                  low/middle/high forecasting model + calibration
│   ├── validate.py               held-out village and held-out region tests
│   ├── productive_use.py         daytime business and cost-of-power estimate
│   ├── finance.py                breakeven demand and chance of covering the loan
│   ├── explain.py                "what moves the forecast" table
│   ├── forecast.py               one call that builds the whole forecast
│   ├── service.py                loads the model, reports what it was trained on
│   ├── geo/osm.py                free map services: Overpass + Nominatim (cached)
│   ├── geo/features.py           coordinates -> village features + warnings
│   ├── geo/raster.py             optional night-light GeoTIFF reader
│   ├── geo/solar.py              NASA POWER sunshine (free)
│   ├── sizing.py                 solar + battery size and the cost of a wrong forecast
│   ├── geo/grid.py               heatmap grid + GeoJSON/CSV
│   └── memo.py                   writes the lender memo
├── data/                         sample_sites.csv appears here
├── models/                       the trained model is saved here
├── reports/                      validation.json, validation.png, sample memo
├── tests/test_basic.py           automatic checks

```
