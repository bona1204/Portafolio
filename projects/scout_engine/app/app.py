"""Streamlit entry point for the Scout Engine app.

Lets a user search for a player and see statistically similar players,
based on a k-NN index over standardized per-90 xG/xA metrics fitted by
src/models/train.py. The player can be viewed for a single season or as
a minutes-weighted career average across all fetched seasons.

UI rendering only — data loading/caching lives in data.py, and the k-NN
search itself lives in similarity.py.
"""

import sys
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.data import (
    ALL_SEASONS_LABEL,
    DB_PATH,
    MODEL_DIR,
    artifact_mtime,
    build_career_averages,
    display_columns,
    get_active_player_ids,
    league_display_name,
    load_cluster_labels,
    load_kmeans,
    load_mart_table,
    load_player_features,
    load_scaler,
)
from app.similarity import find_similar_players
from src.models.train import FEATURE_COLUMNS

PROJECT_NAME: Final[str] = "Scout Engine"
GITHUB_URL: Final[str] = "https://github.com/bona1204/Portafolio/tree/main/projects/scout_engine"
# TODO: update once the Streamlit Community Cloud app is deployed and its
# real URL is known (see README.md#deployment) — this is a placeholder.
DEMO_URL: Final[str] = "https://share.streamlit.io"
DEFAULT_N_SIMILAR: Final[int] = 5


def render_branding() -> None:
    """Render static sidebar branding (shown on every tab)."""
    with st.sidebar:
        st.title(PROJECT_NAME)
        st.caption("Data Engineering Portfolio")


def render_season_selector(seasons: list[str]) -> str:
    """Render the season selector and return the chosen scope.

    Rendered inline in the Player Explorer tab (not the sidebar) so it
    doesn't leak into the Hidden Gems / Team xG Table tabs, which don't
    use it. Must run before `season_df` is built, since the season choice
    determines which rows go into it.

    Args:
        seasons: All available season values.

    Returns:
        Either ALL_SEASONS_LABEL or a specific season string.
    """
    return st.selectbox("Season", [ALL_SEASONS_LABEL, *sorted(seasons, reverse=True)])


def render_player_controls(season_df: pd.DataFrame) -> tuple[str | None, int]:
    """Render the player search controls inline in the Player Explorer tab.

    The player selectbox already supports typing to search by name, so
    there's no separate league filter here — similar-player search always
    runs across every league anyway, and a league filter that only narrowed
    this dropdown (without also narrowing the comparison pool) was more
    confusing than useful.

    Args:
        season_df: The player rows for the currently selected season scope.

    Returns:
        The selected player's display label (or None) and how many similar
        players to show.
    """
    col1, col2 = st.columns([3, 1])

    with col1:
        player_options = season_df.sort_values("player_name")["player_name"].tolist()
        selected_player = st.selectbox(
            "Player",
            player_options,
            index=None,
            placeholder="Type to search a player...",
        )

    with col2:
        n_similar = st.slider("Similar players to show", min_value=3, max_value=10, value=DEFAULT_N_SIMILAR)

    return selected_player, n_similar


def render_methodology_note() -> None:
    """Render a collapsible explanation of how similarity is computed."""
    with st.expander("How is “similar players” computed?"):
        st.markdown(
            "For every player-season we compute 7 **per-90-minute** rates "
            "(xG, xA, non-penalty xG, shots, key passes, xG chain, xG buildup), "
            "then standardize each one (subtract the dataset mean, divide by "
            "its standard deviation) so no single metric dominates just "
            "because of its raw scale.\n\n"
            "“Similar players” are the closest points to the selected "
            "player in that 7-dimensional standardized space, measured by "
            "Euclidean distance (k-nearest-neighbors). Position isn't an "
            "input to the distance — but because forwards, midfielders and "
            "defenders naturally sit in very different regions of that "
            "space (shot volume, chance creation, etc.), neighbors almost "
            "always end up being players in a similar role.\n\n"
            "**Playstyle cluster** is a related but separate thing: instead "
            "of finding individual closest neighbors, it groups *every* "
            "player-season into 8 broad buckets (via k-means on that same "
            "standardized feature space) ahead of time, and names each "
            "bucket after its 2 strongest features (e.g. \"high xA, key "
            "passes\"). Choosing \"Same playstyle cluster\" as the search "
            "scope below means: only look for similar players inside the "
            "selected player's bucket, rather than across everyone — a "
            "coarser, faster first filter before the precise k-NN distance "
            "narrows it down further."
        )


def render_player_profile(
    season_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    scaler,
    cluster_labels: dict[int, str],
    selected_player: str | None,
    n_similar: int,
    active_player_ids: set,
) -> None:
    """Render the selected player's stats, a comparison chart, and similar players.

    Args:
        season_df: The rows for the currently selected season scope (what
            the player was picked from).
        reference_df: The full per-season feature table (every league,
            every season) — used as the "all seasons" similarity pool and
            as the percentile-rank baseline for the radar chart.
        scaler: The fitted StandardScaler.
        cluster_labels: Mapping from k-means cluster id to a human-readable
            playstyle label (see `src.models.train.label_clusters`).
        selected_player: The chosen player's name, or None if nothing picked yet.
        n_similar: How many similar players to display, excluding the player itself.
        active_player_ids: player_id values present in the most recent
            fetched season — "Active players only" pools are limited to
            these, so retired/departed players don't show up as "active"
            comparables (see get_active_player_ids).
    """
    render_methodology_note()

    if not selected_player:
        st.info("Search for a player above to get started.")
        return

    row = season_df[season_df["player_name"] == selected_player].iloc[0]
    # Same-scope peers: if we're viewing Mbappé's career average, "position
    # average" and "compare with another player" should also default to
    # career averages — not mix in single-season rows.
    position_peers = season_df[season_df["primary_position"] == row["primary_position"]]
    playstyle = cluster_labels[row["cluster"]]

    st.header(row["player_name"])
    scope = "career average" if row["season"] == ALL_SEASONS_LABEL else row["season"]
    st.caption(
        f"{league_display_name(row['league'])} · {row['primary_position']} · "
        f"{scope} · {int(row['minutes_played'])} min · Playstyle: {playstyle}"
    )

    stat_cols = st.columns(len(FEATURE_COLUMNS))
    for col, feature in zip(stat_cols, FEATURE_COLUMNS):
        position_avg = position_peers[feature].mean()
        col.metric(
            feature.replace("_per_90", "").replace("_", " "),
            f"{row[feature]:.2f}",
            delta=f"{row[feature] - position_avg:+.2f} vs {row['primary_position']} avg",
        )

    latest_season = str(reference_df["season"].astype(int).max())

    st.subheader("Statistically similar players")
    st.caption(
        "Two independent choices: **who** is eligible to show up as a match, "
        "and **which season's** numbers to judge them by."
    )
    pool_col, season_col = st.columns([3, 1])

    with pool_col:
        pool_choice = st.radio(
            "Who's eligible",
            [
                "Active players only",
                "Same playstyle cluster",
                "Everyone fetched (incl. retired/departed)",
            ],
            horizontal=True,
            help=(
                f"Playstyle: {playstyle} — 'Same playstyle cluster' narrows eligibility to only "
                "players in this same pre-grouped bucket. See 'How is similar players computed?' "
                "above for the difference between this and the k-NN distance itself. 'Active "
                f"players' means anyone who appeared in the {latest_season} season, regardless "
                "of which season's stats end up being compared (see the Season control)."
            ),
        )

    with season_col:
        all_seasons = sorted(reference_df["season"].unique(), reverse=True)
        season_filter = st.selectbox(
            "Season", [f"Latest ({latest_season})", "Any season (mixed years)", *all_seasons]
        )

    if pool_choice.startswith("Active"):
        pool = reference_df[reference_df["player_id"].isin(active_player_ids)]
    elif pool_choice.startswith("Same playstyle"):
        pool = reference_df[reference_df["cluster"] == row["cluster"]]
    else:
        pool = reference_df

    query_row = row
    if season_filter.startswith("Latest"):
        candidate_pool = pool[pool["season"] == latest_season]
        own_latest = reference_df[
            (reference_df["player_id"] == row["player_id"]) & (reference_df["season"] == latest_season)
        ]
        if own_latest.empty:
            st.info(
                f"{row['player_name']} has no {latest_season} data in this dataset "
                "(retired, departed the top 5 leagues, or injured all season) — "
                "comparing their selected scope's stats against this pool instead."
            )
        else:
            query_row = own_latest.iloc[0]
    elif season_filter.startswith("Any season"):
        candidate_pool = pool
    else:
        candidate_pool = pool[pool["season"] == season_filter]

    similar = find_similar_players(query_row, candidate_pool, scaler, n_similar)

    display_similar = similar.copy()
    display_similar["league"] = display_similar["league"].map(league_display_name)
    st.dataframe(
        display_columns(display_similar[["player_name", "league", "season", *FEATURE_COLUMNS]]).reset_index(
            drop=True
        ),
        use_container_width=True,
    )

    st.subheader("Profile comparison")
    compare_label, compare_values = render_comparison_picker(row, position_peers, similar)
    render_radar_chart(row, reference_df, compare_label, compare_values)


def render_comparison_picker(
    row: pd.Series, position_peers: pd.DataFrame, similar: pd.DataFrame
) -> tuple[str, pd.Series]:
    """Render the "compare against" control and resolve the comparison profile.

    The comparison player is always read from `position_peers`, i.e. the
    same season scope as the top-level Season selector — there's no
    separate season override here, so changing the Season control up top
    consistently moves both the selected player and whoever they're being
    compared against, instead of leaving the comparison pinned to a season
    picked independently inside this widget.

    Args:
        row: The selected player's feature row.
        position_peers: Same-scope peers (career averages, or same-season
            rows) sharing the selected player's primary position — used so
            the comparison stays apples-to-apples with the player's own scope.
        similar: The precomputed nearest neighbors for the selected player.

    Returns:
        A (label, values) tuple, where values holds one number per
        FEATURE_COLUMNS entry to plot alongside the player's own profile.
    """
    mode = st.radio(
        "Compare against",
        [f"{row['primary_position']} average", "Average of similar players", "A specific player"],
        horizontal=True,
    )

    if mode == "A specific player":
        options = position_peers[position_peers["player_name"] != row["player_name"]].sort_values("player_name")
        choice = st.selectbox(
            "Compare with", options["player_name"].tolist(), index=None, placeholder="Type a player name..."
        )
        if choice is None:
            st.info(f"Showing {row['primary_position']} average until you pick a player.")
            return f"{row['primary_position']} average", position_peers[FEATURE_COLUMNS].mean()

        chosen_row = options[options["player_name"] == choice].iloc[0]
        label = choice if row["season"] == ALL_SEASONS_LABEL else f"{choice} ({chosen_row['season']})"
        return label, chosen_row[FEATURE_COLUMNS]

    if mode == "Average of similar players" and not similar.empty:
        return f"Top {len(similar)} similar players (avg)", similar[FEATURE_COLUMNS].mean()

    return f"{row['primary_position']} average", position_peers[FEATURE_COLUMNS].mean()


def render_radar_chart(row: pd.Series, reference_df: pd.DataFrame, compare_label: str, compare_values: pd.Series) -> None:
    """Render a radar (polar) chart comparing the player to a comparison profile.

    Both profiles are converted to percentile ranks (0-100) against the full
    dataset so metrics with very different raw scales (e.g. shots vs. xA)
    are visually comparable on the same axes.

    Args:
        row: The selected player's feature row.
        reference_df: The full player-season feature table, used as the
            percentile-rank baseline.
        compare_label: Display name for the comparison series.
        compare_values: One value per FEATURE_COLUMNS entry to compare against.
    """
    labels = [f.replace("_per_90", "").replace("_", " ") for f in FEATURE_COLUMNS]

    def percentile(value: float, feature: str) -> float:
        return float((reference_df[feature] <= value).mean() * 100)

    player_pct = [percentile(row[f], f) for f in FEATURE_COLUMNS]
    compare_pct = [percentile(compare_values[f], f) for f in FEATURE_COLUMNS]

    PLAYER_COLOR = "#2563eb"  # blue
    COMPARE_COLOR = "#f97316"  # orange — high contrast against blue
    TEXT_COLOR = "#1a1a2e"

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=player_pct + player_pct[:1],
            theta=labels + labels[:1],
            fill="toself",
            name=row["player_name"],
            line=dict(color=PLAYER_COLOR, width=2),
            fillcolor="rgba(37, 99, 235, 0.35)",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=compare_pct + compare_pct[:1],
            theta=labels + labels[:1],
            fill="toself",
            name=compare_label,
            line=dict(color=COMPARE_COLOR, width=2),
            fillcolor="rgba(249, 115, 22, 0.35)",
        )
    )
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color=TEXT_COLOR, size=13),
        polar=dict(
            bgcolor="white",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                ticksuffix="",
                tickfont=dict(color=TEXT_COLOR, size=11),
                gridcolor="rgba(26, 26, 46, 0.15)",
            ),
            angularaxis=dict(tickfont=dict(color=TEXT_COLOR, size=13), gridcolor="rgba(26, 26, 46, 0.15)"),
        ),
        showlegend=True,
        legend=dict(font=dict(color=TEXT_COLOR)),
        margin=dict(t=40, b=20),
    )
    st.caption("Each axis is a percentile rank (0–100) against the full dataset, so metrics on very different scales stay comparable.")
    st.plotly_chart(fig, use_container_width=True)


def render_hidden_gems_tab() -> None:
    """Render the 'Breakout Watch' ranking: FWD/MID players trending up fastest."""
    st.subheader("Breakout Watch")
    st.caption(
        "Forwards and midfielders new to the dataset (at most 3 seasons on "
        "record) whose output jumped the most between the latest season and "
        "the one before — a proxy for 'young and already producing at a "
        "rapidly rising rate,' without needing external market-value data."
    )
    with st.expander("What do these columns mean, and why only forwards and midfielders?"):
        st.markdown(
            "**Understat only tracks shot- and chance-based numbers** — xG, "
            "xA, key passes, etc. — nothing on passing accuracy, defensive "
            "actions, or goalkeeping. So \"output\" here means something "
            "different by position, and is only shown for roles where "
            "these numbers are actually meaningful:\n\n"
            "- **Prior/Latest Season Output (Forwards)**: npxG + xA per 90 "
            "— non-penalty goal threat plus chances created.\n"
            "- **Prior/Latest Season Output (Midfielders)**: xA + Key "
            "Passes per 90 — chance creation, since a midfielder's job is "
            "rarely to shoot.\n"
            "- **Change vs Prior Season**: latest output minus the season "
            "before — a bigger positive number means a bigger year-over-year jump.\n"
            "- **Breakout Percentile**: where that jump ranks against every "
            "other player at the same position (1.0 = biggest jump at that position).\n\n"
            "This still doesn't cover a genuinely **defensive midfielder** — "
            "a 'destroyer' who rarely creates chances won't rank highly here "
            "no matter how good they are, because Understat has no metric "
            "for tackling, ball-winning, or positioning. Goalkeepers and "
            "defenders are excluded outright for the same reason: their "
            "shot/chance numbers are near-zero regardless of quality, so a "
            "year-over-year delta on them would be pure noise, not signal "
            "(an earlier version of this tab compared raw npxG across ALL "
            "positions against a scraped market value, and kept surfacing "
            "goalkeepers and centre-backs as its top \"undervalued\" picks "
            "as a result)."
        )

    try:
        cache_key = artifact_mtime(DB_PATH)
        df = load_mart_table(cache_key, "mart_player_breakout")
    except Exception as exc:
        st.error(f"mart_player_breakout not available yet: {exc}")
        return

    positions = sorted(df["primary_position"].unique())
    selected_positions = st.multiselect("Position", positions, default=positions)
    filtered = df[df["primary_position"].isin(selected_positions)] if selected_positions else df

    display = filtered.sort_values("breakout_percentile", ascending=False).head(25)
    st.dataframe(
        display_columns(
            display[
                [
                    "player_name",
                    "primary_position",
                    "team",
                    "league",
                    "prior_output_per_90",
                    "current_output_per_90",
                    "output_delta",
                    "breakout_percentile",
                ]
            ].assign(league=lambda d: d["league"].map(league_display_name))
        ).reset_index(drop=True),
        use_container_width=True,
    )


def render_team_table_tab() -> None:
    """Render the team-season xG table: actual points vs. performance-vs-xG."""
    st.subheader("Team xG table")
    st.caption(
        "Performance vs xG = Goal Difference minus xG Difference: positive "
        "means a team scored/conceded more favorably than its underlying "
        "chance quality alone would predict (finishing, goalkeeping, or "
        "luck); negative means the opposite."
    )

    try:
        cache_key = artifact_mtime(DB_PATH)
        df = load_mart_table(cache_key, "mart_team_season")
    except Exception as exc:
        st.error(f"mart_team_season not available yet: {exc}")
        return

    leagues = sorted(df["league"].unique())
    col1, col2 = st.columns(2)
    league_choice = col1.selectbox("League", leagues, format_func=league_display_name)
    seasons = sorted(df[df["league"] == league_choice]["season"].unique(), reverse=True)
    season_choice = col2.selectbox("Season", seasons)

    table = df[(df["league"] == league_choice) & (df["season"] == season_choice)].sort_values(
        "points", ascending=False
    )
    st.dataframe(
        display_columns(
            table[
                [
                    "team",
                    "matches_played",
                    "points",
                    "goals_for",
                    "goals_against",
                    "xg_for",
                    "xg_against",
                    "performance_vs_xg",
                ]
            ]
        ).reset_index(drop=True),
        use_container_width=True,
    )


def render_footer() -> None:
    """Render the footer with links to the GitHub repo and live demo."""
    st.divider()
    st.markdown(f"[GitHub]({GITHUB_URL}) · [Demo]({DEMO_URL})")


def main() -> None:
    """Configure the page and render all sections."""
    st.set_page_config(layout="wide", page_title=PROJECT_NAME)
    render_branding()

    player_tab, gems_tab, teams_tab = st.tabs(["Player Explorer", "Hidden Gems", "Team xG Table"])

    with player_tab:
        cache_key = artifact_mtime(
            MODEL_DIR / "scaler.joblib",
            MODEL_DIR / "kmeans.joblib",
            MODEL_DIR / "cluster_labels.joblib",
            MODEL_DIR / "player_features.parquet",
        )

        try:
            scaler = load_scaler(cache_key)
            kmeans = load_kmeans(cache_key)
            cluster_labels = load_cluster_labels(cache_key)
            reference_df = load_player_features(cache_key)
        except FileNotFoundError as exc:
            st.error(str(exc))
        else:
            active_player_ids = get_active_player_ids(reference_df)
            seasons = sorted(reference_df["season"].unique())
            season_choice = render_season_selector(seasons)
            season_df = (
                build_career_averages(reference_df, scaler, kmeans)
                if season_choice == ALL_SEASONS_LABEL
                else reference_df[reference_df["season"] == season_choice]
            )

            selected_player, n_similar = render_player_controls(season_df)
            render_player_profile(
                season_df, reference_df, scaler, cluster_labels, selected_player, n_similar, active_player_ids
            )

    with gems_tab:
        render_hidden_gems_tab()

    with teams_tab:
        render_team_table_tab()

    render_footer()


if __name__ == "__main__":
    main()
