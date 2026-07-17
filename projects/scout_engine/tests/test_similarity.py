"""Unit tests for app/similarity.py: the k-NN "similar players" search."""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from app.similarity import find_similar_players
from src.models.train import FEATURE_COLUMNS


def _make_df(n: int) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    data = {col: rng.normal(size=n) for col in FEATURE_COLUMNS}
    data["player_id"] = list(range(n))
    return pd.DataFrame(data)


def test_find_similar_players_excludes_the_queried_player():
    df = _make_df(10)
    scaler = StandardScaler().fit(df[FEATURE_COLUMNS])
    row = df.iloc[0]

    result = find_similar_players(row, df, scaler, n_similar=3)

    assert row["player_id"] not in result["player_id"].values
    assert len(result) == 3


def test_find_similar_players_excludes_all_rows_of_the_same_player_id():
    # Simulates a player appearing in the pool across multiple seasons:
    # every row sharing their player_id should be excluded, not just the
    # exact row that was searched from.
    df = _make_df(5)
    duplicate_season = df.iloc[[0]].copy()  # same player_id, identical features
    df = pd.concat([df, duplicate_season], ignore_index=True)

    scaler = StandardScaler().fit(df[FEATURE_COLUMNS])
    row = df.iloc[0]

    result = find_similar_players(row, df, scaler, n_similar=3)

    assert (result["player_id"] == row["player_id"]).sum() == 0


def test_find_similar_players_returns_empty_when_pool_has_no_one_else():
    df = _make_df(1)
    scaler = StandardScaler().fit(df[FEATURE_COLUMNS])
    row = df.iloc[0]

    result = find_similar_players(row, df, scaler, n_similar=3)

    assert result.empty


def test_find_similar_players_caps_at_pool_size():
    df = _make_df(3)  # only 2 other players available
    scaler = StandardScaler().fit(df[FEATURE_COLUMNS])
    row = df.iloc[0]

    result = find_similar_players(row, df, scaler, n_similar=10)

    assert len(result) == 2
