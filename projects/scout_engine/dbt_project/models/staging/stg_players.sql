-- Reads the raw Understat player-season Parquet files written by
-- src/pipeline/fetch_data.py and standardizes column names/types.
-- One row per player, per league, per season.

with source as (

    select *
    from read_parquet('{{ var("raw_data_path", "../data/raw") }}/*.parquet', filename = true)

),

renamed as (

    select
        cast(id as bigint)              as player_id,
        player_name,
        position                        as raw_position,
        team_title                      as team,
        cast(games as integer)          as games_played,
        cast(time as integer)           as minutes_played,
        cast(goals as integer)          as goals,
        cast(xG as double)              as xg,
        cast(assists as integer)        as assists,
        cast(xA as double)              as xa,
        cast(shots as integer)          as shots,
        cast(key_passes as integer)     as key_passes,
        cast(yellow_cards as integer)   as yellow_cards,
        cast(red_cards as integer)      as red_cards,
        cast(npg as integer)            as non_penalty_goals,
        cast(npxG as double)            as npxg,
        cast(xGChain as double)         as xg_chain,
        cast(xGBuildup as double)       as xg_buildup,
        -- filename encodes ".../{league}_{season}.parquet", e.g. "la_liga_2023.parquet".
        -- Season is always the trailing 4-digit year, so split on that rather than
        -- on the first "_" (league codes like "la_liga" contain underscores too).
        regexp_replace(regexp_extract(filename, '([^/\\]+)$'), '_[0-9]{4}\.parquet$', '') as league,
        regexp_extract(filename, '_([0-9]{4})\.parquet$', 1) as season,
        cast(fetched_at as timestamp) as fetched_at

    from source

)

select * from renamed
