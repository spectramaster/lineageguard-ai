select
    customer_id,
    customer_age,
    region,
    last_purchase_days_ago <= 30 as active_last_30d,
    total_spend,
    case when total_spend >= 1000 then 1 else 0 end as high_value_customer
from {{ ref('stg_customers') }}
