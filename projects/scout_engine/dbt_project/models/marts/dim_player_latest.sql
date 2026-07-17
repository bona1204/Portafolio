-- One row per player: their most recently observed team/league/position.
-- This is the thing that actually changes between pipeline runs (a
-- mid-season transfer, a re-fetch picking up updated stats) — snapshots/
-- player_team_snapshot.sql tracks its history as a Type-2 SCD.

with ranked as (

    select
        *,
        row_number() over (
            partition by player_id
            order by season desc, fetched_at desc
        ) as rn

    from {{ ref('mart_player_season') }}

)

select
    player_id,
    player_name,
    team,
    league,
    primary_position,
    season as latest_season,
    fetched_at
from ranked
where rn = 1
