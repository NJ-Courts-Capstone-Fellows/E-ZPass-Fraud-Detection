{{ config(
    materialized='table',
    tags=['gold'],
    alias='gold_automation'
) }}

WITH metrics AS (
    SELECT * FROM {{ ref('_gold__metrics') }}
)

SELECT 
    *

FROM metrics