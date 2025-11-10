{{ config(
    materialized='table',
    tags=['gold'],
) }}

WITH metrics AS (
    SELECT * FROM {{ ref('_gold__metrics') }}
)

SELECT 
    tag_plate_number,
        transaction_date,
        daily_count,
        state_name,
        agency,
        agency_name,
    
        entry_time,
        entry_plaza,
        entry_plaza_name,

        exit_time,
        exit_plaza,
        exit_plaza_name,

        vehicle_type_code,
        vehicle_class_category,

        fare_type,
        amount,

        flag_is_weekend,
        flag_is_out_of_state,
        flag_is_vehicle_type_gt2,
        flag_is_holiday,
        flag_fraud,
        threat_severity,

        last_updated,
        source_file,
    
        ------Existing Features------
        --plan_rate,
        --prepaid,
        --posting_date,
        --description,
        --entry_lane,
        --exit_lane,

        ------New Features------
        --transaction_dayofweek,
        --transaction_dayofyear,
        --transaction_month,
        --transaction_day,
        --entry_time_of_day,
        --exit_time_of_day,
        --journey_time_of_day,
        --entry_hour,
        --exit_hour,
        --travel_duration_category,

FROM metrics