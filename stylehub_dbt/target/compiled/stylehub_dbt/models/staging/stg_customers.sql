select 
    customer_id,
    signup_date::date as signed_up_at,
    lower(trim(acquisition_channel)) as acquisition_channel,
    lower(trim(country)) as country,
    email_subscriber, --flag
    --persona (hidden - we'll discover this through analysis)
    persona_actual as persona_hidden
from customers