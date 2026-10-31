# Prompt for Lovable or Bolt (paste everything below the line)

Tips: paste it as one message. If the first result is rough, fix one thing at
a time in follow-up messages. Keep `frontend/reference/index.html` as a
working backup.

---------------------------------------------------------------------------

Build a map-first web app called **DemandRange**. It forecasts how much
electricity each customer of a planned village mini-grid will use, with a
low, middle and high case, so developers and lenders can size and finance the
system before building. Users are mini-grid developers, lenders and
development-fund analysts in West and East Africa, often on modest laptops
and slow connections.

## The one rule
**Never show invented numbers.** Every figure comes from my backend API. If a
call fails, show a plain-language error and what the user can do next. No mock
data, no placeholder charts.

## Backend
Read the base address from the environment variable `VITE_API_URL`
(no trailing slash). All endpoints return JSON unless noted. CORS is open.

1. `GET /health` returns `{status, model: {trained_on_simulated_data, warning, data_source, n_sites}}`
2. `GET /geocode?q=Kaduna, Nigeria` returns `{results: [{name, lat, lon}]}`
3. `POST /forecast` body: `{lat, lon, name?, energy_spend_usd?, overrides?, skip_map_lookup?, assumptions?}`
   - `overrides` may contain: households, business_per_100, night_light,
     dist_to_grid_km, market_within_5km (0 or 1), schools_clinics, energy_spend_usd
   - `assumptions` may contain: customers, capex_per_customer_usd,
     opex_per_customer_year_usd, tariff_usd_per_kwh, debt_share,
     interest_rate, tenor_years, target_dscr
   Response:
   ```
   { location, site_inputs: {...},
     data_quality: {sources: [..], warnings: [..]},
     model_info: {trained_on_simulated_data, warning, n_sites, data_source},
     curve: [{year:0,p10,p50,p90}, ... year 4],            // kWh per customer per month
     years_1_to_3_average: {p10,p50,p90},
     productive_use: {load_factor, cost_index, cost_saving_vs_household_only_pct, anchors:[..]},
     finance: {breakeven_kwh, prob_cover_debt, cushion_pct, annual_debt_service_usd,
               typical_monthly_bill_usd, bill_vs_current_spend},
     drivers: [{what_changes, change_kwh}],
     solar: {annual_kwh_m2_day, worst_month_kwh_m2_day, worst_month} | null,
     system_sizing: {sizes: {low_case|middle_case|high_case: {daily_kwh, pv_kwp, battery_kwh}},
                     cost_of_wrong: {persons_served, benchmark_capex_usd, capex_per_person_usd,
                                     capex_per_10pct_sizing_error_usd, wasted_if_sized_for_high_case_usd}} | null,
     memo_markdown: "..." }
   ```
4. `POST /heatmap` body: `{lat, lon, half_width_km (2-15), cells_per_side (2-6), metric ("p10"|"p50"|"p90"|"prob_cover_debt"), year? (0-4), energy_spend_usd?}`
   returns GeoJSON FeatureCollection. Each polygon has `properties`:
   `{cell_id, status ("ok"|"failed"), value, p10, p50, p90, prob_cover_debt, households, business_per_100, dist_to_grid_km, buildings_mapped, warnings}`.
   `metadata` has `{metric, unit, min, max, cells_ok, cells_failed, warnings, model_info}`.
   This can take up to a minute: show progress text, never freeze the page.
5. `POST /export/heatmap?format=csv` or `format=geojson`, same body as `/heatmap`; returns a file to download.
6. `GET /validation` returns `{model, results: {held_out_sites: {mae_kwh, baseline_mae_kwh, improvement_vs_baseline_pct, range_coverage_pct, rows_tested}, held_out_regions: {...}, held_out_sites_map_inputs_only: {...}, growth_year0_to_year3_pct: {actual, predicted}, data_note}}`
7. `GET /heatmap/presets` returns `{presets: [names]}`; `GET /heatmap/presets/{name}` returns a pre-computed heatmap GeoJSON (loads instantly).

## Screens and behaviour
**One main screen**, map on the right (about 65% width on desktop, full width
on top for mobile), control panel on the left (a bottom sheet on mobile).

- **Map:** Leaflet with OpenStreetMap tiles and attribution (free). Click to
  drop a pin. A search box calls `/geocode` and flies to the first result.
  Show the pin's coordinates.
- **Forecast button:** calls `/forecast` for the pin. While waiting, show
  "Reading the map and forecasting...".
- **Result panel:**
  - Three headline figures: middle case (kWh per customer per month, average of years 1 to 3), the low to high range, and the chance the site covers its loan (`prob_cover_debt` as a percent).
  - A **range chart** (Recharts or similar): x = years after connection (0 to 4), a shaded band between `p10` and `p90`, a solid line for `p50`, and a horizontal reference line at `finance.breakeven_kwh` labelled "Needed to cover the loan".
  - "What drives this" list from `drivers` (top 4, show sign and size).
  - Daytime business card: load factor percent and "x% cheaper power", plus the `anchors` list.
  - **System card** (only if `system_sizing` is not null): solar kW and battery kWh for the low, middle and high case, the sunshine figure, and the line "each 10% sizing error is about USD X" from `cost_of_wrong`. Say it uses the ESMAP cost per person.
  - Affordability line: typical monthly bill and `bill_vs_current_spend` as a percent of what households spend today.
  - "Where this came from": list `data_quality.sources`, and show every string in `data_quality.warnings` in a visible amber notice.
- **Advanced inputs (collapsed):** let the user override any map-derived input
  (sliders and a market switch) and edit loan and tariff assumptions. Send them
  as `overrides` and `assumptions`, and recompute.
- **Heatmap:** a "Show demand heatmap" button with a selector for the metric
  (Middle case, Low case, High case, Chance to cover loan). Calls `/heatmap`,
  draws the polygons colour-scaled between `metadata.min` and `metadata.max`,
  with a legend showing the unit. Click a cell for a popup with p10, p50, p90,
  chance to cover loan and buildings mapped. Cells with `status: "failed"`
  appear grey with "No map data". Also offer a "Load saved heatmap" dropdown
  filled from `/heatmap/presets`.
- **Exports** (visible after a result): "Download lender memo" (save
  `memo_markdown` as a .md file), "Heatmap CSV", "Heatmap GeoJSON" (call
  `/export/heatmap`), and "Print or save as PDF" (browser print, with a print
  stylesheet that hides the map controls and shows the figures, chart and memo).
- **Lender memo tab:** render `memo_markdown` as formatted text.
- **How well it works tab:** call `/validation` and show typical error in kWh,
  how much better it is than guessing the average (percent), how often the range
  caught the real value (aim for about 80%), growth predicted vs actual, and
  `data_note`. Show the error for unseen villages and for an unseen region.

## Honesty banner (required)
Call `/health` on load. If `model.trained_on_simulated_data` is true, show a
persistent banner at the top of the screen with `model.warning`, and on every
printed or exported view. Never hide it. If `model.warning` is set for any other
reason (for example few sites), show that too.

## Design direction
This is a field tool for people who read maps and spreadsheets, so make it calm,
dense where it counts, and trustworthy, not a startup landing page.
- **Palette:** deep ink `#14213D`, teal `#0B7A75` (primary actions and the middle-case line), pale teal `#9CC9C6` (range band), amber `#E8A317` (only for the "needed to cover the loan" line and warnings), light grey-blue `#EEF3F6` (panels), white background.
- **Type:** one family, Atkinson Hyperlegible (readable on small, low-quality screens). Sentence case everywhere. Numbers in tabular figures.
- **Layout:** the map is the hero. No hero banner, no gradient washes, no identical stacks of rounded cards: use one panel with clear sections separated by thin rules, and let the range chart be the single most visual element.
- Use plain language: say "low case, middle case, high case", never "quantile" or "P10". Say "how steadily the power is used" next to "load factor".
- Visible keyboard focus, good contrast, works on a 375 px wide phone, respects reduced motion, no auto-playing animation.

## Done when
1. Searching "Kaduna, Nigeria" moves the map; clicking drops a pin.
2. "Forecast" shows the three figures, the range chart with the loan line, drivers, business card and affordability line.
3. Warnings from the API appear in amber, and the simulated-data banner shows when the API says so.
4. The heatmap draws coloured cells, popups work, failed cells are grey.
5. All four exports work and the printed page is clean.
6. If the API is down, the user sees a clear message, not a blank screen.
7. No data is hard-coded anywhere.

---------------------------------------------------------------------------
## Follow-up prompts you may need
- "Add a loading skeleton while the heatmap builds, and a cancel button."
- "The chart band is not shading between p10 and p90. Use an area from p10 to p90 and a separate line for p50."
- "Make the right panel a bottom sheet on screens under 800 px."
- "Add a CSV upload so a user can forecast many villages: columns name, lat, lon. Call /forecast for each and show a sortable table, with an export button."
