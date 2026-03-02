
  
    
    

    create  table
      "stylehub"."main"."rpt_customer_rfm__dbt_tmp"
  
    as (
      

with customers as (
    select * from "stylehub"."main"."stg_customers"
),

orders as (
    select * from "stylehub"."main"."stg_orders"
),

sessions as (
    select * from "stylehub"."main"."stg_sessions"
),

--calculate RFM metrics per customer
customer_metrics as (
    select 
        c.customer_id,
        c.signed_up_at,
        c.acquisition_channel,
        c.country,
        c.persona_hidden,

        --recency (days since last order)
        max(o.ordered_at) as last_order_date,
        datediff('day', max(o.ordered_at), date '2023-12-31') as recency_days,

        --frequency (number of orders)
        count(distinct o.order_id) as frequency_orders,

        --monetary (total spent)
        coalesce(sum(o.total), 0) as monetary_total,

        --additional metrics
        count(distinct s.session_id) as total_sessions,
        coalesce(sum(o.num_items), 0) as total_items_purchased,
        coalesce(avg(o.total), 0) as avg_order_value,
        sum(case when o.returned then 1 else 0 end) as returned_orders,
        sum(case when o.used_discount then 1 else 0 end) as orders_with_discount
    from customers c 
    left join sessions s on c.customer_id = s.customer_id
    left join orders o on c.customer_id = o.customer_id 
    group by 
        c.customer_id, c.signed_up_at, c.acquisition_channel,
        c.country, c.persona_hidden 
),

--calculate RFM scores (1-5 scale)
rfm_scored as (
    select 
        *,

        --recency score (lower days = better = higher score)
        case 
            when recency_days <= 30 then 5
            when recency_days <= 60 then 4
            when recency_days <= 90 then 3
            when recency_days <= 180 then 2
            when recency_days is null then 0 --never ordered
            else 1
        end as r_score,

        --frequency score
        case
            when frequency_orders >= 10 then 5
            when frequency_orders >= 5 then 4
            when frequency_orders >= 3 then 3
            when frequency_orders >= 2 then 2
            when frequency_orders >= 1 then 1
            else 0
        end as f_score,

        --monetary score
        case 
            when monetary_total >= 500 then 5
            when monetary_total  >= 250 then 4
            when monetary_total >= 100 then 3
            when monetary_total >= 50 then 2
            when monetary_total > 0 then 1 
            else 0
        end m_score 
    from customer_metrics 
),

--assigning RFM segments 
final as (
    select 
        *,
        --combine RFM score
        r_score + f_score + m_score as rfm_score,

        --RFM segment labels
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

        --behavioral flags
        case 
            when total_sessions > 0 and frequency_orders = 0 then true 
            else false
        end as is_browser_only,

        case
            when returned_orders::float / nullif(frequency_orders, 0) > 0.2 then true
            else false
        end as higher_returner,

        case
            when orders_with_discount::float / nullif(frequency_orders, 0) > 0.5 then true
            else false
        end as discount_seeker

    from rfm_scored
)

select * from final
    );
  
  