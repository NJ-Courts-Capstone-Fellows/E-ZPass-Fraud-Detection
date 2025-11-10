
  
    

    create or replace table `njc-ezpass`.`ezpass_data`.`gold`
      
    
    

    
    OPTIONS()
    as (
      

WITH  __dbt__cte___gold__aggregation as (


WITH source AS (
    SELECT * FROM `njc-ezpass`.`ezpass_data`.`silver`
),

aggregation AS (
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

    FROM source
)

SELECT * FROM aggregation
),  __dbt__cte___gold__metrics as (


WITH aggregation AS (
    SELECT * FROM __dbt__cte___gold__aggregation
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
), metrics AS (
    SELECT * FROM __dbt__cte___gold__metrics
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
    );
  