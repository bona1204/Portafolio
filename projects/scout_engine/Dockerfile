FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Bake the data into the image at build time: nothing under data/,
# models_saved/, or dbt_project/profiles.yml is committed to git (see
# .gitignore), so without this the deployed container would boot with no
# database and no trained models. This makes the image fully
# self-contained and reproducible from a clean checkout, at the cost of a
# slower build (Understat fetch + dbt + training run once, here).
RUN cp dbt_project/profiles.yml.example dbt_project/profiles.yml && \
    python -m src.pipeline.fetch_data && \
    cd dbt_project && dbt run && dbt snapshot && cd .. && \
    python -m src.models.train

EXPOSE 8501
CMD ["streamlit", "run", "app/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
