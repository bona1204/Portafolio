# Scout Engine

Hidden gem detector using xG profiles and player similarity clustering
across 6 European leagues.

**Status:** Live

## Stack
DuckDB · K-Means · Understat · Streamlit

## Layout
- `src/pipeline/` — Understat data ingestion
- `src/models/` — similarity clustering model
- `app/` — Streamlit demo
- `dbt_project/` — SQL transformations (staging → marts)

## Local setup
See the [root README](../../README.md#local-setup).
