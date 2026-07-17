"""Model training for Scout Engine.

Fits a player-similarity engine on top of the `mart_player_season` dbt
model: features are standardized and clustered with K-Means (for the
"playstyle profile" grouping shown in the app). The k-NN "find similar
players to X" search itself is fit on-demand in app.py, not here — see
`train()` for why. Fitted artifacts are persisted to models_saved/.
"""

from pathlib import Path
from typing import Final

import joblib
import pandas as pd
from loguru import logger
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.utils.db import execute_query, get_conn

FEATURE_COLUMNS: Final[list[str]] = [
    "xg_per_90",
    "xa_per_90",
    "npxg_per_90",
    "shots_per_90",
    "key_passes_per_90",
    "xg_chain_per_90",
    "xg_buildup_per_90",
]

MODEL_DIR: Final[Path] = Path("models_saved")
N_CLUSTERS: Final[int] = 8
N_NEIGHBORS: Final[int] = 6  # includes the queried player itself


def load_features(db_path: str = "data/portfolio.duckdb") -> pd.DataFrame:
    """Load the per-90 player feature set produced by the mart_player_season dbt model.

    Args:
        db_path: Path to the DuckDB database populated by `dbt run`.

    Returns:
        A DataFrame with player identifiers and the per-90 feature columns.
    """
    conn = get_conn(db_path)
    id_columns = ["player_id", "player_name", "team", "primary_position", "league", "season", "minutes_played"]
    columns = ", ".join([*id_columns, *FEATURE_COLUMNS])
    # ORDER BY makes row order deterministic across calls — the app relies on
    # this matching the row order the k-NN/K-Means models were fit on.
    rows = execute_query(conn, f"select {columns} from mart_player_season order by player_id, season, league")
    if not rows:
        raise ValueError("mart_player_season returned no rows — run `dbt run` first")
    return pd.DataFrame(rows, columns=[*id_columns, *FEATURE_COLUMNS])


def label_clusters(kmeans: KMeans, scaler: StandardScaler) -> dict[int, str]:
    """Derive a human-readable playstyle label for each k-means cluster.

    Cluster IDs are arbitrary integers with no inherent meaning, so this
    inverse-transforms each centroid back into per-90 feature space, then
    names the cluster after the 2 features that stand out most relative to
    the overall dataset average (in standardized units — cluster_centers_
    are already in that space, so no extra scaling needed here).

    Args:
        kmeans: The fitted KMeans model.
        scaler: The StandardScaler the k-means was fit on (used only to
            keep the mapping obvious; centers are read directly from kmeans).

    Returns:
        A mapping from cluster id to a short descriptive label, e.g.
        "High-volume finisher (xg, shots)".
    """
    feature_labels = {
        "xg_per_90": "xg",
        "xa_per_90": "xa",
        "npxg_per_90": "npxg",
        "shots_per_90": "shots",
        "key_passes_per_90": "key passes",
        "xg_chain_per_90": "xg chain",
        "xg_buildup_per_90": "xg buildup",
    }
    labels: dict[int, str] = {}
    for cluster_id, center in enumerate(kmeans.cluster_centers_):
        top_idx = center.argsort()[::-1][:2]
        top_features = ", ".join(feature_labels[FEATURE_COLUMNS[i]] for i in top_idx)
        labels[cluster_id] = f"Cluster {cluster_id}: high {top_features}"
    return labels


def train(db_path: str = "data/portfolio.duckdb", out_dir: Path = MODEL_DIR) -> None:
    """Fit the clustering + similarity models and persist them to disk.

    Args:
        db_path: Path to the DuckDB database populated by `dbt run`.
        out_dir: Directory to write the fitted model artifacts to.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_features(db_path)
    logger.info(f"Loaded {len(df)} player-season rows for training")

    scaler = StandardScaler()
    X = scaler.fit_transform(df[FEATURE_COLUMNS])

    n_clusters = min(N_CLUSTERS, len(df))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    df["cluster"] = kmeans.fit_predict(X)
    cluster_labels = label_clusters(kmeans, scaler)
    logger.info(f"Fit K-Means with {n_clusters} clusters")

    # No separately persisted NearestNeighbors index: the app refits one
    # on-demand in find_similar_players (scoped to whatever pool the user
    # picks), since refitting on ~27k rows is effectively instant — a
    # pretrained index here would just be dead weight.

    joblib.dump(scaler, out_dir / "scaler.joblib")
    joblib.dump(kmeans, out_dir / "kmeans.joblib")
    joblib.dump(cluster_labels, out_dir / "cluster_labels.joblib")
    joblib.dump(FEATURE_COLUMNS, out_dir / "feature_columns.joblib")

    # Canonical, ordered snapshot of exactly what the models were fit on.
    # The app must read this file (not re-query DuckDB) so that positional
    # indices returned by `nn.kneighbors()` still point at the right player.
    df.to_parquet(out_dir / "player_features.parquet", index=False)
    logger.success(f"Saved model artifacts to {out_dir}")


if __name__ == "__main__":
    train()
