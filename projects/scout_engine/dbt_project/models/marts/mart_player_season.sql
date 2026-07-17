-- Per-90-minute player profile, the feature set consumed by the
-- similarity/clustering model in src/models/train.py.
-- Filters out low-minute samples that make per-90 rates unstable.
--
-- Incremental: each `dbt run` only reprocesses rows from the most recent
-- fetch_data.py run (fetched_at newer than what's already in this table),
-- instead of recomputing the full 27k-row history every time. A player
-- re-fetched for the same league/season (e.g. stats updated mid-season)
-- replaces their existing row via the unique_key below.

{{
    config(
        materialized='incremental',
        unique_key=['player_id', 'league', 'season'],
        incremental_strategy='delete+insert',
    )
}}

with staged as (

    select * from {{ ref('stg_players') }}

    {% if is_incremental() %}
    where fetched_at > (select coalesce(max(fetched_at), '1900-01-01') from {{ this }})
    {% endif %}

),

min_minutes_filtered as (

    select *
    from staged
    -- Validated against src/models/train.py's k-means step: silhouette score
    -- at 450/630/900-minute cutoffs is 0.285/0.272/0.287 (within +/-0.003
    -- sampling noise across 5 seeds at each), so raising the threshold buys
    -- no real cluster separation — 450 min (~5 full matches) is kept since
    -- it retains ~5,300 more player-seasons than 900 for the same quality.
    where minutes_played >= 450

),

per_90 as (

    select
        player_id,
        player_name,
        team,
        -- Understat's raw position string looks like "F S" (forward, sub) or
        -- "D M" (played both defense and midfield) — take the first token's
        -- leading letter as the primary position bucket for grouping/filtering.
        case
            when raw_position ilike 'GK%' then 'GK'
            when raw_position ilike 'D%'  then 'DEF'
            when raw_position ilike 'M%'  then 'MID'
            when raw_position ilike 'F%'  then 'FWD'
            else 'UNK'
        end as primary_position,
        league,
        season,
        fetched_at,
        minutes_played,
        goals,
        assists,
        round(xg / (minutes_played / 90.0), 3)         as xg_per_90,
        round(xa / (minutes_played / 90.0), 3)          as xa_per_90,
        round(npxg / (minutes_played / 90.0), 3)        as npxg_per_90,
        round(shots / (minutes_played / 90.0), 3)       as shots_per_90,
        round(key_passes / (minutes_played / 90.0), 3)  as key_passes_per_90,
        round(xg_chain / (minutes_played / 90.0), 3)    as xg_chain_per_90,
        round(xg_buildup / (minutes_played / 90.0), 3)  as xg_buildup_per_90

    from min_minutes_filtered

)

select * from per_90
