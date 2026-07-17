-- Team-season rollup from match results: actual points earned vs. the
-- points an "xG table" would suggest, i.e. is a team over- or
-- under-performing its underlying chance quality?

with matches as (

    select * from {{ ref('stg_matches') }}

),

team_season as (

    select
        team_id,
        team,
        league,
        season,
        count(*)                       as matches_played,
        sum(points)                    as points,
        sum(goals_for)                 as goals_for,
        sum(goals_against)             as goals_against,
        sum(goals_for) - sum(goals_against)  as goal_diff,
        round(sum(xg_for), 2)          as xg_for,
        round(sum(xg_against), 2)      as xg_against,
        round(sum(xg_for) - sum(xg_against), 2) as xg_diff

    from matches
    group by team_id, team, league, season

)

select
    *,
    -- "Expected points" from an xG-based Poisson table is a whole modeling
    -- exercise on its own; goal_diff - xg_diff is a simpler, directly
    -- interpretable proxy: positive means the team is scoring/conceding
    -- more favorably than its chance quality alone would predict
    -- (finishing well, a strong keeper, or some luck) — negative means
    -- the opposite.
    round(goal_diff - xg_diff, 2) as performance_vs_xg

from team_season
