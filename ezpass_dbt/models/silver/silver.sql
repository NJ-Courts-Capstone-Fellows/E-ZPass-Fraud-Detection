{{ config(
    materialized='view',
    tags=['silver'],
) }}

WITH silver_flag AS (
    SELECT * FROM {{ ref('_silver__flag') }}
)

SELECT 
    -- Transaction ID
    transaction_id,
    
    -- Dates
    transaction_date,
    posting_date,
    
    -- Timestamps
    entry_time,
    exit_time,
    
    -- IDs
    tag_plate_number,
    agency,
    agency_name,
    -- Removed description as it only has 'TOLL' as value
    -- description,
    
    -- Entry info
    entry_plaza,
    entry_plaza_name,
    entry_lane,
    
    -- Exit info
    exit_plaza,
    exit_plaza_name,
    exit_lane,
    
    -- Vehicle & fare
    vehicle_type_code,
    plan_rate,
    fare_type,
    
    -- Financial
    amount,
    -- Removed prepaid as it only has 'Y' as value
    -- prepaid,
    balance,
    
    -- New features
    daily_count,
    state_name,
    transaction_dayofweek,
    transaction_dayofyear,
    transaction_month,
    transaction_day,
    entry_time_of_day,
    exit_time_of_day,
    journey_time_of_day,
    entry_hour,
    exit_hour,
    travel_duration_category,
    vehicle_class_category,

    -- Flags
    flag_is_weekend,
    flag_is_out_of_state,
    flag_is_vehicle_type_gt2,
    flag_is_holiday,
    is_missing_entry_plaza,
    is_missing_exit_plaza,
    is_missing_entry_time,
    is_missing_exit_time,

    -- Metadata (last)
    loaded_at as last_updated,
    source_file

FROM silver_flag