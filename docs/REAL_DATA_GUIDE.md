# Real data guide: where to get it, how to train, how to prove it

## The honest picture first

I searched for open, site-level **metered** mini-grid datasets (kWh per
customer, by village). I found **none that you can simply download**. This
matches Brief 03's own data pack, which marks metered consumption from live
sites as "Partner needed". So your plan has three tiers. Do Tier 1 first,
and keep Tiers 2 and 3 as your safety net.

| Tier | What | Gives you | Effort |
|---|---|---|---|
| 1 | Metered data from a real operator (partner) | Real accuracy numbers, the thing judges reward most | Ask early. Depends on a human saying yes |
| 2 | Real mini-grid **locations** (no kWh) | A real-world plausibility check | 30 minutes |
| 3 | Household survey data | Local spend defaults and sanity bands | 1 to 2 hours |

---------------------------------------------------------------------------
## Tier 1. Metered data from an operator

**Who to ask (in this order):**
1. Your hackathon coach (ask in Slack in the first two hours). Coaches are
   there to make introductions.
2. Mini-grid developers in your country. Look at members of the Africa
   Minigrids Developers Association (AMDA) and developers named in ESMAP
   reports.
3. The Mini-Grid Innovation Lab (run by Energy4Impact with Odyssey) analysed
   smart-meter data from 62 sites of 12 developers in East Africa and Nigeria.
   I could not confirm that dataset is public. Ask the organisers whether
   they can share it or point you to the owners.

**What to ask for (the minimum):** for each site, the **coordinates** (rounded
to about 1 km is fine), the **connection date**, and **monthly kWh sold and
number of customers**. No names, meter IDs or bills.

**What to offer:** a free benchmark report comparing their sites with similar
villages, free forecasts for their next sites, and credit in your project.

**Message you can send:**

> Hello [name], I am [you], building DemandRange for the Global Energy
> Hackathon (Brief 03: predicting mini-grid demand before building). We would
> like to test our forecaster on real metered sites. Could you share, for even
> 5 to 10 sites, the village coordinates (rounded to 1 km), connection date,
> and monthly kWh and customer counts? No customer-level data is needed. In
> return we will give you a free benchmark report and forecasts for your next
> sites. The data stays private, and we will sign a short data-use agreement.
> Our deadline is Sunday 12:00 PM ET, so a quick reply would help a lot.

**Format to ask for.** A spreadsheet in one of these two layouts (the script
`scripts/build_training_table.py` reads either):

```
A) site_id,lat,lon,years_since_connection,kwh_per_customer_month
B) site_id,lat,lon,connection_date,month,kwh_total,customers
```

Optional extra columns: `region` (country or area), `energy_spend_usd`.

**Privacy rules:** do not commit their file to GitHub (the `.gitignore`
already blocks `data/raw/`). Publish only aggregated results and the trained
model, and say in your disclosure that the data was shared by a partner.

---------------------------------------------------------------------------
## Tier 1b. A public metered dataset: DRC mini-grid (Harvard Dataverse)

A teammate or another team may point you to a public CC0 dataset of metered
mini-grid data from the DRC on Harvard Dataverse. I could not open that record
myself, so check these things before you build on it:

1. **Licence:** the Dataverse page says CC0 (or another open licence). Cite the
   dataset title, authors and DOI in your disclosure.
2. **Unit:** is it one row per connection per month (customer-level), or
   already per site? Which columns hold locality, connection id, month, kWh?
3. **Coordinates:** is there GPS per connection or per locality? If not, find the
   locality centres (OpenStreetMap or Nominatim) and make a small
   `locality,lat,lon` file.
4. **Customer type:** is there a household vs business (SME) column?

A study I found fits this description: Lunanga, Stoop, Verpoorten and
Desbureaux (Energy Economics, Feb 2026) use pre-grid surveys and about six years
of consumption records from four rural and one urban locality served by one
operator in North Kivu. I have not confirmed it is the same dataset. If it is,
its findings help you: pre-grid factors explain only part of demand, businesses
use far more per connection than households, and use rises after connection then
levels off. That supports a range (not a single number), a productive-use
module, and a growth curve that flattens.

**Honest limit:** that is about five localities and one operator in one conflict
region, so it cannot show the model works everywhere.

**How to use it:**

```
$ python scripts/prepare_connection_data.py --input data/raw/connections.csv \
    --locality-col <your column> --connection-col <your column> \
    --month-col <your column> --kwh-col <your column> \
    --type-col <household/business column> \
    --lat-col <lat column> --lon-col <lon column> --cell-km 1.0
$ python scripts/build_training_table.py --input data/raw/operator_sites.csv
$ python run_pipeline.py --data data/real_training.csv
```

With GPS, `--cell-km 1.0` turns each 1 km cell into its own site, so you get
dozens of real sites instead of five, and each locality becomes a "region" for the
unseen-region test. The first script also prints average kWh per connection by
year since commissioning, and the business-to-household ratio. Both are real-data
facts for your slides.

If the model does **not** beat the flat-average guess on this data, say so.
Report the range hit rate and the growth curve instead. Judges score evidence,
and they trust honest results.

---------------------------------------------------------------------------
## Free tools your coach shared (kickoff slide) and how DemandRange uses them

| Tool | Use in DemandRange |
|---|---|
| NASA POWER (free, no key) | **Used.** Sunshine at the village, which turns the forecast into a solar and battery size |
| World Bank ENERGYDATA.INFO | **Use now.** Real mini-grid locations and electrification maps (see Tier 2) |
| QGIS + OpenStreetMap | **Used** (OpenStreetMap live in the app). QGIS for map layers and checking |
| NLR PVWatts API, Global Solar Atlas | Optional upgrade to the sunshine numbers (PVWatts needs a free key) |
| pandapower, PyPSA, OpenDSS | Not used. For grid engineering studies, outside our scope |
| OpenEI, EIA, Open Power System Data | Not used. US and Europe focused |

The slide's starter for access projects is "ENERGYDATA.INFO + QGIS". That is
exactly Tier 2 below plus the map lookups.

**Paywall note:** the journal version of the DRC paper is paywalled, but the
authors' working paper is free (chair-energy-prosperity.org). Its published
averages are already saved in `data/benchmarks/drc_published_means.csv`, and
`python scripts/compare_to_published.py` compares your forecasts with them. That
needs no purchase. Harvard Dataverse datasets are normally free to download.

---------------------------------------------------------------------------
## Tier 2. Real mini-grid locations (a plausibility check)

World Bank **energydata.info** hosts open files of existing mini-grid
locations, for example **Kenya: Existing mini-grids** (CC0, shapefile) and
**Somalia: Minigrids** (Open Database License). They contain locations but not
consumption.

1. Download the file. If it is a **GeoJSON of points** (like the Somalia mini-grids),
   convert it with the script. It swaps the coordinate order for you:

```
$ python scripts/geojson_to_csv.py --input somalia_minigrids.geojson --output data/raw/known_minigrids.csv
```

   If the file is a CSV or shapefile, make a CSV with `name`, `lat`, `lon` columns
   (QGIS can export one). **Use off-grid mini-grid sites only.** Power-line files,
   substations and big towns on the national grid are not mini-grids and give
   meaningless results.
2. Save it in `data/raw/`. Try five sites first, then the full file:

```
$ python scripts/sanity_check_known_sites.py --input data/raw/known_minigrids.csv --limit 5
$ python scripts/sanity_check_known_sites.py --input data/raw/known_minigrids.csv
```

The script prints progress for every site. If it stops early, the free map
servers are busy or unreachable: wait a few minutes and run it again (finished
sites are remembered). A ready-made Somalia file is in `data/raw/known_minigrids_somalia.csv`.

It forecasts each real location from the map and reports how many land inside
the 5 to 35 kWh band that ESMAP found. **Say this in your pitch:** "plausibility
check on N real sites, not an accuracy test."

---------------------------------------------------------------------------
## Tier 3. Household survey data (supporting evidence)

The World Bank **Microdata Library** holds the ESMAP **Multi-Tier Framework**
household surveys (for example Kenya 2016 to 2018 and Niger 2018). A free
account is needed. They include monthly household electricity use and spending
on kerosene, candles and batteries.

Use them to (a) pick a realistic `energy_spend_usd` for your country instead of
the placeholder, and (b) cross-check that your forecasts are the right size.
Check the data dictionary: public survey files usually identify villages only by
cluster codes, not coordinates, so they cannot train the coordinate-based model.

---------------------------------------------------------------------------
## Free map layers the project uses

| Layer | Used for | Cost and access |
|---|---|---|
| OpenStreetMap through the Overpass API | Buildings, shops, markets, schools, clinics, power lines (live, no key) | Free. Shared service: results are cached, requests are spaced out |
| Nominatim (OpenStreetMap) | Searching a place name | Free, max 1 request per second. Set `GEO_CONTACT` to your email |
| OpenStreetMap tiles in Leaflet | The map picture | Free with attribution, for light use |
| WorldPop "Nighttime Lights 2015-2023" | Night light at the village (optional) | Free country-level GeoTIFF (about 100 m). Download your country, then set `NIGHTLIGHT_TIF=path/to/file.tif` |

If you skip night light, the model still works. It just gives a slightly wider
range. Better building data (Google Open Buildings or Overture Maps) is a
stretch upgrade for places where OpenStreetMap is thin.

**Known weakness, say it out loud:** OpenStreetMap is incomplete in some rural
areas. The API warns when fewer than 20 buildings are mapped. Because your
real-data model trains on features read the same way, it learns what an
under-mapped village looks like.

---------------------------------------------------------------------------
## Train on your real data (after Tier 1)

```
$ python scripts/build_training_table.py --input data/raw/operator_sites.csv
$ python run_pipeline.py --data data/real_training.csv
```

- The first command reads the map for every site (about 1 to 3 seconds per
  site) and writes `data/real_training.csv`. Sites it cannot read are listed in
  `data/real_training_skipped.csv`.
- The second trains, validates on sites the model never saw, and saves the
  model. The warning banner in the app and API changes from "simulated" to
  "trained on N real sites".
- With fewer than 30 sites the app adds an "indicative only" warning. Keep it.
  Fewer than 5 sites cannot be validated.

Check `reports/validation.json`. Put these real numbers in your slides:
`held_out_sites.mae_kwh`, `held_out_sites.improvement_vs_baseline_pct`,
`held_out_sites.range_coverage_pct`.

**Deploy the real model:** `git add -f models/demandrange.joblib reports/validation.json`
then commit and push. The Dockerfile uses the committed model.

---------------------------------------------------------------------------
## If no partner data arrives by Saturday noon ET

Do not fake it. Instead:
1. Run Tier 2 on at least 10 real mini-grid locations.
2. Show the map-driven forecasts and heatmap on real coordinates.
3. Keep the "trained on simulated data" banner visible in your demo.
4. Present the real-data validation as your funded first step, with the
   operator data-sharing proposal as the plan to get it.
Judges reward honesty about limits, and they check numbers.
