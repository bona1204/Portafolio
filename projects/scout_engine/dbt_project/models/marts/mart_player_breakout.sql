-- "Breakout Watch": which FWD/MID players jumped the most in their
-- position-appropriate output metric between the two most recent
-- absolute seasons in the dataset? Self-joins mart_player_season to
-- itself (current season vs. the prior one) to compute that
-- year-over-year delta directly in SQL.
--
-- The output metric differs by position because Understat only tracks
-- shot- and chance-based numbers (xG, xA, key passes, etc.) — nothing on
-- passing accuracy, defensive actions, or goalkeeping. That's a real
-- signal for forwards (goal threat) and for midfielders (chance
-- creation), so FWD uses npxG+xA and MID uses xA+key passes. It's NOT a
-- meaningful signal for a genuinely defensive midfielder (a "destroyer"
-- who rarely creates chances won't show up here regardless of how good
-- they are — Understat simply has no defensive metric to detect that),
-- and it's close to zero for GK/DEF regardless of quality, which is why
-- this model excludes those positions entirely rather than fabricating
-- a score from data that doesn't measure what they do (an earlier
-- version compared raw npxG across ALL positions against a scraped
-- market value, and kept surfacing goalkeepers and centre-backs as its
-- top "undervalued" picks as a result).
--
-- "Breakout" here also requires the player to be new-ish to the dataset
-- (at most 3 seasons on record) — without a birthdate we don't have real
-- age data from Understat, so total seasons observed is the closest proxy
-- for "hasn't been around long enough to already be widely known."

with seasons as (

    select
        player_id,
        player_name,
        team,
        league,
        primary_position,
        cast(season as integer) as season,
        minutes_played,
        case
            when primary_position = 'FWD' then npxg_per_90 + xa_per_90
            when primary_position = 'MID' then xa_per_90 + key_passes_per_90
        end as output_per_90

    from {{ ref('mart_player_season') }}
    where primary_position in ('FWD', 'MID')

),

current_season as (

    select * from seasons
    where season = (select max(season) from seasons)

),

prior_season as (

    select * from seasons
    where season = (select max(season) from seasons) - 1

),

tenure as (

    -- Total seasons on record per player, across ALL positions/leagues —
    -- a player who only just started appearing in this dataset.
    select player_id, count(distinct season) as seasons_on_record
    from {{ ref('mart_player_season') }}
    group by player_id

),

joined as (

    select
        cur.player_id,
        cur.player_name,
        cur.team,
        cur.league,
        cur.primary_position,
        cur.season as latest_season,
        cur.minutes_played,
        cur.output_per_90 as current_output_per_90,
        prior.output_per_90 as prior_output_per_90,
        cur.output_per_90 - prior.output_per_90 as output_delta,
        t.seasons_on_record

    from current_season cur
    inner join prior_season prior using (player_id)
    inner join tenure t using (player_id)
    where t.seasons_on_record <= 3

)

select
    *,
    round(percent_rank() over (partition by primary_position order by output_delta), 3) as breakout_percentile
from joined
order by breakout_percentile desc
