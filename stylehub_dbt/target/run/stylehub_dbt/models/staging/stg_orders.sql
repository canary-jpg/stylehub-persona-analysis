
  
  create view "stylehub"."main"."stg_orders__dbt_tmp" as (
    select 
    order_id,
    customer_id,
    session_id,
    order_date::date as ordered_at,

    --metrics
    num_items,
    subtotal,
    discount,
    total,

    --flags
    returned,

    --derived metrics
    date_trunc('day', order_date::timestamp)::date as order_date_only,
    date_trunc('week', order_date::timestamp)::date as order_week,
    date_trunc('month', order_date::timestamp)::date as order_month,

    --discount analysis
    case
        when discount > 0 then true
        else false
    end as used_discount,

    case
        when subtotal > 0 then discount / subtotal * 100
        else 0
    end as discount_pct
from orders
  );
