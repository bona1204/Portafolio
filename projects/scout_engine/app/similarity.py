"""k-NN "find similar players" search over the standardized feature space.

Split out of app.py so this logic can be unit-tested directly (with plain
DataFrames and a fitted scaler) without going through Streamlit.
"""

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from src.models.train import FEATURE_COLUMNS


def compute_query_point(row: pd.Series, scaler) -> np.ndarray:
    """Standardize a single player's feature row into the model's input space.

    Args:
        row: A player feature row (must contain all FEATURE_COLUMNS).
        scaler: The fitted StandardScaler.

    Returns:
        A (1, n_features) standardized array, ready for `nn.kneighbors()`.
    """
    return scaler.transform(row[FEATURE_COLUMNS].to_frame().T.astype(float))


def find_similar_players(row: pd.Series, candidate_pool: pd.DataFrame, scaler, n_similar: int) -> pd.DataFrame:
    """Find the k nearest neighbors to a player within a candidate pool.

    Fits a fresh NearestNeighbors index on the given pool each call rather
    than reusing a single pretrained index — the pool changes depending on
    which scope the user picks, and refitting on ~27k rows is effectively
    instant.

    The player's own rows are excluded from the pool (by player_id, not
    just the currently-viewed row) *before* fitting: when searching across
    "all seasons", a player's own prior/later seasons are usually the
    closest points to them, and used to eat into the n_similar budget —
    e.g. asking for 5 similar players could silently return only 3 if 2 of
    the nearest neighbors turned out to be the same player in other years.

    Args:
        row: The selected player's feature row.
        candidate_pool: The rows to search within (e.g. season_df for
            "active players only", or reference_df for "all seasons").
        scaler: The fitted StandardScaler.
        n_similar: How many neighbors to return.

    Returns:
        The n_similar closest rows in candidate_pool, excluding the player themself.
    """
    others = candidate_pool[candidate_pool["player_id"] != row["player_id"]]
    if others.empty:
        return others

    X = scaler.transform(others[FEATURE_COLUMNS].astype(float))
    k = min(n_similar, len(others))
    nn = NearestNeighbors(n_neighbors=k, metric="euclidean").fit(X)

    query_point = compute_query_point(row, scaler)
    _, neighbor_idx = nn.kneighbors(query_point)
    return others.iloc[neighbor_idx[0]].copy()
