"""Data ingestion pipeline for Scout Engine.

Pulls two things from Understat for the 6 supported European leagues:
- Season-level player xG data (fetch_data) -> data/raw/
- Match-level team results + xG (fetch_match_data) -> data/raw_matches/

Both stamp a `fetched_at` column so downstream incremental dbt models
can tell which rows arrived in which pipeline run.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Final

import pandas as pd
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from understatapi import UnderstatClient

LEAGUES: Final[list[str]] = [
    "EPL",
    "La_Liga",
    "Ligue_1",
    "Serie_A",
    "Bundesliga",
    "RFPL",
]

RAW_DATA_DIR: Final[Path] = Path("data/raw")
RAW_MATCHES_DIR: Final[Path] = Path("data/raw_matches")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _fetch_league_players(client: UnderstatClient, league: str, season: str) -> pd.DataFrame:
    """Fetch player-level season data for a single league, with retries.

    Args:
        client: An open UnderstatClient session.
        league: Understat league code, e.g. "EPL", "La_Liga".
        season: Season start year as a string, e.g. "2023".

    Returns:
        A DataFrame of player season stats for the given league/season.
    """
    logger.info(f"Fetching {league} players for season {season}")
    raw = client.league(league=league).get_player_data(season=season)
    return pd.DataFrame(raw)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _fetch_league_matches(client: UnderstatClient, league: str, season: str) -> pd.DataFrame:
    """Fetch match-level results and xG for a single league, with retries.

    Args:
        client: An open UnderstatClient session.
        league: Understat league code, e.g. "EPL", "La_Liga".
        season: Season start year as a string, e.g. "2023".

    Returns:
        A DataFrame of match results for the given league/season.
    """
    logger.info(f"Fetching {league} matches for season {season}")
    raw = client.league(league=league).get_match_data(season=season)
    return pd.DataFrame(raw)


def fetch_data(seasons: list[str], leagues: list[str] = LEAGUES, out_dir: Path = RAW_DATA_DIR) -> None:
    """Fetch player xG data for the given leagues/seasons and write it to data/raw/.

    Args:
        seasons: Season start years to fetch, e.g. ["2021", "2022", "2023"].
        leagues: Understat league codes to fetch. Defaults to all 6 supported leagues.
        out_dir: Directory to write the raw Parquet files to.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc)

    with UnderstatClient() as client:
        for league in leagues:
            for season in seasons:
                try:
                    df = _fetch_league_players(client, league, season)
                except Exception as exc:
                    logger.error(f"Failed to fetch {league} {season} after retries: {exc}")
                    continue

                if df.empty:
                    logger.warning(f"No data returned for {league} {season}")
                    continue

                df["fetched_at"] = fetched_at
                out_path = out_dir / f"{league.lower()}_{season}.parquet"
                df.to_parquet(out_path, index=False)
                logger.success(f"Wrote {len(df)} rows to {out_path}")


def fetch_match_data(seasons: list[str], leagues: list[str] = LEAGUES, out_dir: Path = RAW_MATCHES_DIR) -> None:
    """Fetch match-level results and xG for the given leagues/seasons.

    Args:
        seasons: Season start years to fetch, e.g. ["2021", "2022", "2023"].
        leagues: Understat league codes to fetch. Defaults to all 6 supported leagues.
        out_dir: Directory to write the raw Parquet files to.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc)

    with UnderstatClient() as client:
        for league in leagues:
            for season in seasons:
                try:
                    df = _fetch_league_matches(client, league, season)
                except Exception as exc:
                    logger.error(f"Failed to fetch {league} {season} matches after retries: {exc}")
                    continue

                if df.empty:
                    logger.warning(f"No match data returned for {league} {season}")
                    continue

                df["fetched_at"] = fetched_at
                out_path = out_dir / f"{league.lower()}_{season}.parquet"
                df.to_parquet(out_path, index=False)
                logger.success(f"Wrote {len(df)} match rows to {out_path}")


if __name__ == "__main__":
    # Understat has covered these 6 leagues since the 2014/15 season.
    seasons = [str(year) for year in range(2014, 2026)]
    fetch_data(seasons=seasons)
    fetch_match_data(seasons=seasons)
