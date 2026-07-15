# Surf Predictor

Surf session quality classifier for Costa Verde beach using the
Open-Meteo Marine API.

**Status:** Building

## Stack
Decision Tree · Open-Meteo · Parquet · DuckDB

## Layout
- `src/pipeline/` — Open-Meteo Marine API ingestion
- `src/models/` — session quality decision tree classifier
- `app/` — Streamlit demo
- `dbt_project/` — SQL transformations (staging → marts)

## Local setup
See the [root README](../../README.md#local-setup).
