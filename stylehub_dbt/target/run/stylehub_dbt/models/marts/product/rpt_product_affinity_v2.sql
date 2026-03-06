
  
    
    

    create  table
      "stylehub"."main"."rpt_product_affinity_v2__dbt_tmp"
  
    as (
      

with order_items as (
    select * from "stylehub"."main"."fct_order_items"
),

--get all product pairs purchased together
product_pairs as (
    select 
        oi1.cluster_name,
        oi1.product_id as product_a,
        oi1.category as category_a,
        oi1.brand as brand_a,
        oi2.product_id as product_b,
        oi2.category as category_b,
        oi2.brand as brand_b,
        oi1.order_id 
    from order_items oi1 
    inner join order_items oi2 
        on oi1.order_id = oi2.order_id 
        and oi1.product_id < oi2.product_id --avoid duplicates and self-joins
    where oi1.cluster_name is not null 
),

--count co-occurrences
product_affinity as (
    select 
        cluster_name,
        product_a,
        category_a,
        brand_a,
        product_b,
        category_b,
        brand_b,
        count(*) as times_bought_together,
        count(distinct order_id) as orders_with_both 
    from product_pairs 
    group by 
        cluster_name,
        product_a, category_a, brand_a,
        product_b, category_b, brand_b
),

--calculate individual product purchase counts
product_totals as (
    select 
        cluster_name,
        product_id,
        count(distinct order_id) as total_orders
    from order_items 
    where cluster_name is not null 
    group by cluster_name, product_id 
),

--calculate confidence with lift
affinity_metrics as (
    select 
        pa.cluster_name,
        pa.product_a,
        pa.category_a,
        pa.brand_a,
        pa.product_b,
        pa.category_b,
        pa.brand_b,
        pa.times_bought_together,
        pa.orders_with_both,

        --support: % of orders containing both products
        round(pa.orders_with_both::float / 
            sum(pa.orders_with_both) over (partition by pa.cluster_name) * 100, 2) as support_pct,

        --confidence: if bought A, what % also bought B
        round(pa.orders_with_both::float / pt_a.total_orders * 100, 2) as confidence_pct,

        --lift: how much more liely to but together vs independent
        round(
            (pa.orders_with_both::float / pt_a.total_orders) /
            (pt_b.total_orders::float / sum(pt_b.total_orders) over (partition by pa.cluster_name)),
            2
        ) as lift 
    from product_affinity pa 
    left join product_totals pt_a 
        on pa.cluster_name = pt_a.cluster_name 
        and pa.product_a = pt_a.product_id 
    left join product_totals pt_b 
        on pa.cluster_name = pt_b.cluster_name 
        and pa.product_b = pt_b.product_id 
),

final as (
    select 
        cluster_name,
        product_a,
        category_a,
        brand_a,
        product_b,
        category_b,
        brand_b,
        times_bought_together,
        support_pct,
        confidence_pct,
        lift,

        --recommendation strength
        case 
            when times_bought_together >= 50 and lift >= 2.0 then 'Very Strong'
            when times_bought_together >= 30 and lift >= 1.5 then 'Strong'
            when times_bought_together >= 15 and lift >= 1.2 then 'Moderate'
            else 'Weak'
        end recommendation_strength,

        --recommendation text
        'Customers who bought ' || category_a || ' (' || brand_a || ') also bought ' ||
        category_b || ' (' || brand_b || ') ' || confidence_pct || '% of the time' as recommendation_text 
    from affinity_metrics 
    where times_bought_together >= 5 --minimum threshold
        and lift >= 1.0 --only show when there's actual affinity
)

select * from final 
order by cluster_name, times_bought_together desc
    );
  
  