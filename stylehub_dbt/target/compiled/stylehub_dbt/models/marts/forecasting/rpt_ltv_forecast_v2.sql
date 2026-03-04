

with customers as (
    select * from "stylehub"."main"."stg_customers"
),

clusters as (
    select * from "stylehub"."main"."rpt_behavioral_clusters"
),

orders as (
    select * from "stylehub"."main"."stg_orders"
),

--get current customer status
customer_current_state as (
    select 
        c.customer_id,
        c.signed_up_at,
        cl.cluster_name,
        cl.monetary_total as actual_ltv_to_date,
        cl.frequency_orders as orders_to_date,
        cl.total_sessions,

        --time metrics
        datediff('month', c.signed_up_at, date '2023-12-31') as months_active,

        --last order
        max(o.ordered_at) as last_order_date,
        datediff('day', max(o.ordered_at), date '2023-12-31') as days_since_last_order
    from customers c 
    left join clusters cl on c.customer_id = cl.customer_id 
    left join orders o on c.customer_id = o.customer_id 
    where cl.cluster_name is not null 
    group by 
        c.customer_id, c.signed_up_at, cl.cluster_name,
        cl.monetary_total, cl.frequency_orders, cl.total_sessions 
),

--calculate average spending velocity by cluster ($ per month active)
cluster_monthly_velocity as (
    select 
        cluster_name,
        avg(actual_ltv_to_date / nullif(months_active, 0)) as avg_monthly_spend
    from customer_current_state 
    where months_active > 0
    group by cluster_name 
),

--forecast based on monthly velocity
ltv_forecast as (
    select 
        cs.customer_id,
        cs.signed_up_at,
        cs.cluster_name,
        cs.actual_ltv_to_date,
        cs.orders_to_date,
        cs.total_sessions,
        cs.months_active,
        cs.days_since_last_order,

        --churn probability (higher if inactive)
        case 
            when cs.days_since_last_order is null then 1.0 -- never purchased
            when cs.days_since_last_order <= 30 then 0.10
            when cs.days_since_last_order <= 60 then 0.25
            when cs.days_since_last_order <= 90 then 0.50
            when cs.days_since_last_order <= 180 then 0.75
            else 0.90
        end as churn_probability,

        --simple forecast: monthly velocity * months remaining * (1 - churn_probability)
        cmv.avg_monthly_spend *
        greatest(0, 12 - cs.months_active) *
        (1 - case
            when cs.days_since_last_order is null then 1.0
            when cs.days_since_last_order <= 30 then 0.10
            when cs.days_since_last_order <= 60 then 0.25
            when cs.days_since_last_order <= 90 then 0.50
            when cs.days_since_last_order <= 180 then 0.75
            else 0.90
        end) as predicted_future_revenue,

        cmv.avg_monthly_spend
    from customer_current_state cs 
    left join cluster_monthly_velocity cmv on cs.cluster_name = cmv.cluster_name
),

final as (
    select 
        *,

        --total 12-month LTV forecast
        actual_ltv_to_date + coalesce(predicted_future_revenue, 0) as predicted_12m_ltv,

        --value tier
        case 
            when actual_ltv_to_date + coalesce(predicted_future_revenue, 0) >= 2000 then 'Platinum'
            when actual_ltv_to_date + coalesce(predicted_future_revenue, 0) >= 1000 then 'Gold'
            when actual_ltv_to_date + coalesce(predicted_future_revenue, 0) >= 500 then 'Silver'
            when actual_ltv_to_date + coalesce(predicted_future_revenue, 0) >= 100 then 'Bronze'
            else 'Basic'
        end as value_tier,

        --risk flag
        case 
            when churn_probability >= 0.50 and actual_ltv_to_date >= 1000 then 'High Value At Risk'
            when churn_probability >= 0.75 then 'Likely Churned'
            when churn_probability >+ 0.50 then 'At Risk'
            else 'Healthy'
        end as risk_status
    from ltv_forecast
)

select * from final