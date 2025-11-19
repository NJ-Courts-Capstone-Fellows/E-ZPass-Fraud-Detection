{{ config(
    materialized='ephemeral',
    tags=['gold', 'training']
) }}

WITH source AS (
    SELECT * FROM {{ ref('gold') }}
),

-- Calculate frequency encoding for route_name
route_frequencies AS (
    SELECT
        route_name,
        COUNT(*) as route_frequency
    FROM source
    GROUP BY route_name
),

-- Calculate frequency encoding for entry_plaza
entry_plaza_frequencies AS (
    SELECT
        entry_plaza,
        COUNT(*) as entry_plaza_frequency
    FROM source
    GROUP BY entry_plaza
),

-- Calculate frequency encoding for exit_plaza
exit_plaza_frequencies AS (
    SELECT
        exit_plaza,
        COUNT(*) as exit_plaza_frequency
    FROM source
    GROUP BY exit_plaza
),

-- Calculate frequency encoding for vehicle_type_code
vehicle_frequencies AS (
    SELECT
        vehicle_type_code,
        COUNT(*) as vehicle_type_frequency
    FROM source
    GROUP BY vehicle_type_code
),

-- Calculate frequency encoding for agency
agency_frequencies AS (
    SELECT
        agency,
        COUNT(*) as agency_frequency
    FROM source
    GROUP BY agency
),

encoded AS (
    SELECT
        s.*,
        
        -- Route encodings
        COALESCE(rf.route_frequency, 0) as route_name_freq_encoded,
        
        -- Entry plaza encoding
        COALESCE(epf.entry_plaza_frequency, 0) as entry_plaza_freq_encoded,
        
        -- Exit plaza encoding
        COALESCE(expf.exit_plaza_frequency, 0) as exit_plaza_freq_encoded,
        
        -- Vehicle type encoding
        COALESCE(vf.vehicle_type_frequency, 0) as vehicle_type_freq_encoded,
        
        -- Agency encoding
        COALESCE(af.agency_frequency, 0) as agency_freq_encoded
        
    FROM source s
    LEFT JOIN route_frequencies rf
        ON s.route_name = rf.route_name
    LEFT JOIN entry_plaza_frequencies epf
        ON s.entry_plaza = epf.entry_plaza
    LEFT JOIN exit_plaza_frequencies expf
        ON s.exit_plaza = expf.exit_plaza
    LEFT JOIN vehicle_frequencies vf
        ON s.vehicle_type_code = vf.vehicle_type_code
    LEFT JOIN agency_frequencies af
        ON s.agency = af.agency
)

SELECT * FROM encoded

