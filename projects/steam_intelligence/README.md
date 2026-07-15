# Steam Intelligence

Tag association mining to identify winning game niches for indie
developers.

**Status:** Building

## Stack
Apriori · K-Means · Prefect · SteamSpy

## Layout
- `src/pipeline/` — SteamSpy data ingestion via Prefect flows
- `src/models/` — tag association mining and clustering
- `app/` — Streamlit demo
- `dbt_project/` — SQL transformations (staging → marts)

## Local setup
See the [root README](../../README.md#local-setup).
