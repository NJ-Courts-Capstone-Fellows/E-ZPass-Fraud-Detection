{{ config(
    materialized='ephemeral',
    tags=['silver', 'intermediate']
) }}

WITH base_features AS (
    SELECT * FROM {{ ref('_silver__feateng_route') }}
),

price_features AS (
    SELECT
        *,
        
        -- Rolling average toll amount over last 30 transactions per driver
        AVG(amount) OVER (
            PARTITION BY tag_plate_number 
            ORDER BY transaction_date, COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) as amount_last_30txn_avg,
        
        -- Rolling standard deviation of toll amounts over last 30 transactions per driver
        STDDEV(amount) OVER (
            PARTITION BY tag_plate_number 
            ORDER BY transaction_date, COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) as amount_last_30txn_std,
        
        -- Rolling minimum toll amount over last 30 transactions per driver
        MIN(amount) OVER (
            PARTITION BY tag_plate_number 
            ORDER BY transaction_date, COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) as amount_last_30txn_min,
        
        -- Rolling maximum toll amount over last 30 transactions per driver
        MAX(amount) OVER (
            PARTITION BY tag_plate_number 
            ORDER BY transaction_date, COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) as amount_last_30txn_max,
        
        -- Rolling count of transactions (useful for normalization)
        COUNT(*) OVER (
            PARTITION BY tag_plate_number 
            ORDER BY transaction_date, COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) as amount_last_30txn_count

    FROM base_features
),

-- Calculate plaza-level statistics using window functions
plaza_amount AS (
    SELECT
        pf.*,
        AVG(pf.amount) OVER (
            PARTITION BY pf.plaza_route
        ) as route_amount_avg,
        STDDEV(pf.amount) OVER (
            PARTITION BY pf.plaza_route
        ) as route_amount_std,
        MIN(pf.amount) OVER (
            PARTITION BY pf.plaza_route
        ) as route_amount_min,
        MAX(pf.amount) OVER (
            PARTITION BY pf.plaza_route
        ) as route_amount_max
    FROM price_features pf
)

SELECT * FROM plaza_amount