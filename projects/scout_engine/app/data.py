"""Data loading, caching, and display-formatting helpers for the Scout Engine app.

Split out of app.py so the Streamlit-caching/IO layer (this module) stays
separate from UI rendering (app.py) and from the k-NN search logic
(similarity.py) — each is independently testable without a running
Streamlit session.
"""

from pathlib import Path
from typing import Final

import duckdb
import joblib
import pandas as pd
import streamlit as st

from src.models.train import FEATURE_COLUMNS

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
MODEL_DIR: Final[Path] = PROJECT_ROOT / "models_saved"
DB_PATH: Final[Path] = PROJECT_ROOT / "data" / "portfolio.duckdb"
ALL_SEASONS_LABEL: Final[str] = "All seasons (career average)"

LEAGUE_DISPLAY_NAMES: Final[dict[str, str]] = {
    "epl": "Premier League",
    "la_liga": "La Liga",
    "ligue_1": "Ligue 1",
    "serie_a": "Serie A",
    "bundesliga": "Bundesliga",
    "rfpl": "Russian Premier League",
}

COLUMN_DISPLAY_NAMES: Final[dict[str, str]] = {
    "player_name": "Player",
    "primary_position": "Position",
    "team": "Team",
    "league": "League",
    "season": "Season",
    "xg_per_90": "xG per 90",
    "xa_per_90": "xA per 90",
    "npxg_per_90": "npxG per 90 (xG excl. penalties)",
    "shots_per_90": "Shots per 90",
    "key_passes_per_90": "Key Passes per 90",
    "xg_chain_per_90": "xG Chain per 90",
    "xg_buildup_per_90": "xG Buildup per 90",
    "prior_output_per_90": "Prior Season Output",
    "current_output_per_90": "Latest Season Output",
    "output_delta": "Change vs Prior Season",
    "breakout_percentile": "Breakout Percentile",
    "matches_played": "Matches Played",
    "points": "Points",
    "goals_for": "Goals For",
    "goals_against": "Goals Against",
    "xg_for": "xG For",
    "xg_against": "xG Against",
    "performance_vs_xg": "Performance vs xG",
}


def display_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename a DataFrame's columns to human-readable labels for display.

    Tables in this app are queried with snake_case column names (matching
    the dbt models), but shown to users via `COLUMN_DISPLAY_NAMES` instead
    of raw identifiers like `xg_per_90` — falls back to a title-cased,
    space-separated version of the column name if it isn't in that mapping.

    Args:
        df: The DataFrame to rename, in its original snake_case form.

    Returns:
        A copy of df with display-friendly column names.
    """
    return df.rename(columns=lambda c: COLUMN_DISPLAY_NAMES.get(c, c.replace("_", " ").title()))


def league_display_name(league_code: str) -> str:
    """Map a raw Understat league code to a human-readable display name.

    Args:
        league_code: Raw league code as stored in the data, e.g. "la_liga".

    Returns:
        A human-readable league name, falling back to a title-cased code
        for any league not in LEAGUE_DISPLAY_NAMES.
    """
    return LEAGUE_DISPLAY_NAMES.get(league_code, league_code.replace("_", " ").title())


def artifact_mtime(*paths: Path) -> float:
    """Return the latest modification time across the given files.

    Passed into cached loaders as a cache-busting argument: st.cache_data
    and st.cache_resource key on function arguments, not on-disk file
    contents, so without this a retrained model on disk would keep being
    shadowed by a stale in-memory cache from an earlier app run.
    """
    return max((p.stat().st_mtime for p in paths if p.exists()), default=0.0)


@st.cache_resource
def load_scaler(_cache_key: float):
    """Load the fitted StandardScaler from models_saved/.

    The k-NN similarity search is rebuilt on demand in `find_similar_players`
    (scoped to whatever candidate pool the user picks), so only the scaler —
    which defines the standardized feature space — needs to be loaded here.

    Args:
        _cache_key: Latest mtime of the artifact file; forces a cache miss
            (and reload) whenever it changes on disk. The leading underscore
            keeps Streamlit from trying to hash it as a resource.

    Returns:
        The fitted StandardScaler.

    Raises:
        FileNotFoundError: If the artifacts have not been trained yet.
    """
    scaler_path = MODEL_DIR / "scaler.joblib"
    if not scaler_path.exists():
        raise FileNotFoundError(
            "Model artifacts not found. Run `python -m src.pipeline.fetch_data`, "
            "`dbt run`, then `python -m src.models.train` first."
        )
    return joblib.load(scaler_path)


@st.cache_resource
def load_kmeans(_cache_key: float):
    """Load the fitted K-Means model used for the "playstyle profile" grouping.

    Args:
        _cache_key: Latest mtime of the artifact file; see `load_scaler`.

    Returns:
        The fitted KMeans model.
    """
    return joblib.load(MODEL_DIR / "kmeans.joblib")


@st.cache_resource
def load_cluster_labels(_cache_key: float) -> dict[int, str]:
    """Load the human-readable label for each K-Means cluster id.

    Args:
        _cache_key: Latest mtime of the artifact file; see `load_scaler`.

    Returns:
        A mapping from cluster id to a short descriptive label (see
        `src.models.train.label_clusters`).
    """
    return joblib.load(MODEL_DIR / "cluster_labels.joblib")


@st.cache_data
def load_player_features(_cache_key: float) -> pd.DataFrame:
    """Load the canonical player-season feature table the models were fit on.

    This reads the Parquet snapshot written by src/models/train.py rather
    than re-querying DuckDB, so that row positions here line up exactly
    with the positions `nn.kneighbors()` returns.

    Args:
        _cache_key: Latest mtime of player_features.parquet; forces a cache
            miss whenever the file changes on disk.

    Returns:
        The player-season feature DataFrame, in training row order.

    Raises:
        FileNotFoundError: If training has not been run yet.
    """
    path = MODEL_DIR / "player_features.parquet"
    if not path.exists():
        raise FileNotFoundError("Run `python -m src.models.train` first to generate model artifacts.")
    return pd.read_parquet(path)


@st.cache_data
def load_mart_table(_cache_key: float, table_name: str) -> pd.DataFrame:
    """Load a dbt mart table straight out of DuckDB.

    Args:
        _cache_key: DuckDB file mtime; forces a cache miss whenever the
            database changes on disk (see `artifact_mtime`).
        table_name: The dbt model/table name to select from, e.g.
            "mart_player_breakout". Only ever called with hardcoded names
            from this module, never user input.

    Returns:
        The full contents of the table as a DataFrame.
    """
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    return conn.execute(f"select * from {table_name}").fetchdf()  # noqa: S608 (table_name is not user input)


def build_career_averages(df: pd.DataFrame, scaler, kmeans) -> pd.DataFrame:
    """Collapse a player-season table into one minutes-weighted row per player.

    Args:
        df: The player-season feature table.
        scaler: The fitted StandardScaler, used to re-derive a playstyle
            cluster for the aggregated row (a per-season "cluster" column
            already exists on `df`, but averaging it across seasons
            wouldn't mean anything — a career-average row needs its own
            cluster assignment from the averaged features).
        kmeans: The fitted KMeans model used for that cluster assignment.

    Returns:
        One row per player_id with each feature minutes-weighted across
        all of their available seasons/leagues, plus their most recent
        league and a playstyle cluster fit on the averaged features.
    """
    weights = df["minutes_played"].clip(lower=1)
    weighted = df[FEATURE_COLUMNS].multiply(weights, axis=0)

    agg = weighted.groupby(df["player_id"]).sum().div(weights.groupby(df["player_id"]).sum(), axis=0)
    total_minutes = weights.groupby(df["player_id"]).sum().rename("minutes_played")
    latest = df.sort_values("season").groupby("player_id").last()[["player_name", "team", "primary_position", "league"]]

    out = latest.join(agg).join(total_minutes).reset_index()
    out["season"] = ALL_SEASONS_LABEL
    out["cluster"] = kmeans.predict(scaler.transform(out[FEATURE_COLUMNS]))
    return out


def get_active_player_ids(reference_df: pd.DataFrame) -> set:
    """Find players who appeared in the most recently fetched season.

    Used to keep "Active players only" similarity search limited to players
    who are still active — e.g. Benzema's last fetched Understat season is
    2021 (he left Europe's top 5 leagues after that), so he shouldn't turn
    up as a "current" comparable even though his career-average stats are
    still in the dataset.

    Args:
        reference_df: The full per-season feature table.

    Returns:
        The set of player_id values present in the latest season.
    """
    latest_season = reference_df["season"].astype(int).max()
    return set(reference_df.loc[reference_df["season"].astype(int) == latest_season, "player_id"])
