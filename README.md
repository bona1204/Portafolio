# Data Engineering Portfolio — Sebastian Zapata

Portfolio of end-to-end data engineering projects: ingestion pipelines, dbt
transformations, ML models, and Streamlit apps, built with a lightweight,
cost-free local-first stack.

## Projects

| Project | Description | Stack | Status |
|---|---|---|---|
| [Scout Engine](projects/scout_engine) | Football player similarity engine | DuckDB · K-Means · Understat · Streamlit | Live |
| [Lima Real Estate](projects/real_estate_lima) | Property price predictor for Lima | Random Forest · dbt · MercadoLibre · DuckDB | Building |
| [Steam Intelligence](projects/steam_intelligence) | Game niche detector via tag mining | Apriori · K-Means · Prefect · SteamSpy | Building |
| [Surf Predictor](projects/surf_predictor) | Wave session quality classifier for Costa Verde | Decision Tree · Open-Meteo · Parquet · DuckDB | Building |

## Architecture decisions

- **DuckDB over Spark**: every project stays under ~1M rows; DuckDB gives
  in-process OLAP performance without cluster infrastructure.
- **Parquet as storage format**: columnar, compressed, and natively readable
  by DuckDB — no intermediate serialization cost.
- **dbt Core**: SQL transformations with lineage, tests, and documentation,
  run locally against DuckDB via `dbt-duckdb`.
- **Prefect**: lightweight orchestration for scheduled/triggered pipelines
  without provisioning infrastructure.
- **Hugging Face Spaces**: free Docker-based deployment target for the
  Streamlit apps, always-on.

## Repository layout

```
portfolio/
├── docs/                # GitHub Pages landing site
├── projects/
│   ├── scout_engine/
│   ├── real_estate_lima/
│   ├── steam_intelligence/
│   └── surf_predictor/
├── .gitignore
└── README.md
```

Each project follows the same internal layout: `src/` (pipeline, models,
utils), `data/` (raw, silver, gold), `app/` (Streamlit app), `dbt_project/`,
`models_saved/`, and `notebooks/`.

## Local setup

```bash
# From within a given project directory, e.g. projects/scout_engine
cp .env.example .env
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run the Streamlit app
streamlit run app/app.py

# Run dbt models
cp dbt_project/profiles.yml.example dbt_project/profiles.yml
cd dbt_project && dbt run
```

## Landing page

The `docs/` folder is a static, dependency-free landing page (HTML/CSS/JS)
served via GitHub Pages, showcasing all projects.
