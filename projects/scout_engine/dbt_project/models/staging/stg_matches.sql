-- Reads the raw Understat match-result Parquet files written by
-- src/pipeline/fetch_data.py:fetch_match_data(). One row per match,
-- unpivoted into one row per (match, side) so home and away can be
-- aggregated identically in the team-season mart.

with source as (

    select *
    from read_parquet('{{ var("raw_matches_path", "../data/raw_matches") }}/*.parquet', filename = true)
    where isResult  -- drop unplayed/future fixtures

),

with_season as (

    select
        *,
        -- filename encodes ".../{league}_{season}.parquet"
        regexp_replace(regexp_extract(filename, '([^/\\]+)$'), '_[0-9]{4}\.parquet$', '') as league,
        regexp_extract(filename, '_([0-9]{4})\.parquet$', 1) as season

    from source

),

unpivoted as (

    select
        cast(id as bigint)         as match_id,
        league,
        season,
        cast(datetime as timestamp) as kickoff_at,
        cast(h.id as bigint)       as team_id,
        h.title                    as team,
        cast(a.id as bigint)       as opponent_id,
        a.title                    as opponent,
        'home'                     as venue,
        cast(goals.h as integer)   as goals_for,
        cast(goals.a as integer)   as goals_against,
        cast(xG.h as double)       as xg_for,
        cast(xG.a as double)       as xg_against,
        fetched_at
    from with_season

    union all

    select
        cast(id as bigint)         as match_id,
        league,
        season,
        cast(datetime as timestamp) as kickoff_at,
        cast(a.id as bigint)       as team_id,
        a.title                    as team,
        cast(h.id as bigint)       as opponent_id,
        h.title                    as opponent,
        'away'                     as venue,
        cast(goals.a as integer)   as goals_for,
        cast(goals.h as integer)   as goals_against,
        cast(xG.a as double)       as xg_for,
        cast(xG.h as double)       as xg_against,
        fetched_at
    from with_season

)

select
    *,
    case
        when goals_for > goals_against then 3
        when goals_for = goals_against then 1
        else 0
    end as points
from unpivoted
