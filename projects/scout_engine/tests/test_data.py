"""Unit tests for app/data.py: display formatting and pandas aggregation logic."""

import pandas as pd
import pytest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from app.data import build_career_averages, display_columns, get_active_player_ids, league_display_name
from src.models.train import FEATURE_COLUMNS


def test_league_display_name_known_code():
    assert league_display_name("la_liga") == "La Liga"


def test_league_display_name_unknown_code_falls_back_to_title_case():
    assert league_display_name("eredivisie") == "Eredivisie"


def test_display_columns_maps_known_names_and_title_cases_unknown():
    df = pd.DataFrame({"player_name": ["A"], "xg_per_90": [0.5], "some_new_col": [1]})
    renamed = display_columns(df)
    assert list(renamed.columns) == ["Player", "xG per 90", "Some New Col"]


def _feature_rows(n: int) -> dict:
    return {col: [0.0] * n for col in FEATURE_COLUMNS}


def test_build_career_averages_weights_by_minutes_played():
    # Same player, 2 seasons: 900 min at xg_per_90=1.0, 2700 min at 0.0.
    # Minutes-weighted average should be (1.0*900 + 0.0*2700) / 3600 = 0.25.
    df = pd.DataFrame(
        {
            "player_id": [1, 1],
            "player_name": ["Test Player", "Test Player"],
            "team": ["Team A", "Team B"],
            "primary_position": ["FWD", "FWD"],
            "league": ["epl", "epl"],
            "season": ["2020", "2021"],
            "minutes_played": [900, 2700],
            **_feature_rows(2),
        }
    )
    df["xg_per_90"] = [1.0, 0.0]

    scaler = StandardScaler().fit(df[FEATURE_COLUMNS])
    kmeans = KMeans(n_clusters=1, random_state=0, n_init="auto").fit(scaler.transform(df[FEATURE_COLUMNS]))

    out = build_career_averages(df, scaler, kmeans)

    assert len(out) == 1
    assert out.loc[0, "xg_per_90"] == pytest.approx(0.25)
    assert out.loc[0, "minutes_played"] == 3600
    # "team" should come from the most recent season (2021), not the first.
    assert out.loc[0, "team"] == "Team B"
    assert "cluster" in out.columns


def test_build_career_averages_keeps_one_row_per_player():
    df = pd.DataFrame(
        {
            "player_id": [1, 1, 2],
            "player_name": ["A", "A", "B"],
            "team": ["X", "X", "Y"],
            "primary_position": ["FWD", "FWD", "MID"],
            "league": ["epl", "epl", "epl"],
            "season": ["2020", "2021", "2020"],
            "minutes_played": [900, 900, 900],
            **_feature_rows(3),
        }
    )
    scaler = StandardScaler().fit(df[FEATURE_COLUMNS])
    kmeans = KMeans(n_clusters=1, random_state=0, n_init="auto").fit(scaler.transform(df[FEATURE_COLUMNS]))

    out = build_career_averages(df, scaler, kmeans)

    assert sorted(out["player_id"].tolist()) == [1, 2]


def test_get_active_player_ids_limited_to_latest_season():
    df = pd.DataFrame({"player_id": [1, 2], "season": ["2024", "2023"]})
    assert get_active_player_ids(df) == {1}
