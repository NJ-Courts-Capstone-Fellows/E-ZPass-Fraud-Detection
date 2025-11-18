{{ config(
    materialized='ephemeral',
    tags=['silver', 'intermediate']
) }}

WITH base_features AS (
    SELECT * FROM {{ ref('_silver__feateng') }}
),


distance_lookup AS (
    SELECT * FROM {{ source('raw', 'address_to_miles') }}
),

-- Extract all in-state plazas (plazas that appear in origin_plaza column)
instate_plazas AS (
    SELECT DISTINCT origin_plaza as plaza_name
    FROM distance_lookup
),

-- Add route sequence features
route_sequence AS (
    SELECT
        *,
        
        -- Previous exit plaza for this driver (useful for route pattern analysis)
        -- Replace NULL with 'Unknown'
        COALESCE(
            LAG(exit_plaza) OVER (
                PARTITION BY tag_plate_number 
                ORDER BY transaction_date, COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))
            ),
            'Unknown'
        ) as exit_plaza_previous

    FROM base_features
),

-- Build route string with cleaned plazas
route_features AS (
    SELECT
        *,
        
        -- Route from previous exit to current exit
        CONCAT(
            COALESCE(exit_plaza, 'Unknown'), 
            ' to ', 
            exit_plaza_previous
        ) as plaza_route

    FROM route_sequence
),

-- Add route classification features
check_route AS (
    SELECT
        rf.*,

        CASE
            -- If either plaza is Unknown or NULL, route classification is Unknown
            WHEN rf.exit_plaza IS NULL OR rf.exit_plaza = 'Unknown' 
                 OR rf.exit_plaza_previous IS NULL OR rf.exit_plaza_previous = 'Unknown' 
            THEN 'Unknown'
            -- Both plazas must be in-state for route to be In-state
            WHEN rf.exit_plaza IN (SELECT plaza_name FROM instate_plazas)
                 AND rf.exit_plaza_previous IN (SELECT plaza_name FROM instate_plazas)
            THEN 'In-state'
            ELSE 'Out-state'
        END as route_instate
        
    FROM route_features rf
)

SELECT * FROM check_route

