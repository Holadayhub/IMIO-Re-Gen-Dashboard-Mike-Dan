# Imio Re-Gen — Executive Dashboard (Streamlit)

Holaday Seed Company · Soil Health & Pathogen Monitoring

This is a Streamlit port of the Imio Re-Gen executive dashboard, built so you can host it as a live, shareable URL on **Streamlit Community Cloud** (free).

## What's in this folder

- `app.py` — the Streamlit application
- `requirements.txt` — Python package dependencies
- `blocks_data.json` — the 35-block dataset (grower, ranch, block, nutrients, pathogens, scores, notes, recommendations, photos)
- `logo.png` — Holaday Seed Company logo used in the header

All four files must stay together in the same folder/repo — `app.py` loads the other three by filename.

## Deploying to Streamlit Community Cloud (free, ~5 minutes)

1. **Create a GitHub repo.** Go to [github.com/new](https://github.com/new), create a new repository (public or private both work), e.g. `imio-regen-dashboard`.
2. **Upload these 4 files** to the repo. Easiest way: on the repo's GitHub page, click "Add file" → "Upload files", drag in `app.py`, `requirements.txt`, `blocks_data.json`, and `logo.png`, then commit.
3. **Sign in to Streamlit Community Cloud.** Go to [share.streamlit.io](https://share.streamlit.io) and sign in with your GitHub account.
4. **Deploy the app.** Click "New app", pick your repo/branch, set the main file path to `app.py`, and click "Deploy".
5. **Get your link.** After a minute or two, Streamlit will build the app and give you a public URL like `https://your-app-name.streamlit.app` — that's the live, shareable dashboard link.

## Updating the data later

When you have a new tracker/results file, the simplest path is: ask me to rebuild `blocks_data.json` from the updated tracker, then replace that one file in your GitHub repo (upload it again with the same filename and commit). Streamlit Community Cloud auto-redeploys within a minute or two whenever the repo changes — no other steps needed.

## Running it locally first (optional)

If you want to preview it on your own machine before deploying:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL it prints (usually `http://localhost:8501`).

## What it includes

- Grower filter that reactively updates every section (KPIs, donut, charts, table, drill-down)
- KPI row: Blocks Sampled, Growers, Ranches, Avg Soil Health Score, High-Risk Blocks, Low-Risk Blocks, Pending Lab Results
- Risk distribution donut (High / Moderate / Low / Pending)
- Most Frequently Flagged Metrics chart
- Average Soil Health Score by Ranch, with explicit "No data" bars for ranches with no lab results yet
- Grower cards showing each grower's average score or "no data yet"
- Sortable block table (Rank, Grower, Ranch, Block, Score, Risk, Metrics Scored, Flagged Metrics)
- Block drill-down: full 17-nutrient and 7-pathogen panels (color-coded), sub-scores, crop cycle & sample dates, notes, recommendations, and field photos
