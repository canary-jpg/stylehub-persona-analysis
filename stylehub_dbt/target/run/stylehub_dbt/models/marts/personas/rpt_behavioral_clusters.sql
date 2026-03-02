
  
    
    

    create  table
      "stylehub"."main"."rpt_behavioral_clusters__dbt_tmp"
  
    as (
      

with rfm_data as (
    select * from "stylehub"."main"."rpt_customer_rfm_v2"
    where frequency_orders > 0 --only customers who've purchased
),

--normalize features for clustering (z-score normalization)
feature_stats as (
    select 
        avg(total_sessions) as avg_sessions,
        stddev(total_sessions) as std_sessions,
        avg(frequency_orders) as avg_frequency,
        stddev(frequency_orders) as std_frequency,
        avg(monetary_total) as avg_monetary,
        stddev(monetary_total) as std_monetary,
        avg(avg_order_value) as avg_aov,
        stddev(avg_order_value) as std_aov,
        avg(returned_orders) as avg_returns,
        stddev(returned_orders) as std_returns
    from rfm_data 
),

normalized_features as (
    select 
        r.customer_id,
        r.persona_hidden,

        --original features
        r.total_sessions,
        r.frequency_orders,
        r.monetary_total,
        r.avg_order_value,
        r.returned_orders,
        r.is_browser_only,
        r.high_returner,
        r.discount_seeker,

        --normalized features (for z-scores)
        (r.total_sessions - s.avg_sessions) / nullif(s.std_sessions, 0) as sessions_z,
        (r.frequency_orders - s.avg_frequency) / nullif(s.std_frequency, 0) as frequency_z,
        (r.monetary_total - s.avg_monetary) / nullif(s.std_monetary, 0) as monetary_z,
        (r.avg_order_value - s.avg_aov) / nullif(s.std_aov, 0) as aov_z,
        (r.returned_orders - s.avg_returns) / nullif(s.std_returns, 0) as returns_z
    from rfm_data r 
    cross join feature_stats s 
),

--simple k-means implementation using business rules
--true k-means would require iterative alogrithm, let's use thresholds here
cluster_assignment as (
    select
        *,
        --cluster based on behavioral patterns
        case 
            --cluster 1: high frequency, high spend, and low returns
            when frequency_z > 0.5 and monetary_z > 0.5 and returns_z < 0.5 then 1
            --cluster 2: high frequency, moderate spend, and high returns
            when frequency_z > 0.5 and returns_z > 0.5 then 2
            --cluster 3: low frequency, high AOV, and low returns (big ticket buyer)
            when frequency_z < 0 and aov_z > 0.5 and returns_z < 0.5 then 3
            --cluster 4: high sessions, low conversion (browsers)
            when sessions_z > 0.5 and frequency_z < 0 then 4
            --cluster 5: discount seekers
            when discount_seeker = true then 5
            --cluster 6: everyone else (casual buyers)
            else 6
        end as cluster_id,

        --assign interpretable cluster names
        case 
            when frequency_z > 0.5 and monetary_z > 0.5 and returns_z < 0.5 then 'VIP Loyalists'
            when frequency_z > 0.5 and returns_z > 0.5 then 'Serial Returns'
            when frequency_z < 0 and aov_z > 0.5 and returns_z < 0.5 then 'Big Ticket Buyers'
            when sessions_z > 0.5 and frequency_z < 0 then 'Window Browsers'
            when discount_seeker = true then 'Deal Hunters'
            else 'Casual Shoppers'
        end as cluster_name
    from normalized_features
),

--calculate cluster statistics
final as (
    select 
        customer_id,
        persona_hidden,
        
        --cluster assignments
        cluster_id,
        cluster_name,

        --original metrics
        total_sessions,
        frequency_orders,
        monetary_total,
        avg_order_value,
        returned_orders,

        --behavioral flags
        is_browser_only,
        high_returner,
        discount_seeker,

        --normalized scores (for analysis)
        round(sessions_z, 2) as session_score,
        round(frequency_z, 2) as frequency_score,
        round(monetary_z, 2) as monetary_score,
        round(aov_z, 2) as aov_score,
        round(returns_z, 2) as returns_score
    from cluster_assignment 
)

select * from final
    );
  
  