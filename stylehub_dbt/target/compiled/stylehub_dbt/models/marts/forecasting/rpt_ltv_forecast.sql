

with customers as (
    select * from "stylehub"."main"."stg_customers"
),

clusters as (
    select * from "stylehub"."main"."rpt_behavioral_clusters"
),

orders as (
    select * from "stylehub"."main"."stg_orders"
),

--calculate historical spending patterns by cohort month and persona
cohort_spend_patterns as (
    select 
        date_trunc('month', c.signed_up_at) as cohort_month,
        cl.cluster_name,

        --months since signup
        datediff('month', c.signed_up_at, o.ordered_at) as months_since_signup,

        --spending metrics
        avg(o.total) as avg_order_value,
        count(*) as orders,
        sum(o.total) as total_revenue
    from customers c 
    inner join clusters cl on c.customer_id = cl.customer_id 
    inner join orders o on c.customer_id = o.customer_id 
    where datediff('month', c.signed_up_at, o.ordered_at) <= 12 
    group by
        date_trunc('month', c.signed_up_at),
        cl.cluster_name,
        datediff('month', c.signed_up_at, o.ordered_at)
),

--calculates average revenue curve by cluster
cluster_revenue_curve as (
    select 
        cluster_name,
        months_since_signup,
        avg(avg_order_value) as typical_order_value,
        avg(orders) as typical_order_count,
        avg(total_revenue) as typical_monthly_revenue
    from cohort_spend_patterns 
    group by cluster_name, months_since_signup 
),

--get current customer status
customer_current_state as (
    select 
        c.customer_id,
        c.signed_up_at,
        cl.cluster_name,
        cl.monetary_total as actual_ltv_to_date,
        cl.frequency_orders as orders_to_date,

        --time metrics
        datediff('month', c.signed_up_at, date '2023-12-31') as months_active,
        12 - datediff('month', c.signed_up_at, date '2023-12-31') as months_remaining,

        --last order
        max(o.ordered_at) as last_order_date,
        datediff('day', max(o.ordered_at), date '2023-12-31') as days_since_last_order
    
    from customers c 
    left join clusters cl on c.customer_id = cl.customer_id 
    left join orders o on c.customer_id = o.customer_id 
    group by 
        c.customer_id, c.signed_up_at, cl.cluster_name,
        cl.monetary_total, cl.frequency_orders 
),

--forecast future revenue
ltv_forecast as (
    select 
        cs.customer_id,
        cs.signed_up_at,
        cs.cluster_name,
        cs.actual_ltv_to_date,
        cs.orders_to_date,
        cs.months_active,
        cs.months_remaining,
        cs.days_since_last_order,

        --churn probability
        case
            when cs.days_since_last_order <= 30 then 0.10
            when cs.days_since_last_order <= 60 then 0.25
            when cs.days_since_last_order <= 90 then 0.50
            when cs.days_since_last_order <= 180 then 0.75
            else 0.90
        end as churn_probability,

        --predicted future revenue (sum remaining months)
        sum(
            crc.typical_monthly_revenue * 
            (1 - case
                when cs.days_since_last_order <= 30 then 0.10
                when cs.days_since_last_order <= 60 then 0.25
                when cs.days_since_last_order <= 90 then 0.50
                when cs.days_since_last_order <= 180 then 0.75
                else 0.90
            end)
        ) over (
            partition by cs.customer_id 
        ) as predicted_future_revenue,

        --MoM forecast
        max(case when crc.months_since_signup = cs.months_active + 1 then crc.typical_monthly_revenue else 0 end) as forecast_month_1,
        max(case when crc.months_since_signup = cs.months_active + 2 then crc.typical_monthly_revenue else 0 end) as forecast_month_2, 
        max(case when crc.months_since_signup = cs.months_active + 3 then crc.typical_monthly_revenue else 0 end) as forecast_month_3

    from customer_current_state cs 
    left join cluster_revenue_curve crc 
        on cs.cluster_name = crc.cluster_name 
        and crc.months_since_signup > cs.months_active 
        and crc.months_since_signup <= 12
    group by
        cs.customer_id, cs.signed_up_at, cs.cluster_name,
        cs.actual_ltv_to_date, cs.orders_to_date, cs.months_active,
        cs.months_remaining, cs.days_since_last_order, crc.typical_monthly_revenue
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
            when churn_probability >= 0.50 then 'At Risk'
            else 'Healthy'
        end as risk_status
    from ltv_forecast
)

select * from final
where cluster_name is not null