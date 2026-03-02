
  
    
    

    create  table
      "stylehub"."main"."rpt_customer_rfm_v2__dbt_tmp"
  
    as (
      

with customers as (

    select * from "stylehub"."main"."stg_customers"

),

-- Aggregate orders per customer separately to avoid cartesian product
customer_orders as (

    select
        customer_id,
        max(ordered_at) as last_order_date,
        count(*) as frequency_orders,
        sum(total) as monetary_total,
        sum(num_items) as total_items_purchased,
        avg(total) as avg_order_value,
        sum(case when returned then 1 else 0 end) as returned_orders,
        sum(case when used_discount then 1 else 0 end) as orders_with_discount

    from "stylehub"."main"."stg_orders"
    group by customer_id

),

-- Aggregate sessions per customer separately
customer_sessions as (

    select
        customer_id,
        count(*) as total_sessions

    from "stylehub"."main"."stg_sessions"
    group by customer_id

),

-- Combine everything
customer_metrics as (

    select
        c.customer_id,
        c.signed_up_at,
        c.acquisition_channel,
        c.country,
        c.persona_hidden,
        
        -- Order metrics
        co.last_order_date,
        datediff('day', co.last_order_date, date '2023-12-31') as recency_days,
        coalesce(co.frequency_orders, 0) as frequency_orders,
        coalesce(co.monetary_total, 0) as monetary_total,
        coalesce(co.total_items_purchased, 0) as total_items_purchased,
        coalesce(co.avg_order_value, 0) as avg_order_value,
        coalesce(co.returned_orders, 0) as returned_orders,
        coalesce(co.orders_with_discount, 0) as orders_with_discount,
        
        -- Session metrics
        coalesce(cs.total_sessions, 0) as total_sessions

    from customers c
    left join customer_orders co on c.customer_id = co.customer_id
    left join customer_sessions cs on c.customer_id = cs.customer_id

),

-- Calculate RFM scores
rfm_scored as (

    select
        *,
        
        -- Recency score (lower days = better = higher score)
        case
            when recency_days <= 30 then 5
            when recency_days <= 60 then 4
            when recency_days <= 90 then 3
            when recency_days <= 180 then 2
            when recency_days is null then 0
            else 1
        end as r_score,
        
        -- Frequency score
        case
            when frequency_orders >= 10 then 5
            when frequency_orders >= 5 then 4
            when frequency_orders >= 3 then 3
            when frequency_orders >= 2 then 2
            when frequency_orders >= 1 then 1
            else 0
        end as f_score,
        
        -- Monetary score
        case
            when monetary_total >= 500 then 5
            when monetary_total >= 250 then 4
            when monetary_total >= 100 then 3
            when monetary_total >= 50 then 2
            when monetary_total > 0 then 1
            else 0
        end as m_score

    from customer_metrics

),

-- Assign RFM segments
final as (

    select
        *,
        
        -- Combined RFM score
        r_score + f_score + m_score as rfm_score,
        
        -- RFM segment labels
        case
            when r_score >= 4 and f_score >= 4 and m_score >= 4 then 'Champions'
            when r_score >= 3 and f_score >= 3 and m_score >= 3 then 'Loyal Customers'
            when r_score >= 4 and f_score <= 2 and m_score <= 2 then 'New Customers'
            when r_score <= 2 and f_score >= 3 and m_score >= 3 then 'At Risk'
            when r_score <= 2 and f_score <= 2 and m_score <= 2 then 'Lost'
            when r_score >= 3 and f_score <= 2 and m_score >= 3 then 'Big Spenders'
            when r_score >= 3 and f_score >= 3 and m_score <= 2 then 'Frequent Shoppers'
            when r_score = 0 and f_score = 0 and m_score = 0 then 'Never Purchased'
            else 'Potential'
        end as rfm_segment,
        
        -- Behavioral flags
        case 
            when total_sessions > 0 and frequency_orders = 0 then true 
            else false 
        end as is_browser_only,
        
        case 
            when returned_orders::float / nullif(frequency_orders, 0) > 0.2 then true 
            else false 
        end as high_returner,
        
        case 
            when orders_with_discount::float / nullif(frequency_orders, 0) > 0.5 then true 
            else false 
        end as discount_seeker

    from rfm_scored

)

select * from final
    );
  
  