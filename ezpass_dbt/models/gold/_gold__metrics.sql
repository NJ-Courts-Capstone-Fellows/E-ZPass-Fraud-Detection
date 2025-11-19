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
        NULL AS status,
        ARRAY_TO_STRING(
        ARRAY_CONCAT(
            IF(flag_is_weekend = TRUE, ['flag_is_weekend'], []),
            IF(flag_is_out_of_state = TRUE, ['flag_is_out_of_state'], []),
            IF(flag_vehicle_type_class = TRUE, ['flag_vehicle_type_class'], []),
            IF(flag_is_holiday = TRUE, ['flag_is_holiday'], []),
            IF(flag_possible_cloning = TRUE, ['flag_possible_cloning'], [])
        ),
        ', '
    ) AS triggered_flags,

        CASE
            WHEN flag_vehicle_type_class = TRUE THEN 'High'
            WHEN flag_possible_cloning = TRUE THEN ' Medium'
            WHEN flag_is_out_of_state = TRUE THEN 'Medium'
            WHEN flag_is_weekend = TRUE THEN 'Low'
            WHEN flag_is_holiday = TRUE THEN 'Low'
        END as threat_severity,

            
        CASE 
            WHEN flag_is_weekend = TRUE
            or flag_is_out_of_state = TRUE
            or flag_vehicle_type_class = TRUE
            or flag_is_holiday = TRUE
            or flag_possible_cloning = TRUE
            THEN TRUE
            ELSE FALSE
        END as flag_fraud
       
    FROM aggregation
)

SELECT * FROM metrics