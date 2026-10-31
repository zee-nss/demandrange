# Step-by-step guide: from zero to a submitted project

No coding experience needed for Parts A to C. Copy each command exactly.
Lines starting with `$` are typed in the terminal (do not type the `$`).

---------------------------------------------------------------------------
## Part A. Set up your computer (about 20 minutes)

**A1. Install Python.** Go to python.org/downloads and install Python 3.10 or
newer. On Windows, tick **"Add Python to PATH"** on the first screen.

**A2. Install VS Code** (code.visualstudio.com). It is a free editor.

**A3. Unzip the project** to a folder you can find, for example `Documents`.
You should now have a folder called `demandrange`.

**A4. Open it in VS Code.** File > Open Folder > choose `demandrange`.
Then open a terminal: Terminal > New Terminal.

**A5. Create a private Python environment** (this keeps packages tidy):

```
$ python -m venv .venv
```

Activate it:

- Mac or Linux: `$ source .venv/bin/activate`
- Windows (PowerShell): `$ .venv\Scripts\Activate.ps1`
  (If Windows blocks it, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.)

You should see `(.venv)` at the start of the terminal line.
If `python` is not found, try `python3` (Mac) or `py` (Windows).

**A6. Install the packages:**

```
$ pip install -r requirements.txt
```

---------------------------------------------------------------------------
## Part B. Run it and see it work (about 10 minutes)

**B1. Build everything with one command:**

```
$ python run_pipeline.py
```

It prints four steps: create data, validate, train, write a sample memo.
Look for the "Held-out sites" line. That is your accuracy test on villages the
model has never seen. When it finishes you will have new files in `data/`,
`models/` and `reports/`.

**B2. Run the automatic checks:**

```
$ pytest -q
```

You want to see `7 passed`.

**B3. Start the app:**

```
$ streamlit run app.py
```

Your browser opens at http://localhost:8501. Try it:

1. Pick **Market town** in the sidebar. Watch the forecast change.
2. Drag **Businesses per 100 households**. See the growth curve and cost move.
3. Open **Loan and tariff assumptions** and lower the tariff. Watch the
   "chance it covers the loan" drop.
4. Open the **Lender memo** tab and click **Download memo**.
5. Open **How well it works** to see the validation chart.

Stop the app with `Ctrl + C` in the terminal.

---------------------------------------------------------------------------
## Part C. What each file does (so you can explain it)

| File | Plain-language job |
|---|---|
| `demandrange/data.py` | Makes simulated villages, and loads your real CSV |
| `demandrange/model.py` | Learns to predict low, middle and high demand; widens the range until it is right about 80% of the time |
| `demandrange/validate.py` | Hides villages (and a whole region) from the model, then checks its predictions |
| `demandrange/productive_use.py` | Turns business activity into a load factor and a cost-of-power saving, calibrated to the brief's 22% to 40% and 25% figures |
| `demandrange/finance.py` | Works out how many kWh a customer must use for the loan to be safe, and the chance the forecast gets there |
| `demandrange/explain.py` | Changes one input at a time to show what drives the forecast |
| `demandrange/memo.py` | Writes the one-page lender memo |
| `app.py` | The web app judges will see in your demo |

---------------------------------------------------------------------------
## Part D. Make it real (do this DURING the sprint)

**Why this matters.** Everything you built before Oct 30 counts as *prior
work*. Judges score what you accomplish during the 48 hours, and the brief's
top score needs validation on *real metered sites*. So the sprint is for
swapping simulated data for real data and showing the result.

**D1. Get real demand data** (try them in this order):

1. **Ask for metered data.** Post in your track's Slack channel and ask your
   coach to introduce a mini-grid operator. Even 3 to 5 sites with monthly
   kWh per customer helps. Offer to give back a free benchmark report.
2. **World Bank Multi-Tier Framework household surveys** (public). Use them
   to link household traits to electricity use.
3. **ESMAP and AMDA mini-grid benchmarking reports** (public). Use them to
   sanity-check your numbers and to replace the placeholder costs.

**D2. Get real village features** (all public, listed in the brief's data pack):

| Column in the CSV | Where it comes from |
|---|---|
| `households` | Count of buildings: Google Open Buildings or OpenStreetMap |
| `business_per_100` | Larger or clustered buildings and OpenStreetMap shops, per 100 homes |
| `night_light` | NOAA VIIRS night-time lights |
| `dist_to_grid_km` | GridFinder |
| `market_within_5km` | Energy Access Explorer or OpenStreetMap (1 or 0) |
| `schools_clinics` | Energy Access Explorer or OpenStreetMap |
| `energy_spend_usd` | Household surveys (monthly spend on candles, kerosene, batteries, diesel) |

Tip: QGIS (free) can sample these map layers at a village's coordinates
without any code. Ask your coach or teammates for help here.

**D3. Build one CSV** called `data/real_sites.csv` with these exact columns
(one row per village per year since connection):

```
site_id,region,households,business_per_100,night_light,dist_to_grid_km,market_within_5km,schools_clinics,energy_spend_usd,years_since_connection,kwh_per_customer_month
```

`region` is the country or area name (it is used for the "new region" test).
Open `data/sample_sites.csv` to see the format.

**D4. Run the pipeline on your data:**

```
$ python run_pipeline.py --data data/real_sites.csv
```

If a column is missing, the error message tells you which one.

**D5. Check the new results** in `reports/validation.json` and the app's
"How well it works" tab. The simulated numbers are replaced by real ones.
Write the real error (kWh) and the real range hit rate in your slides.

**D6. Replace the placeholder money numbers.** In the app's sidebar, open
"Loan and tariff assumptions" and enter real build cost, running cost, tariff
and loan terms from ESMAP or AMDA benchmarks (or from your operator). Write
down each source for your deck. The judges' checklist says every number needs
a source.

**If you cannot get any real metered data:** keep the simulated validation but
label it everywhere as simulated, show the method working on a survey-based
dataset (D1 option 2) if you can, and state in your pitch that real-data
validation is the first step of your 6 to 18 month plan. Never present
simulated results as real.

---------------------------------------------------------------------------
## Part E. Your 48-hour plan (all times Eastern; Sprint: Fri Oct 30 12:00 PM to Sun Nov 1 12:00 PM)

If you are in Nigeria (WAT), the sprint runs Fri 5:00 PM to Sun 6:00 PM,
because US clocks go back on Nov 1. Check the schedule on hackathon.anneru.com.

| Sprint hour | Do this |
|---|---|
| Before: Thu Oct 29 | Run Parts A and B. Tag your code: `git init`, `git add .`, `git commit -m "pre-sprint"`, `git tag pre-sprint`. Join the 8:00 PM ET kick-off and read the full Brief 03. |
| 00 to 02 | Pick Brief 03, Track 2 (Digital Solutions and AI), setting A (Residential). Request a coach in Slack. |
| 02 to 05 | Write your Proof of Concept in one line: "Our model beats a flat-average guess on real held-out sites and shows a range." Fill `docs/appendix_a_solution_outline.md`. |
| 05 to 16 | Do Part D: real data in, retrain, validate. Ask the coach for operator data. |
| 24 (Sat 12:00 PM) | Coach checkpoint. Bring your validation result and one question. |
| 32 (Sat about 8:00 PM) | **Feature freeze.** No new features after this. |
| 36 to 40 | Polish the app. Make sure it shows the brief's metric (error on held-out sites) on screen. |
| 40 to 46 | Record the demo video (3 to 5 minutes). See `docs/pitch_and_demo_scripts.md`. |
| 46 to 48 | Record the pitch video. Upload everything early. Finish `docs/disclosure_statement.md`. |

---------------------------------------------------------------------------
## Part F. Your six deliverables (due Sun Nov 1, 12:00 PM ET)

| # | Deliverable | How to make it |
|---|---|---|
| 1 | Demo video, 3 to 5 min (MP4 or link) | Screen-record the app. Script in `docs/pitch_and_demo_scripts.md`. Name: `TeamName_Brief03_Demo.mp4` |
| 2 | Pitch video, up to 5 min | Narrate over your slides and app. Name: `TeamName_Brief03_Pitch.mp4` |
| 3 | Pitch deck, PDF, up to 5 slides | Follow the GEH Pitch Template (5 slides, mapped in the pitch script) |
| 4 | One-page summary, PDF | Copy `docs/appendix_a_solution_outline.md` into a one-page document, export to PDF |
| 5 | Build files (link) | Push this folder to GitHub and share the link. Judges look for commits during the sprint |
| 6 | Disclosure statement (portal form) | Copy from `docs/disclosure_statement.md` and fill the blanks |

**Video checks:** 1080p or lower, under 500 MB, English. If you submit a link
(YouTube unlisted, Drive), open it in a private window to confirm it plays
without sign-in. Voice-over is allowed, and your face is optional.

**Upload to GitHub** (free account at github.com):

```
$ git add .
$ git commit -m "Describe what you changed"
$ git remote add origin https://github.com/zeenah/demandrange.git
$ git push -u origin main
```

Commit a few times during the sprint (after each part of Part D) so the
history shows real work.

---------------------------------------------------------------------------
## Part G. Common problems

| Problem | Fix |
|---|---|
| `python: command not found` | Use `python3` (Mac) or `py` (Windows) |
| `No module named demandrange` | Run commands from inside the `demandrange` folder |
| `No module named sklearn` or `streamlit` | Activate the environment (A5), then `pip install -r requirements.txt` |
| App shows an old model | Delete `models/demandrange.joblib`, run `python run_pipeline.py` again |
| `Your CSV is missing these columns` | Match the column names in D3 exactly |
| Port already in use | `streamlit run app.py --server.port 8502` |
| Charts or app look wrong after changing data | Stop the app (`Ctrl + C`) and start it again |

---------------------------------------------------------------------------
## Part H. Stretch goals if you have time (in this order)

1. **Auto-fill from coordinates:** read the map layers at a latitude and
   longitude so users do not type village features (the brief says "any
   location"). Ask a teammate who knows GIS.
2. **Real growth data:** use metered sites with 2+ years of history to
   check the growth curve.
3. **Two countries:** train on one country, test on another, and report the
   result. This directly supports the Scalability score.

---------------------------------------------------------------------------
## Part I. Going live: real coordinates, API, front end

Parts A to H gave you a working prototype. To use **real coordinates**, a
**heatmap**, and a **Lovable or Bolt front end**, follow these in order:

1. `docs/REAL_DATA_GUIDE.md` : where to get real data and how to train on it.
2. `docs/DEPLOY_GUIDE.md` : run the API, deploy it, connect the front end.
3. `docs/LOVABLE_BOLT_PROMPT.md` : the prompt to paste into Lovable or Bolt.

Quick local test of the live map lookup (needs internet):

```
$ export GEO_CONTACT=you@example.com
$ uvicorn api.main:app --port 8000
```

Then open http://localhost:8000/docs, try **POST /forecast** with
`{"lat": 10.52, "lon": 7.44}`, and open `frontend/reference/index.html`.
