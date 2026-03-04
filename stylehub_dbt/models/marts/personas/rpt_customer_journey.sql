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

-- Combine all events into timeline
all_events as (

    -- Session events
    select
        s.customer_id,
        s.session_started_at as event_timestamp,
        'Session' as event_type,
        s.num_products_viewed as event_value,
        s.purchased as led_to_purchase
    from sessions s

    union all

    -- Purchase events
    select
        o.customer_id,
        o.ordered_at as event_timestamp,
        'Purchase' as event_type,
        o.total as event_value,
        true as led_to_purchase
    from orders o

    union all

    -- Return events
    select
        o.customer_id,
        o.ordered_at + interval '7 days' as event_timestamp,  -- Assume returns happen 7 days later
        'Return' as event_type,
        o.total as event_value,
        false as led_to_purchase
    from orders o
    where o.returned = true

),

-- Add customer context and calculate days since signup
events_with_context as (

    select
        e.customer_id,
        c.signed_up_at,
        e.event_timestamp,
        e.event_type,
        e.event_value,
        e.led_to_purchase,
        
        -- Days since signup
        datediff('day', c.signed_up_at, e.event_timestamp) as days_since_signup,
        
        -- Week since signup  
        floor(datediff('day', c.signed_up_at, e.event_timestamp) / 7) as week_since_signup,
        
        -- Event sequence number
        row_number() over (partition by e.customer_id order by e.event_timestamp) as event_sequence,
        
        -- Cluster info
        cl.cluster_name,
        cl.persona_hidden

    from all_events e
    inner join customers c on e.customer_id = c.customer_id
    left join clusters cl on e.customer_id = cl.customer_id

),

-- Create journey timeline string
journey_timeline as (

    select
        customer_id,
        cluster_name,
        persona_hidden,
        signed_up_at,
        
        -- Journey milestones
        min(case when event_type = 'Session' then event_timestamp end) as first_session,
        min(case when event_type = 'Purchase' then event_timestamp end) as first_purchase,
        min(case when event_type = 'Return' then event_timestamp end) as first_return,
        
        -- Days to milestones
        min(case when event_type = 'Session' then days_since_signup end) as days_to_first_session,
        min(case when event_type = 'Purchase' then days_since_signup end) as days_to_first_purchase,
        min(case when event_type = 'Return' then days_since_signup end) as days_to_first_return,
        
        -- Event counts by week
        count(case when week_since_signup = 0 then 1 end) as week_0_events,
        count(case when week_since_signup = 1 then 1 end) as week_1_events,
        count(case when week_since_signup = 2 then 1 end) as week_2_events,
        count(case when week_since_signup = 3 then 1 end) as week_3_events,
        count(case when week_since_signup = 4 then 1 end) as week_4_events,
        
        -- Purchase counts by week
        count(case when week_since_signup = 0 and event_type = 'Purchase' then 1 end) as week_0_purchases,
        count(case when week_since_signup = 1 and event_type = 'Purchase' then 1 end) as week_1_purchases,
        count(case when week_since_signup = 2 and event_type = 'Purchase' then 1 end) as week_2_purchases,
        count(case when week_since_signup = 3 and event_type = 'Purchase' then 1 end) as week_3_purchases,
        count(case when week_since_signup = 4 and event_type = 'Purchase' then 1 end) as week_4_purchases

    from events_with_context
    group by customer_id, cluster_name, persona_hidden, signed_up_at

),

-- Sample journey strings (first 30 days)
journey_strings as (

    select
        customer_id,
        cluster_name,
        string_agg(
            event_type || 
            case 
                when event_type = 'Purchase' then ' ($' || round(event_value, 0) || ')'
                when event_type = 'Session' then ' (' || round(event_value, 0) || ' views)'
                else ''
            end ||
            ' [Day ' || days_since_signup || ']',
            ' → '
            order by event_timestamp
        ) as journey_path

    from events_with_context
    where days_since_signup <= 30  -- First 30 days only
    group by customer_id, cluster_name

)

-- Combine everything
select
    jt.*,
    js.journey_path

from journey_timeline jt
left join journey_strings js on jt.customer_id = js.customer_id