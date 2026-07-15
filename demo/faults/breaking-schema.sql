select
    customer_id,
    2026 - birth_year as age_years,
    region,
    last_purchase_days_ago,
    total_spend
from {{ ref('raw_customers') }}
