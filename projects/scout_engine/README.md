# Scout Engine

Player similarity search over xG profiles across 6 European leagues
(2014–2025), plus a "Breakout Watch" that flags FWD/MID players new to
the dataset whose attacking output jumped the most year-over-year.

**Status:** Live

## Stack
DuckDB · dbt (incremental models + snapshots) · scikit-learn (k-NN) · Understat · Streamlit

## Data model

```
Understat (players)  ──▶ stg_players  ──▶ mart_player_season (incremental)
                                              │                  │      │
                                              ▼                  ▼      ▼
                                       dim_player_latest   src/models/  mart_player_breakout
                                       (+ SCD2 snapshot)   train.py     (year-over-year
                                                            (k-NN)       output delta)
Understat (matches)   ──▶ stg_matches ──▶ mart_team_season
```

- **`mart_player_season`** is an incremental dbt model, keyed on
  `(player_id, league, season)`: re-running the pipeline only
  reprocesses rows newer than the last fetch, not the full ~27k-row
  history.
- **`snapshots/player_team_snapshot.sql`** tracks each player's
  team/league/position as a Type-2 SCD — a mid-season transfer (or a
  re-fetch that picks one up) shows up as a new row with
  `dbt_valid_from`/`dbt_valid_to`, not a silent overwrite.
- **`mart_player_breakout`** self-joins `mart_player_season` (latest
  absolute season vs. the one before) to rank FWD/MID players new to
  the dataset (≤3 seasons on record) by the change in a position-specific
  output metric: npxG+xA per 90 for forwards, xA+Key Passes per 90 for
  midfielders (goal threat vs. chance creation — Understat has no
  passing/defensive/goalkeeping data, so GK/DEF and genuinely defensive
  midfielders aren't covered; see the model's header comment). An
  earlier version of this model compared raw npxG across all positions
  against a scraped Transfermarkt market value, and kept surfacing
  goalkeepers and centre-backs as its top "undervalued" picks as a
  result. That scraper was also a Transfermarkt ToS violation, so it
  was dropped entirely rather than fixed.

## How the app serves this

The dbt marts and `train.py` artifacts above are all this pipeline
produces "at rest" — none of it is queried live from Understat. The
Streamlit app is a thin, cached read layer on top of that output:

```
Browser
  │
  ▼
app/app.py  (UI only: tabs, widgets, charts — no data access itself)
  │
  ├──▶ app/data.py
  │      • load_scaler / load_kmeans / load_cluster_labels  → models_saved/*.joblib
  │      • load_player_features                             → models_saved/player_features.parquet
  │      • load_mart_table("mart_player_breakout" | "mart_team_season") → data/portfolio.duckdb (read-only)
  │      all wrapped in @st.cache_resource / @st.cache_data, keyed on
  │      each file's mtime (artifact_mtime) so a retrained model on disk
  │      is picked up without a stale in-memory cache surviving it
  │
  └──▶ app/similarity.py
         • find_similar_players: fits a fresh scikit-learn NearestNeighbors
           on whatever candidate pool the user's filters select (active
           players / same playstyle cluster / everyone, × a season scope)
         • refit-per-query instead of one pretrained index, since the
           pool changes per request and refitting on ~27k rows is
           effectively instant
```

`player_features.parquet` (not a live DuckDB query) is the source of
truth for anything the k-NN touches — it's the exact row order
`train.py` fit the scaler on, so row positions stay consistent between
training and search. The dbt marts (`mart_player_breakout`,
`mart_team_season`) are queried directly from DuckDB instead, since
those tabs don't need row-position alignment with a fitted model.

## Layout
- `src/pipeline/` — Understat ingestion (players + matches)
- `src/models/` — similarity/clustering model
- `app/` — Streamlit app: `app.py` (UI only), `data.py` (loading/caching),
  `similarity.py` (k-NN search)
- `dbt_project/` — staging → marts, plus snapshots
- `tests/` — pytest unit tests for the pure Python logic in `app/` and `src/`

## Local setup
See the [root README](../../README.md#local-setup). After `dbt run`, also
run `dbt snapshot` to capture the SCD2 team-history table.

## Deployment
Deployed on [Streamlit Community Cloud](https://streamlit.io/cloud) (free
tier), which only runs `pip install -r requirements.txt` then `app/app.py`
— no custom build step. So unlike a Docker-based deploy, `data/portfolio.duckdb`
and `models_saved/*.joblib`/`*.parquet` are **committed to the repo as a
frozen snapshot** (an exception carved out of the root `.gitignore`),
rather than regenerated on every deploy. To refresh the demo with newer
data: re-run the pipeline locally (`fetch_data` → `dbt run` → `dbt
snapshot` → `train`) and commit the updated files.

## Testing
```bash
pytest
```
Covers the pandas/scikit-learn logic in `app/data.py`, `app/similarity.py`,
and `src/models/train.py`'s cluster labeling, plus `src/utils/db.py`'s
query error handling. dbt's own `not_null`/`unique` schema tests
(`dbt test`) cover the SQL models.
