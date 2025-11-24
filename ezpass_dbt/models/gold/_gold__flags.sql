{{ config(
    materialized='ephemeral',
    tags=['gold', 'base']
) }}

WITH aggregated_features AS (
    SELECT * FROM {{ ref('_gold__agg') }}
),

driver_prev_transaction_count AS (
    SELECT
    *,
    COUNT(*) OVER (
        PARTITION BY tag_plate_number
        ORDER BY COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))
        ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
    ) AS driver_num_prior_txns

    FROM aggregated_features
),

driver_flags AS (
    SELECT
        *,
        CASE WHEN driver_amount_modified_z_score > 1 AND amount >= 10 THEN TRUE ELSE FALSE 
        END as flag_driver_amount_outlier,

        CASE WHEN ABS(route_amount_z_score) > 1 THEN TRUE ELSE FALSE 
        END as flag_route_amount_outlier,
        
        CASE WHEN amount_deviation_from_avg_pct > 80 
            OR amount_deviation_from_median_pct > 80 THEN TRUE ELSE FALSE -- 80% deviation from average or median
        END as flag_amount_unusually_high,

        -- Could add flag_unusually_low here if needed
        
        -- Flag for spending spike (daily spend > 3x average and amount >= $20)
        CASE 
            WHEN driver_avg_daily_spend_30d IS NOT NULL 
                AND (
                    driver_today_spend > (3 * driver_avg_daily_spend_30d)
                    OR driver_today_spend = driver_amount_last_30txn_max
                )
                AND amount >= 50
            THEN TRUE
            ELSE FALSE
        END as flag_driver_spend_spike,

        CASE state_name
            WHEN 'NJ' THEN FALSE
            ELSE TRUE
        END as flag_is_out_of_state,

        CASE
            WHEN amount >= 29
            THEN TRUE
            ELSE FALSE
        END as flag_amount_gt_29
        
    FROM driver_prev_transaction_count
),

final_flags AS (
    SELECT
    *,
    CASE 
            WHEN flag_is_weekend = TRUE
            or flag_is_out_of_state = TRUE
            or flag_amount_gt_29 = TRUE
            or flag_vehicle_type = TRUE
            or flag_is_holiday = TRUE
            THEN TRUE
            ELSE FALSE
        END as flag_fraud
    FROM driver_flags
)

SELECT * FROM final_flags


