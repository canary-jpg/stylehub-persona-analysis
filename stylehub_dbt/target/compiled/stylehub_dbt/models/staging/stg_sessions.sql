select 
    session_id,
    customer_id,
    session_start::timestamp as session_started_at,

    --metrics
    num_products_viewed,
    num_cart_adds,
    --flags
    purchased,
    --dervied metrics
    date_trunc('day', session_start::timestamp)::date as session_date,
    date_trunc('week', session_start::timestamp)::date as session_week,
    date_trunc('month', session_start::timestamp)::date as session_month,
from sessions