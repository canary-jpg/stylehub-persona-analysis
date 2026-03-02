{{
    config(
        materialized='table'
    )
}}

with customers as (
    select * from {{ ref('stg_customers') }}
),

sessions as (
    select * from {{ ref('stg_sessions') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

clusters as (
    select * from {{ ref('rpt_behavioral_clusters') }}
),

--early sessions (1st 7 days only)
early_sessions as (
    select 
        s.customer_id,
        count(*) as sessions_first_7d,
        avg(s.num_cart_adds) as avg_cart_adds,
        avg(s.num_products_viewed) as avg_products_viewed,
        sum(case when s.purchased then 1 else 0 end) as purchases_first_7d,
        min(case when s.purchased
            then datediff('day', c.signed_up_at, s.session_started_at)
        end) as days_to_first_purchase
    from sessions s 
    inner join customers c on s.customer_id = c.customer_id 
    where datediff('day', c.signed_up_at, s.session_started_at) <= 7
    group by s.customer_id 
),

--first order characteristics
first_order as (
    select 
        customer_id,
        min(total) as first_order_value,
        min(num_items) as first_order_items,
        max(case when used_discount then 1 else 0 end) as used_discount_first
    from orders 
    group by customer_id 
),

final as (
    select 
        c.customer_id,
        c.acquisition_channel,

        --early signals
        coalesce(es.sessions_first_7d, 0) as sessions_first_7d,
        coalesce(es.avg_products_viewed, 0) as avg_products_viewed,
        coalesce(es.avg_cart_adds, 0) as avg_cart_adds,
        coalesce(es.purchases_first_7d, 0) as purchases_first_7d,
        es.days_to_first_purchase,
        fo.first_order_value,
        fo.first_order_items,
        fo.used_discount_first,

        --actual cluster (for validation)
        cl.cluster_name,
        cl.persona_hidden as actual_persona
    from customers c 
    left join early_sessions es on c.customer_id = es.customer_id
    left join first_order fo on c.customer_id = fo.customer_id
    left join clusters cl on c.customer_id = cl.customer_id
)

select * from final 