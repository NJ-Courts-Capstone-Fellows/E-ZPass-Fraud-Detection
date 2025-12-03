{{ config(
    materialized='ephemeral',
    tags=['gold', 'base']
) }}

WITH flags AS (
    SELECT * FROM {{ ref('_gold__flags') }}
),

anomaly_scoring AS (
    SELECT
        *,
        
        -- Weighted anomaly score: sum of flag weights
        (
            CASE WHEN flag_amount_gt_29 = TRUE THEN 50 ELSE 0 END +
            CASE WHEN flag_vehicle_type = TRUE THEN 30 ELSE 0 END +
            CASE WHEN flag_is_out_of_state = TRUE THEN 15 ELSE 0 END +
            CASE WHEN flag_is_weekend = TRUE THEN 2 ELSE 0 END +
            CASE WHEN flag_is_holiday = TRUE THEN 3 ELSE 0 END
        ) AS rule_based_score
    FROM flags
),

threat_severity AS (

        -- Score interpretation:
        -- 0: No anomalies detected
        -- 5-15: Low risk
        -- 15-30: Medium risk
        -- 30-50: High risk
        -- 50+: Critical risk
    SELECT
    *,
    CASE 
        WHEN rule_based_score >= 30 THEN 'Critical Risk'
        WHEN rule_based_score >= 15 THEN 'Medium Risk'
        WHEN rule_based_score >= 2 THEN 'Low Risk'
        ELSE 'No Risk'
    END AS threat_severity

    FROM anomaly_scoring
),

status AS (
    SELECT
    *,
    CASE 
        WHEN flag_fraud = TRUE THEN 'Needs Review'
        ELSE 'No Action Required'
    END AS status

    FROM threat_severity
)


SELECT * FROM status

