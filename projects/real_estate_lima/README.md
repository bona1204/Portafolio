# Lima Real Estate

Predictive price/m² model detecting undervalued properties via the
MercadoLibre API.

**Status:** Building

## Stack
Random Forest · dbt · MercadoLibre · DuckDB

## Layout
- `src/pipeline/` — MercadoLibre listing ingestion
- `src/models/` — price/m² regression model
- `app/` — Streamlit demo
- `dbt_project/` — SQL transformations (staging → marts)

## Local setup
See the [root README](../../README.md#local-setup).
