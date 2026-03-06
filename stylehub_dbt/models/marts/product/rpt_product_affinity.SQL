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

--Note: we need to parse the products JSON from orders
--for now, we'll create simply purchase patterns based on order characteristics

--simulate product purchases based on order value and customer segment
product_purchases as (
    select 
        o.customer_id,
        o.order_id,
        o.total,
        cl.cluster_name,
        cl.persona_hidden,

        --assign likely product categories based on order characteristics
        case 
            when o.total >= 300 then 'Outerwear'
            when o.total >= 150 then 'Dresses'
            when o.total >= 80 then 'Shoes'
            when o.total >= 40 then 'Bottoms'
            else 'Tops'
        end as primary_category,

        case 
            when o.num_items >= 4 then 'Accessories'
            when o.num_items >= 2 then 'Tops'
            else null 
        end as secondary_category
    from orders o 
    inner join clusters cl on o.customer_id = cl.customer_id 
),

--category preferences by persona
persona_category_preferences as (
    select 
        cluster_name,
        primary_category,
        count(*) as avg_order_value,
        count(distinct customer_id) as unique_customers
    from product_purchases
    group by cluster_name, primary_category
),

--category co-occurrence (market basket)
category_pairs as (
    select 
        p1.cluster_name,
        p1.primary_category as category_a,
        p1.secondary_category as category_b,
        count(distinct p1.order_id) as co_occurrence_count,
        count(distinct p1.customer_id) as customers 
    from product_purchases p1 
    inner join product_purchases p2 
        on p1.order_id = p2.order_id
        and p1.primary_category != p2.secondary_category
    where p2.secondary_category is not null 
    group by p1.cluster_name, p1.primary_category, p2.secondary_category
),

--calculate lift (how much more likely to buy together vs independent)
category_totals as (
    select 
        cluster_name,
        primary_category,
        count(*) as total_purchases
    from product_purchases
    group by cluster_name, primary_category
),

affinity_with_lift as (
    select
        cp.cluster_name,
        cp.category_a,
        cp.category_b,
        cp.co_occurrence_count,
        cp.customers,

        --support (% of orders with this pair)
        round(cp.co_occurrence_count::float / sum(cp.co_occurrence_count) over (partition by cp.cluster_name) * 100, 2) as support_pct,

        --confidence (if bought A, % also bought B)
        round(cp.co_occurrence_count::float / ct.total_purchases * 100, 2) as confidence_pct,

        --recommendation strength
        case 
            when cp.co_occurrence_count >= 50 then 'Strong'
            when cp.co_occurrence_count >= 20 then 'Moderate'
            else 'Weak'
        end as recommendation_strength
    from category_pairs cp 
    left join category_totals ct 
        on cp.cluster_name = ct.cluster_name
        and cp.category_a = ct.primary_category
),

final as (
    select 
        cluster_name,
        category_a,
        category_b,
        co_occurrence_count,
        customers,
        support_pct,
        confidence_pct,
        recommendation_strength,

        --recommendation text
        'Customers who bought ' || category_a || ' also bought ' || catgory_b ||
        ' (' || confidence_pct || '% of the time)' as recommendation_text
    from affinity_with_lift 
    where co_occurrence_count >= 10 --minimum threshold
)

select * from final 
order by cluster_name, co_occurrence_count desc