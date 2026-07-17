{% snapshot player_team_snapshot %}

{{
    config(
        target_schema='main',
        unique_key='player_id',
        strategy='check',
        check_cols=['team', 'league', 'primary_position'],
    )
}}

-- Type-2 SCD over each player's current team/league/position. Every time
-- `dbt snapshot` runs after a fresh fetch_data.py + dbt run, a changed
-- value here (a transfer window, a re-fetch that picks up a mid-season
-- move) gets a new row with dbt_valid_from/dbt_valid_to, instead of
-- silently overwriting the old one — e.g. "which club was this player at
-- on 2025-01-15" stays answerable after the fact.
select * from {{ ref('dim_player_latest') }}

{% endsnapshot %}
