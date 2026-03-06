{{
    config(
        materialized='table'
    )
}}

with orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

clusters as (
    select * from {{ ref('rpt_behavioral_clusters') }}
),

-- Assign primary category based on order value
order_categories as (
    select
        o.*,
        cl.cluster_name,
        cl.persona_hidden,
        
        -- Assign primary category based on order characteristics
        case
            when o.total >= 300 then 'outerwear'
            when o.total >= 150 then 'dresses'
            when o.total >= 80 then 'shoes'
            when o.total >= 40 then 'bottoms'
            else 'tops'
        end as primary_category,
        
        -- Assign secondary category for multi-item orders
        case
            when o.num_items >= 4 then 'accessories'
            when o.num_items >= 2 then 'tops'
            else null
        end as secondary_category
        
    from orders o
    left join clusters cl on o.customer_id = cl.customer_id
),

-- Generate items with assigned categories
items_with_categories as (
    select
        order_id,
        customer_id,
        ordered_at,
        total,
        num_items,
        returned,
        cluster_name,
        persona_hidden,
        unnest(generate_series(1, num_items)) as item_number,
        
        -- First item is primary category, rest are secondary or random
        case
            when unnest(generate_series(1, num_items)) = 1 then primary_category
            when unnest(generate_series(1, num_items)) = 2 and secondary_category is not null then secondary_category
            else primary_category  -- Keep same category for consistency
        end as assigned_category
        
    from order_categories
),

-- Match with actual products from that category
order_items as (
    select
        ic.order_id,
        ic.customer_id,
        ic.ordered_at,
        ic.item_number,
        
        -- Pick a random product from the assigned category
        (
            select p.product_id
            from products p
            where p.category = ic.assigned_category
            order by random()
            limit 1
        ) as product_id,
        
        ic.cluster_name,
        ic.persona_hidden,
        ic.total as order_total,
        ic.num_items as items_in_order,
        ic.returned as order_returned
        
    from items_with_categories ic
),

-- Enrich with product details
final as (
    select
        oi.order_id,
        oi.customer_id,
        oi.ordered_at,
        oi.product_id,
        
        -- Product details
        p.product_name,
        p.category,
        p.brand,
        p.base_price,
        
        -- Order context
        oi.order_total,
        oi.items_in_order,
        oi.order_returned,
        
        -- Customer context
        oi.cluster_name,
        oi.persona_hidden
        
    from order_items oi
    left join products p on oi.product_id = p.product_id
)

select * from final