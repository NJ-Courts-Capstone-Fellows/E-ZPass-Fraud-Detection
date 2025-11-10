{{ config(
    materialized='ephemeral',
    tags=['gold', 'intermediate']
) }}

WITH aggregation AS (
    SELECT * FROM {{ ref('_gold__aggregation') }}
),

metrics AS (
    SELECT
        *,
        CASE
            WHEN flag_is_vehicle_type_gt2 = TRUE THEN 'High'
            WHEN flag_is_out_of_state = TRUE THEN 'Medium'
            WHEN flag_is_weekend = TRUE THEN 'Low'
            WHEN flag_is_holiday = TRUE THEN 'Low'
        END as threat_severity,

            
        CASE 
            WHEN flag_is_weekend = TRUE
            or flag_is_out_of_state = TRUE
            or flag_is_vehicle_type_gt2 = TRUE
            or flag_is_holiday = TRUE
            THEN TRUE
            ELSE FALSE
        END as flag_fraud
       
    FROM aggregation
)

SELECT * FROM metrics