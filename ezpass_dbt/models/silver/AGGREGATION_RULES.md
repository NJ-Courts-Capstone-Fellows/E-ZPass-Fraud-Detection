# Silver Layer Aggregation Rules Documentation

This document maps the aggregation rules that create parameters in the silver layer of the E-ZPass Fraud Detection data pipeline.

## Overview

The silver layer transforms cleaned bronze data into enriched features through a series of intermediate models. Each model builds upon the previous one, creating aggregated parameters using window functions, lookups, and calculated fields.

## Execution Pipeline

The silver layer models execute in the following order:

```
_silver__cleaning.sql
    ↓
_silver__enrichment.sql
    ↓
_silver__feateng.sql
    ↓
_silver__feateng_route.sql
    ↓
_silver__feateng_price.sql
    ↓
_silver__flag.sql
    ↓
silver.sql (final table)
```

---

## Model 1: `_silver__feateng.sql`

**Purpose**: Base feature engineering - creates time-based features and driver-level aggregations

**Input**: `_silver__enrichment`

### Aggregation Rules

#### 1. Driver Daily Transaction Count
- **Parameter**: `driver_daily_txn_count`
- **Type**: Integer
- **Aggregation Method**: Window function
- **Formula**: 
  ```sql
  COUNT(*) OVER (PARTITION BY tag_plate_number, transaction_date)
  ```
- **Description**: Counts the total number of transactions per driver per day

#### 2. Weekend/Weekday Classification
- **Parameter**: `weekend_or_weekday`
- **Type**: String ('Weekend' | 'Weekday')
- **Aggregation Method**: CASE statement
- **Formula**:
  ```sql
  CASE 
      WHEN EXTRACT(DAYOFWEEK FROM transaction_date) IN (1, 7) THEN 'Weekend'
      ELSE 'Weekday'
  END
  ```
- **Description**: Classifies transaction date as weekend or weekday

#### 3. Rush Hour Flag
- **Parameter**: `flag_rush_hour`
- **Type**: Boolean
- **Aggregation Method**: CASE statement
- **Formula**:
  ```sql
  CASE 
      WHEN (EXTRACT(HOUR FROM entry_time) BETWEEN 6 AND 8) 
           OR (EXTRACT(HOUR FROM entry_time) BETWEEN 15 AND 18)
           OR (EXTRACT(HOUR FROM exit_time) BETWEEN 6 AND 8) 
           OR (EXTRACT(HOUR FROM exit_time) BETWEEN 15 AND 18)
      THEN TRUE
      ELSE FALSE
  END
  ```
- **Description**: Flags transactions occurring during rush hours (6-8 AM or 3-6 PM)

#### 4. Entry/Exit Hour Extraction
- **Parameters**: `entry_hour`, `exit_hour`
- **Type**: Integer (0-23)
- **Aggregation Method**: EXTRACT function
- **Formula**:
  ```sql
  EXTRACT(HOUR FROM entry_time) as entry_hour
  EXTRACT(HOUR FROM exit_time) as exit_hour
  ```
- **Description**: Extracts hour component from entry and exit timestamps

#### 5. Travel Time of Day Category
- **Parameter**: `travel_time_of_day`
- **Type**: String
- **Aggregation Method**: CONCAT with CASE statements
- **Formula**: Combines entry and exit time-of-day categories
- **Description**: Creates journey category (e.g., "Morning Rush to Midday")

#### 6. Vehicle Type Classification
- **Parameter**: `vehicle_type_name`
- **Type**: String ('Passenger Vehicle' | 'Light Commercial' | 'Heavy Commercial' | 'Unknown')
- **Aggregation Method**: CASE statement
- **Formula**:
  ```sql
  CASE 
      WHEN vehicle_type_code IN ('1', '2', '2L', '2H') THEN 'Passenger Vehicle'
      WHEN vehicle_type_code IN ('3', '3L', '3H', 'B2', 'B3') THEN 'Light Commercial'
      WHEN vehicle_type_code IN ('4', '5', '6', '7', '8', '9', '4L', '4H', '5H', '6H', '7H') 
          THEN 'Heavy Commercial'
      ELSE 'Unknown'
  END
  ```
- **Description**: Categorizes vehicle type codes into readable classifications

---

## Model 2: `_silver__feateng_route.sql`

**Purpose**: Route analysis and velocity calculations - creates route features, distance, speed, and travel time aggregations

**Input**: `_silver__feateng`

### Aggregation Rules

#### 1. Previous Transaction Features
- **Parameters**: 
  - `entry_plaza_previous`
  - `exit_plaza_previous`
  - `entry_time_previous`
  - `exit_time_previous`
- **Type**: String (plazas), Timestamp (times)
- **Aggregation Method**: Window function (LAG)
- **Formula**:
  ```sql
  LAG(entry_plaza) OVER (
      PARTITION BY tag_plate_number 
      ORDER BY exit_time ASC NULLS LAST
  ) as entry_plaza_previous
  ```
- **Description**: Retrieves previous transaction's plaza and time information for each driver

#### 2. Route Name Construction
- **Parameter**: `route_name`
- **Type**: String
- **Aggregation Method**: CONCAT function
- **Formula**:
  ```sql
  CONCAT(
      COALESCE(exit_plaza_previous, 'Unknown'), 
      ' to ', 
      exit_plaza
  ) as route_name
  ```
- **Description**: Creates route string from previous exit plaza to current exit plaza

#### 3. Route In-State Classification
- **Parameter**: `route_instate`
- **Type**: String ('In-state' | 'Out-state' | 'Unknown')
- **Aggregation Method**: CASE statement with subquery
- **Formula**:
  ```sql
  CASE
      WHEN exit_plaza IS NULL OR exit_plaza = 'Unknown' 
           OR exit_plaza_previous IS NULL OR exit_plaza_previous = 'Unknown' 
      THEN 'Unknown'
      WHEN exit_plaza IN (SELECT plaza_name FROM instate_plazas)
           AND exit_plaza_previous IN (SELECT plaza_name FROM instate_plazas)
      THEN 'In-state'
      ELSE 'Out-state'
  END
  ```
- **Description**: Classifies route as in-state, out-state, or unknown based on plaza lookups

#### 4. Distance Calculation
- **Parameter**: `distance_miles`
- **Type**: Float
- **Aggregation Method**: LEFT JOIN with lookup table
- **Formula**: 
  ```sql
  LEFT JOIN distance_lookup dl
      ON exit_plaza_previous = dl.origin_plaza
      AND exit_plaza = dl.destination_plaza
  ```
- **Description**: Retrieves expected travel distance from `address_to_miles` lookup table

#### 5. Travel Time Calculation
- **Parameter**: `travel_time_minutes`
- **Type**: Integer
- **Aggregation Method**: TIMESTAMP_DIFF function
- **Formula**:
  ```sql
  TIMESTAMP_DIFF(
      exit_time, 
      exit_time_previous,
      MINUTE
  ) as travel_time_minutes
  ```
- **Description**: Calculates time difference in minutes between current and previous transaction

#### 6. Speed Calculation
- **Parameter**: `speed_mph`
- **Type**: Float
- **Aggregation Method**: CASE statement with calculation
- **Formula**:
  ```sql
  CASE 
      WHEN distance_miles IS NOT NULL 
           AND exit_time IS NOT NULL 
           AND exit_time_previous IS NOT NULL
           AND TIMESTAMP_DIFF(exit_time, exit_time_previous, MINUTE) > 0
      THEN (distance_miles / TIMESTAMP_DIFF(exit_time, exit_time_previous, MINUTE)) * 60
      ELSE NULL
  END
  ```
- **Description**: Calculates implied speed in miles per hour: `(distance / time) * 60`

#### 7. Minimum Required Travel Time
- **Parameter**: `min_required_travel_time_minutes`
- **Type**: Float
- **Aggregation Method**: CASE statement
- **Formula**:
  ```sql
  CASE 
      WHEN distance_miles IS NOT NULL AND distance_miles > 0
      THEN (distance_miles / 88.0) * 60
      ELSE NULL
  END
  ```
- **Description**: Calculates minimum travel time required at 88 mph (reasonable speed limit)

#### 8. Impossible Travel Flag
- **Parameter**: `is_impossible_travel`
- **Type**: Boolean
- **Aggregation Method**: CASE statement with multiple conditions
- **Formula**:
  ```sql
  CASE 
      WHEN TIMESTAMP_DIFF(exit_time, exit_time_previous, MINUTE) <= 0 THEN TRUE
      WHEN distance_miles IS NOT NULL 
           AND distance_miles > 0
           AND TIMESTAMP_DIFF(exit_time, exit_time_previous, MINUTE) < (distance_miles / 90.0) * 60
      THEN TRUE
      WHEN TIMESTAMP_DIFF(exit_time, exit_time_previous, MINUTE) > 0
           AND (distance_miles / TIMESTAMP_DIFF(exit_time, exit_time_previous, MINUTE)) * 60 >= 100
      THEN TRUE
      ELSE FALSE
  END
  ```
- **Description**: Flags transactions with:
  - Negative or zero time difference
  - Travel time less than physically possible at 90 mph
  - Implied speed exceeding 100 mph

#### 9. Rapid Succession Flag
- **Parameter**: `is_rapid_succession`
- **Type**: Boolean
- **Aggregation Method**: CASE statement
- **Formula**:
  ```sql
  CASE 
      WHEN exit_time IS NULL OR exit_time_previous IS NULL THEN NULL
      WHEN TIMESTAMP_DIFF(exit_time, exit_time_previous, MINUTE) < 5 THEN TRUE
      ELSE FALSE
  END
  ```
- **Description**: Flags transactions occurring less than 5 minutes apart

#### 10. Overlapping Journey Flag
- **Parameter**: `flag_overlapping_journey`
- **Type**: Boolean
- **Aggregation Method**: CASE statement
- **Formula**:
  ```sql
  CASE
      WHEN entry_time IS NOT NULL
          AND exit_time_previous IS NOT NULL
          AND entry_time < exit_time_previous
      THEN TRUE
      ELSE FALSE
  END
  ```
- **Description**: Flags when current transaction's entry time starts before previous transaction's exit time

#### 11. Overlapping Journey Duration
- **Parameter**: `overlapping_journey_duration_minutes`
- **Type**: Integer
- **Aggregation Method**: CASE statement with TIMESTAMP_DIFF
- **Formula**:
  ```sql
  CASE 
      WHEN entry_time < exit_time_previous
      THEN TIMESTAMP_DIFF(exit_time_previous, entry_time, MINUTE)
      ELSE 0
  END
  ```
- **Description**: Calculates duration of overlap in minutes

#### 12. Travel Time Category
- **Parameter**: `travel_time_category`
- **Type**: String
- **Aggregation Method**: CASE statement
- **Formula**:
  ```sql
  CASE 
      WHEN travel_time_minutes IS NULL THEN NULL
      WHEN travel_time_minutes < 0 THEN 'Invalid (Negative)'
      WHEN travel_time_minutes < 10 THEN 'Short (<10 min)'
      WHEN travel_time_minutes < 30 THEN 'Medium (10-30 min)'
      WHEN travel_time_minutes < 60 THEN 'Long (30-60 min)'
      ELSE 'Very Long (60+ min)'
  END
  ```
- **Description**: Categorizes travel time into buckets

---

## Model 3: `_silver__feateng_price.sql`

**Purpose**: Price feature engineering - creates driver-level rolling statistics and route-level price aggregations

**Input**: `_silver__feateng_route`

### Aggregation Rules

#### Driver-Level Rolling Statistics (Last 30 Transactions)

All driver-level aggregations use window functions with:
- **Partition**: `tag_plate_number`
- **Order**: `COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))`
- **Window Frame**: `ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING`

##### 1. Driver Amount Average
- **Parameter**: `driver_amount_last_30txn_avg`
- **Type**: Float
- **Aggregation Method**: Window function (AVG)
- **Formula**:
  ```sql
  AVG(amount) OVER (
      PARTITION BY tag_plate_number 
      ORDER BY COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))
      ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
  )
  ```
- **Description**: Rolling average of toll amounts over last 30 transactions per driver

##### 2. Driver Amount Standard Deviation
- **Parameter**: `driver_amount_last_30txn_std`
- **Type**: Float
- **Aggregation Method**: Window function (STDDEV)
- **Formula**:
  ```sql
  STDDEV(amount) OVER (
      PARTITION BY tag_plate_number 
      ORDER BY COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))
      ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
  )
  ```
- **Description**: Rolling standard deviation of toll amounts over last 30 transactions

##### 3. Driver Amount Minimum
- **Parameter**: `driver_amount_last_30txn_min`
- **Type**: Float
- **Aggregation Method**: Window function (MIN)
- **Formula**:
  ```sql
  MIN(amount) OVER (
      PARTITION BY tag_plate_number 
      ORDER BY COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))
      ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
  )
  ```
- **Description**: Rolling minimum toll amount over last 30 transactions

##### 4. Driver Amount Maximum
- **Parameter**: `driver_amount_last_30txn_max`
- **Type**: Float
- **Aggregation Method**: Window function (MAX)
- **Formula**:
  ```sql
  MAX(amount) OVER (
      PARTITION BY tag_plate_number 
      ORDER BY COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))
      ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
  )
  ```
- **Description**: Rolling maximum toll amount over last 30 transactions

##### 5. Driver Transaction Count
- **Parameter**: `driver_amount_last_30txn_count`
- **Type**: Integer
- **Aggregation Method**: Window function (COUNT)
- **Formula**:
  ```sql
  COUNT(*) OVER (
      PARTITION BY tag_plate_number 
      ORDER BY COALESCE(entry_time, TIMESTAMP('1900-01-01 00:00:00'))
      ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
  )
  ```
- **Description**: Count of transactions in the rolling window (useful for normalization)

#### Route-Level Statistics

All route-level aggregations use window functions with:
- **Partition**: `route_name, vehicle_type_code`
- **Window Frame**: Unbounded (all transactions for route)

##### 6. Route Amount Average
- **Parameter**: `route_amount_avg`
- **Type**: Float
- **Aggregation Method**: Window function (AVG)
- **Formula**:
  ```sql
  AVG(amount) OVER (
      PARTITION BY route_name, vehicle_type_code
  )
  ```
- **Description**: Average toll amount for the route and vehicle type combination

##### 7. Route Amount Standard Deviation
- **Parameter**: `route_amount_std`
- **Type**: Float
- **Aggregation Method**: Window function (STDDEV)
- **Formula**:
  ```sql
  STDDEV(amount) OVER (
      PARTITION BY route_name, vehicle_type_code
  )
  ```
- **Description**: Standard deviation of toll amounts for the route

##### 8. Route Amount Minimum
- **Parameter**: `route_amount_min`
- **Type**: Float
- **Aggregation Method**: Window function (MIN)
- **Formula**:
  ```sql
  MIN(amount) OVER (
      PARTITION BY route_name, vehicle_type_code
  )
  ```
- **Description**: Minimum toll amount for the route

##### 9. Route Amount Maximum
- **Parameter**: `route_amount_max`
- **Type**: Float
- **Aggregation Method**: Window function (MAX)
- **Formula**:
  ```sql
  MAX(amount) OVER (
      PARTITION BY route_name, vehicle_type_code
  )
  ```
- **Description**: Maximum toll amount for the route

##### 10. Route Amount Median
- **Parameter**: `route_amount_med`
- **Type**: Float
- **Aggregation Method**: Window function (PERCENTILE_CONT) with conditional logic
- **Formula**:
  ```sql
  CASE 
      WHEN route_transaction_count >= 30 THEN route_amount_med_raw
      ELSE NULL
  END
  ```
  Where `route_amount_med_raw` is:
  ```sql
  PERCENTILE_CONT(amount, 0.5) OVER (
      PARTITION BY route_name, vehicle_type_code
  )
  ```
- **Description**: Median toll amount for the route (only calculated if route has 30+ transactions)

##### 11. Route Transaction Count
- **Parameter**: `route_transaction_count`
- **Type**: Integer
- **Aggregation Method**: Window function (COUNT)
- **Formula**:
  ```sql
  COUNT(*) OVER (
      PARTITION BY route_name, vehicle_type_code
  )
  ```
- **Description**: Total number of transactions for the route and vehicle type combination

---

## Model 4: `_silver__flag.sql`

**Purpose**: Flag creation - creates boolean flags for data quality and business rule validation

**Input**: `_silver__feateng_price`

### Aggregation Rules

#### 1. Weekend Flag
- **Parameter**: `flag_is_weekend`
- **Type**: Boolean
- **Aggregation Method**: CASE statement
- **Formula**:
  ```sql
  CASE weekend_or_weekday
      WHEN 'Weekend' THEN TRUE
      ELSE FALSE
  END
  ```
- **Description**: Boolean flag indicating if transaction occurred on weekend

#### 2. Out-of-State Flag
- **Parameter**: `flag_outstate`
- **Type**: Boolean
- **Aggregation Method**: CASE statement
- **Formula**:
  ```sql
  CASE state_name
      WHEN 'NJ' THEN FALSE
      ELSE TRUE
  END
  ```
- **Description**: Boolean flag indicating if transaction occurred outside New Jersey

#### 3. Holiday Flag
- **Parameter**: `flag_is_holiday`
- **Type**: Boolean
- **Aggregation Method**: EXISTS subquery
- **Formula**:
  ```sql
  CASE 
      WHEN EXISTS (
          SELECT 1
          FROM holidays
          WHERE holiday_date = transaction_date
      ) THEN TRUE
      ELSE FALSE
  END
  ```
- **Description**: Boolean flag indicating if transaction occurred on a NJ Courts holiday (from `holidays` lookup table)

#### 4. Vehicle Type Flag
- **Parameter**: `flag_vehicle_type`
- **Type**: Boolean
- **Aggregation Method**: CASE statement
- **Formula**:
  ```sql
  CASE vehicle_type_name
      WHEN 'Light Commercial' THEN TRUE
      WHEN 'Heavy Commercial' THEN TRUE
      ELSE FALSE
  END
  ```
- **Description**: Boolean flag indicating if vehicle is commercial (light or heavy)

---

## Final Model: `silver.sql`

**Purpose**: Final aggregation - combines all intermediate models into the final silver table

**Input**: `_silver__flag`

### Output Parameters

The final `silver` table includes all parameters created by the aggregation rules above, organized into the following categories:

1. **Core Identifiers**:  
   `transaction_id`  
   `transaction_date`  
   `posting_date`  
   `tag_plate_number`

2. **Location Info**:  
   `agency`  
   `agency_name`  
   `state_name`  
   plaza information  
   `route_name`  
   `route_instate`

3. **Timestamps**:  
   `entry_time`  
   `exit_time`  
   previous transaction times  
   `entry_hour`  
   `exit_hour`  
   `travel_time_of_day`  
   `flag_rush_hour`

4. **Velocity & Travel Features**:  
   `distance_miles`  
   `travel_time_minutes`  
   `speed_mph`  
   `min_required_travel_time_minutes`  
   `is_impossible_travel`  
   `is_rapid_succession`  
   `flag_overlapping_journey`  
   `overlapping_journey_duration_minutes`  
   `travel_time_category`

5. **Vehicle & Fare**:  
   `vehicle_type_code`  
   `vehicle_type_name`  
   `plan_rate`  
   `fare_type`

6. **Financial**:  
   `amount`

7. **Price Features**:  
   - Driver rolling stats:  
     `driver_amount_last_30txn_avg`  
     `driver_amount_last_30txn_std`  
     `driver_amount_last_30txn_min`  
     `driver_amount_last_30txn_max`  
     `driver_amount_last_30txn_count`  
     `driver_daily_txn_count`  
   - Route stats:  
     `route_amount_avg`  
     `route_amount_std`  
     `route_amount_min`  
     `route_amount_max`  
     `route_amount_med`  
     `route_transaction_count`

8. **Flags**:  
   `flag_vehicle_type`  
   `flag_is_weekend`  
   `flag_is_holiday`  
   `flag_outstate`

---

## Summary Table

| Model | Aggregation Type | Parameters Created | Window Function Used |
|-------|-----------------|-------------------|---------------------|
| `_silver__feateng.sql` | Driver daily count, Time features | 6 parameters | Yes (driver daily count) |
| `_silver__feateng_route.sql` | Route features, Velocity, Travel time | 12 parameters | Yes (LAG for previous) |
| `_silver__feateng_price.sql` | Driver rolling stats, Route stats | 11 parameters | Yes (rolling 30, route-level) |
| `_silver__flag.sql` | Boolean flags | 4 parameters | No |
| **Total** | | **33+ parameters** | |

---

## Key Aggregation Patterns

1. **Rolling Window Aggregations**: Driver-level statistics use rolling windows of 30 transactions
2. **Route-Level Aggregations**: Route statistics partition by `route_name` and `vehicle_type_code`
3. **Temporal Aggregations**: Previous transaction features use LAG window functions
4. **Lookup-Based Aggregations**: Distance and holiday flags use lookup tables
5. **Calculated Aggregations**: Speed, travel time, and impossible travel flags use mathematical formulas

---

## Notes

- All window functions order by `entry_time` or `exit_time` to ensure chronological ordering
- Route median is only calculated when route has 30+ transactions for statistical reliability
- Impossible travel detection uses multiple thresholds (90 mph, 100 mph) for robustness
- All aggregations handle NULL values appropriately to avoid calculation errors

