# Deploy guide: API on Hugging Face or Render, front end on Lovable or Bolt

**Order of work:** 1) run the API on your laptop, 2) deploy it, 3) build the
front end against the deployed address, 4) test everything, 5) record your
videos from a run you have already tested.

I could not test Docker builds or live map calls from my environment. Every
step below includes a check so you find problems in minutes, not at 11 AM Sunday.

---------------------------------------------------------------------------
## 1. Run the API on your laptop

```
$ source .venv/bin/activate          # Windows: .venv\Scripts\activate
$ pip install -r requirements.txt
$ python run_pipeline.py             # makes the model (skip if already done)
$ export GEO_CONTACT=you@example.com # Windows PowerShell: $env:GEO_CONTACT="you@example.com"
$ uvicorn api.main:app --reload --port 8000
```

Open http://localhost:8000/docs. This page lets you try every endpoint.

**Checks:**
- `/health` shows `"status": "ok"`.
- In `/docs`, try **POST /forecast** with `{"lat": 10.52, "lon": 7.44}`.
  If it returns numbers, live map lookups work from your network.
  If you get a 503 error, the free map services are busy or blocked. Wait a
  minute and retry. If it keeps failing, use `skip_map_lookup` with manual
  inputs, and pre-compute heatmaps (step 6).
- Open `frontend/reference/index.html` in your browser. It is a working front
  end for this API. Use it to confirm the API works before you touch Lovable.

---------------------------------------------------------------------------
## 2. Deploy on Hugging Face Spaces (free)

1. Create an account at huggingface.co. New > **Space**. Name: `demandrange-api`.
   SDK: **Docker**, template: **Blank**. Visibility: Public.
2. Copy `deploy/huggingface_space_README.md` over `README.md` in your Space
   (the Space needs the header block at the top of its README).
3. Upload or `git push` all project files to the Space (not the `frontend`
   folder, it is optional). The `Dockerfile` is already in the project root.
4. In the Space: Settings > Variables and secrets > add a variable
   `GEO_CONTACT` with your email.
5. Wait for the build (3 to 8 minutes). Your API address is
   `https://YOUR-USERNAME-demandrange-api.hf.space`.

**Check:** open `https://YOUR-USERNAME-demandrange-api.hf.space/health` and
`/docs`.

---------------------------------------------------------------------------
## 2b. Or deploy on Render (free)

1. Push the project to GitHub.
2. Render dashboard > New > **Web Service** > connect the repo. Choose
   **Docker** runtime and the free instance. (The included `render.yaml` holds
   the same settings.)
3. Add the environment variable `GEO_CONTACT` with your email.
4. Your address looks like `https://demandrange-api.onrender.com`.

**Free-tier warning:** free instances go to sleep when idle, and the first
request can take about a minute. Open `/health` yourself a few minutes before
any demo or judging window.

---------------------------------------------------------------------------
## 3. Build the front end on Lovable or Bolt

1. Open `docs/LOVABLE_BOLT_PROMPT.md` and paste the whole prompt into Lovable
   or Bolt.
2. When it asks for the API address, give it your deployed HTTPS address.
   Store it as an environment variable `VITE_API_URL`.
3. Test each feature against the checklist at the bottom of that file.

**Important:** a deployed (HTTPS) front end cannot call an `http://localhost`
API in most browsers. Always point it at your deployed HTTPS API.

If the generated front end misbehaves and time is short, deploy
`frontend/reference/index.html` as a static page (Netlify Drop, GitHub Pages or
Hugging Face static Space). It talks to the same API.

---------------------------------------------------------------------------
## 4. Share the real model, not the private data

Train on real data locally (see `docs/REAL_DATA_GUIDE.md`), then:

```
$ git add -f models/demandrange.joblib reports/validation.json reports/validation.png
$ git commit -m "Real-data model"
$ git push
```

The deployed API then reports `trained on N real sites` instead of the
simulated-data warning. Never commit operator files.

---------------------------------------------------------------------------
## 5. Settings you may need

| Variable | What it does |
|---|---|
| `GEO_CONTACT` | Your email, sent in the User-Agent to the free map services (they ask for it) |
| `ALLOWED_ORIGINS` | Which websites may call the API. `*` means all. For safety set it to your Lovable address before the final submission |
| `NIGHTLIGHT_TIF` | Path to the WorldPop night-light file (optional) |
| `OVERPASS_URL` | Use another Overpass server if the default is busy |
| `MAX_PARALLEL_HEATMAPS` | How many heatmaps can build at once (default 2) |

---------------------------------------------------------------------------
## 6. Make the heatmap demo-proof

Live heatmaps read the map for every cell and can take a minute or fail when
the free servers are busy. For the demo video:

```
$ python scripts/precompute_heatmap.py --name my-region --lat 10.52 --lon 7.44 --half-width-km 15 --cells 6
```

This saves `data/heatmaps/my-region.geojson` and `.csv`. The API serves them at
`/heatmap/presets` and `/heatmap/presets/my-region`, and your front end can load
them instantly. Commit these files so the deployed API has them. Say "computed
from live OpenStreetMap data on [date]" in your demo.

"Real time" here means calculated on demand from current map data, not a
streaming feed. Say it that way.

---------------------------------------------------------------------------
## 7. Problems and fixes

| Problem | Fix |
|---|---|
| 503 "OpenStreetMap is not reachable" | Free servers are busy. Wait, retry, set `OVERPASS_URL`, or use manual inputs and pre-computed heatmaps |
| 429 "Another heatmap is being built" | Wait a minute, or raise `MAX_PARALLEL_HEATMAPS` |
| Browser says "blocked by CORS" | Check `ALLOWED_ORIGINS`, and that you call an HTTPS address |
| Space or Render shows "starting" for minutes | First start or wake-up. Refresh `/health` |
| Forecast says "Very few buildings are mapped" | Real warning. Zoom the map to check the area, or override the inputs |
| Banner says "trained on SIMULATED villages" | You have not trained on real data yet. See the real data guide |
