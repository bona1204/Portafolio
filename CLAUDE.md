# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A monorepo of 4 **independent** data engineering portfolio projects under
`projects/`, plus a static landing page (`docs/`) that showcases all of
them. There is no shared root-level Python environment, build, or test
command — every project is self-contained with its own `requirements.txt`,
`dbt_project/`, and test suite. Commands below are always run from
*within* a project directory unless stated otherwise.

Only **`projects/scout_engine`** is a fully built-out reference
implementation (`Status: Live`). The other three (`real_estate_lima`,
`steam_intelligence`, `surf_predictor`) are identical skeleton stubs
(`Status: Building` — same placeholder `app/app.py`, `src/pipeline/fetch_data.py`,
`src/models/train.py`, `src/utils/db.py` line-for-line) that will be
fleshed out later, following scout_engine's structure. When asked to work
on one of those, treat scout_engine as the pattern to follow.

## Commands (per project, e.g. `projects/scout_engine`)

```bash
# Setup
cp .env.example .env
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# dbt — must be run from inside dbt_project/ (paths in dbt_project.yml's
# `vars` are relative to the invocation directory, not the project root)
cp dbt_project/profiles.yml.example dbt_project/profiles.yml
cd dbt_project
DUCKDB_PATH="$(pwd)/../data/portfolio.duckdb" dbt run
DUCKDB_PATH="$(pwd)/../data/portfolio.duckdb" dbt test       # or `dbt build` to run+test+snapshot together
DUCKDB_PATH="$(pwd)/../data/portfolio.duckdb" dbt snapshot   # SCD2 history, run after dbt run
cd ..

# Train models (after dbt run has populated the DuckDB marts)
python -m src.models.train

# Run the Streamlit app
streamlit run app/app.py

# Tests (pytest.ini sets pythonpath=. and testpaths=tests, so this works
# from the project root without extra config)
pytest                          # full suite
pytest tests/test_similarity.py -v         # single file
pytest tests/test_data.py::test_league_display_name_known_code  # single test
```

Only `scout_engine` currently has a `pytest.ini`/`tests/` suite and a
populated dbt project (staging → marts, snapshot). The other three
projects have empty `dbt_project/models/` and no tests yet.

## Architecture

### Standard per-project layout
Every project follows: `src/pipeline/` (ingestion), `src/models/`
(train.py — fits and persists model artifacts to `models_saved/`),
`src/utils/db.py` (shared DuckDB connection helpers), `app/` (Streamlit
app), `dbt_project/` (staging → marts, `+snapshots/`), `data/` (raw
ingested files + the DuckDB file), `models_saved/` (joblib/parquet
artifacts), `tests/`.

### scout_engine as the reference architecture
Two distinct halves, and it matters which one a task touches:

1. **Data production** (batch, offline): `src/pipeline/fetch_data.py`
   (Understat) → dbt `staging/` → incremental `mart_player_season` →
   fans out to `dim_player_latest` (+ SCD2 `snapshots/player_team_snapshot.sql`),
   `mart_player_breakout` (self-join for year-over-year deltas), and
   `src/models/train.py` (StandardScaler + KMeans, persisted to
   `models_saved/`). A separate match-results branch feeds
   `mart_team_season`. See `projects/scout_engine/README.md` for the full
   diagram and the reasoning behind each model (incremental strategy,
   SCD2, why the breakout metric differs by position).

2. **Serving** (the Streamlit app, split into 3 files — do not put data
   access or business logic back into `app.py`):
   - `app/app.py` — UI rendering only (tabs, widgets, charts).
   - `app/data.py` — all loading/caching (`@st.cache_resource` /
     `@st.cache_data`, keyed on each artifact's mtime via `artifact_mtime`
     so a retrained model on disk isn't shadowed by a stale cache) plus
     display-formatting helpers (`display_columns`, `league_display_name`).
   - `app/similarity.py` — the k-NN "similar players" search; refits a
     fresh `NearestNeighbors` per query against whatever candidate pool
     the UI selects, rather than reusing one pretrained index, since the
     pool changes per request and refitting on ~27k rows is instant.

These two halves don't run in the same place at deploy time — see below.

### Deployment reality (scout_engine)
Deployed on **Streamlit Community Cloud** (not Hugging Face Spaces, despite
what the root README's "Architecture decisions" section says — HF now
requires a PRO subscription for both Docker and Gradio Spaces on the
account this portfolio uses, so that plan was abandoned for this
project). Streamlit Community Cloud only runs `pip install -r
requirements.txt` then the app file — there is no custom build step. So
unlike a Docker-based deploy, `data/portfolio.duckdb` and
`models_saved/*.joblib`/`*.parquet` are **committed to git as a frozen
snapshot**, via explicit negation exceptions carved into the root
`.gitignore` (which otherwise ignores those patterns for every other
project). To refresh scout_engine's demo data: re-run the pipeline
locally end-to-end and commit the regenerated files.

### Landing page (`docs/`)
Static, dependency-free (vanilla HTML/CSS/JS, no build step, no
frameworks), served via GitHub Pages. `index.html` holds all content;
`style.css` uses CSS custom properties (`--accent`, `--surface-1`, etc.)
for the dark theme; `main.js` is a set of small self-invoking modules
(nav scroll state, typing effect, scroll-reveal via IntersectionObserver,
animated counters, an architecture-diagram modal system keyed by
`data-arch-open`/panel `id` pairs). Each project card links out to its
live demo and GitHub source; only projects with `Status: Live` get an
"architecture" modal (built by hand with CSS flexbox nodes/arrows, no
diagramming library) — don't add one for a project that's still
`Building`, since there's nothing finalized yet to diagram.
