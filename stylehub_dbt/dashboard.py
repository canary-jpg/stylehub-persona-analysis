"""
StyleHub Analytics Dashboard
Interactive dashboard for customer personas, LTV forecasting, and product recommendations

Run: streamlit run dashboard.py
"""

import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime

# Page config
st.set_page_config(
    page_title="StyleHub Analytics Dashboard",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #e0e0e0;
    }
    .stMetric label {
        color: #0e1117 !important;
        font-weight: 600 !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #0e1117 !important;
        font-size: 24px !important;
    }
    h1 {
        color: #1f77b4;
    }
    </style>
    """, unsafe_allow_html=True)

# Database connection
@st.cache_resource
def get_db_connection():
    return duckdb.connect('stylehub.db', read_only=True)

# Load data functions
@st.cache_data(ttl=600)
def load_cluster_stats():
    conn = get_db_connection()
    query = """
        SELECT 
            cluster_name,
            COUNT(*) as customers,
            ROUND(AVG(monetary_total), 2) as avg_ltv,
            ROUND(AVG(total_sessions), 1) as avg_sessions,
            ROUND(AVG(frequency_orders), 1) as avg_orders,
            ROUND(AVG(monetary_total / NULLIF(frequency_orders, 0)), 2) as avg_order_value
        FROM main.rpt_behavioral_clusters
        GROUP BY cluster_name
        ORDER BY avg_ltv DESC
    """
    return conn.execute(query).fetchdf()

def load_ltv_forecast():
    """Load LTV forecast data - no caching for debugging"""
    try:
        conn = get_db_connection()
        query = """
            SELECT 
                cluster_name,
                COUNT(*) as customers,
                ROUND(SUM(actual_ltv_to_date), 2) as total_current_ltv,
                ROUND(SUM(predicted_12m_ltv), 2) as total_predicted_ltv,
                ROUND(SUM(predicted_future_revenue), 2) as total_future_revenue,
                ROUND(AVG(actual_ltv_to_date), 2) as avg_current_ltv,
                ROUND(AVG(predicted_12m_ltv), 2) as avg_predicted_ltv,
                ROUND(AVG(predicted_future_revenue), 2) as avg_future_revenue,
                ROUND(AVG(churn_probability) * 100, 1) as avg_churn_pct
            FROM main.rpt_ltv_forecast_v2
            WHERE cluster_name IS NOT NULL
            GROUP BY cluster_name
            ORDER BY avg_predicted_ltv DESC
        """
        df = conn.execute(query).fetchdf()
        
        # Debug output
        if len(df) == 0:
            st.warning(f"⚠️ Query returned 0 rows")
        else:
            st.success(f"✅ Loaded {len(df)} personas")
            
        return df
    except Exception as e:
        st.error(f"❌ Error loading LTV data: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None

@st.cache_data(ttl=600)
def load_at_risk_customers():
    conn = get_db_connection()
    query = """
        SELECT 
            customer_id,
            cluster_name,
            ROUND(actual_ltv_to_date, 2) as actual_ltv,
            ROUND(predicted_12m_ltv, 2) as predicted_ltv,
            days_since_last_order,
            ROUND(churn_probability * 100, 1) as churn_pct,
            risk_status
        FROM main.rpt_ltv_forecast_v2
        WHERE risk_status IN ('High Value At Risk', 'At Risk')
        ORDER BY predicted_ltv DESC
        LIMIT 100
    """
    return conn.execute(query).fetchdf()

@st.cache_data(ttl=600)
def load_product_affinity(persona):
    conn = get_db_connection()
    query = """
        SELECT 
            category_a,
            category_b,
            times_bought_together,
            ROUND(confidence_pct, 1) as confidence_pct,
            ROUND(lift, 2) as lift,
            recommendation_strength
        FROM main.rpt_product_affinity_v2
        WHERE cluster_name = ?
            AND recommendation_strength IN ('Very Strong', 'Strong')
        ORDER BY times_bought_together DESC
        LIMIT 10
    """
    return conn.execute(query, [persona]).fetchdf()

@st.cache_data(ttl=600)
def load_portfolio_metrics():
    conn = get_db_connection()
    query = """
        SELECT 
            COUNT(*) as total_customers,
            ROUND(SUM(actual_ltv_to_date), 2) as current_value,
            ROUND(SUM(predicted_12m_ltv), 2) as predicted_value,
            ROUND(SUM(predicted_future_revenue), 2) as future_opportunity,
            COUNT(CASE WHEN risk_status IN ('High Value At Risk', 'At Risk') THEN 1 END) as at_risk_count,
            ROUND(SUM(CASE WHEN risk_status IN ('High Value At Risk', 'At Risk') THEN predicted_12m_ltv ELSE 0 END), 2) as at_risk_value
        FROM main.rpt_ltv_forecast_v2
    """
    return conn.execute(query).fetchone()

# API prediction function
def predict_persona(sessions, purchases, first_order_value=None):
    """Call the FastAPI prediction endpoint"""
    import json
    
    try:
        url = "http://localhost:8000/predict"
        payload = {
            "sessions_first_7d": int(sessions),
            "purchases_first_7d": int(purchases),
            "avg_products_viewed": 0,
            "first_order_value": float(first_order_value) if first_order_value and first_order_value > 0 else None,
            "days_to_first_purchase": None,
            "used_discount": False
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            url, 
            data=json.dumps(payload),  # Use data + json.dumps instead of json parameter
            headers=headers, 
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API returned status code {response.status_code}")
            with st.expander("See error details"):
                st.json(response.json() if response.text else {"error": "No response"})
            return None
            
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API at http://localhost:8000")
        st.info("Make sure the API is running: `python persona_api_enhanced.py`")
        return None
    except requests.exceptions.Timeout:
        st.error("❌ API request timed out")
        return None
    except Exception as e:
        st.error(f"❌ Error calling API: {str(e)}")
        import traceback
        with st.expander("See full error"):
            st.code(traceback.format_exc())
        return None

# ============================================================================
# SIDEBAR
# ============================================================================

st.sidebar.title("🛍️ StyleHub Analytics")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["📊 Overview", "👥 Personas", "💰 LTV Forecast", "🛒 Product Affinity", "🚨 At Risk", "🔮 Predict"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Stats")

# Load portfolio metrics
metrics = load_portfolio_metrics()
st.sidebar.metric("Total Customers", f"{metrics[0]:,}")
st.sidebar.metric("Portfolio Value", f"${metrics[2]/1_000_000:.2f}M")
st.sidebar.metric("At Risk Value", f"${metrics[5]/1_000_000:.2f}M", delta=f"-{metrics[4]} customers", delta_color="inverse")

# ============================================================================
# MAIN CONTENT
# ============================================================================

if page == "📊 Overview":
    st.title("📊 StyleHub Analytics Dashboard")
    st.markdown("### Customer Intelligence & Persona Analytics")
    
    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Portfolio Value", 
            f"${metrics[2]/1_000_000:.2f}M",
            delta=f"+${metrics[3]/1_000_000:.2f}M forecast"
        )
    
    with col2:
        st.metric(
            "Total Customers",
            f"{metrics[0]:,}",
            delta=f"{metrics[4]} at risk",
            delta_color="inverse"
        )
    
    with col3:
        growth_pct = (metrics[3] / metrics[1]) * 100
        st.metric(
            "Growth Potential",
            f"{growth_pct:.1f}%",
            delta=f"${metrics[3]/1_000_000:.2f}M"
        )
    
    with col4:
        st.metric(
            "Value at Risk",
            f"${metrics[5]/1_000_000:.2f}M",
            delta=f"{metrics[4]} customers",
            delta_color="inverse"
        )
    
    st.markdown("---")
    
    # Load cluster data
    cluster_df = load_cluster_stats()
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👥 Customer Distribution by Persona")
        fig = px.pie(
            cluster_df, 
            values='customers', 
            names='cluster_name',
            title='',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 💰 Average LTV by Persona")
        fig = px.bar(
            cluster_df.sort_values('avg_ltv', ascending=True),
            y='cluster_name',
            x='avg_ltv',
            orientation='h',
            title='',
            color='avg_ltv',
            color_continuous_scale='Blues'
        )
        fig.update_layout(showlegend=False, xaxis_title="Average LTV ($)", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed table
    st.markdown("### 📋 Persona Summary")
    
    # Format the dataframe
    display_df = cluster_df.copy()
    display_df['avg_ltv'] = display_df['avg_ltv'].apply(lambda x: f"${x:,.2f}")
    display_df['avg_order_value'] = display_df['avg_order_value'].apply(lambda x: f"${x:,.2f}")
    display_df.columns = ['Persona', 'Customers', 'Avg LTV', 'Avg Sessions', 'Avg Orders', 'Avg Order Value']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ============================================================================
elif page == "👥 Personas":
    st.title("👥 Customer Personas")
    st.markdown("### Behavioral Clustering Analysis")
    
    cluster_df = load_cluster_stats()
    
    # Persona selector
    selected_persona = st.selectbox(
        "Select Persona",
        cluster_df['cluster_name'].tolist()
    )
    
    # Get persona details
    persona_data = cluster_df[cluster_df['cluster_name'] == selected_persona].iloc[0]
    
    # Display persona card
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Customers", f"{int(persona_data['customers']):,}")
    with col2:
        st.metric("Avg LTV", f"${persona_data['avg_ltv']:,.2f}")
    with col3:
        st.metric("Avg Sessions", f"{persona_data['avg_sessions']:.1f}")
    with col4:
        st.metric("Avg Orders", f"{persona_data['avg_orders']:.1f}")
    with col5:
        st.metric("Avg AOV", f"${persona_data['avg_order_value']:,.2f}")
    
    st.markdown("---")
    
    # Persona characteristics
    personas_info = {
        "VIP Loyalists": {
            "description": "Frequent buyers with high lifetime value",
            "traits": ["Fast conversion", "High frequency", "Low returns"],
            "strategy": "Retain at all costs with VIP perks and early access",
            "accuracy": "92%"
        },
        "Serial Returns": {
            "description": "High spenders but return frequently",
            "traits": ["High spend", "High returns (2.8x)", "Same revenue as VIPs"],
            "strategy": "Implement return fees, improve product descriptions",
            "accuracy": "Cannot predict early"
        },
        "Big Ticket Buyers": {
            "description": "Infrequent but high-value purchases",
            "traits": ["High AOV ($379)", "Seasonal buyers", "Gift shoppers"],
            "strategy": "Holiday campaigns, gift guides, bundling",
            "accuracy": "79%"
        },
        "Window Browsers": {
            "description": "Browse heavily but rarely purchase",
            "traits": ["70+ sessions", "Low conversion", "Research shoppers"],
            "strategy": "Cart abandonment, browse retargeting, minimal investment",
            "accuracy": "95%"
        },
        "Deal Hunters": {
            "description": "Price-sensitive, waits for sales",
            "traits": ["Discount seekers", "Flash sale buyers", "Price sensitive"],
            "strategy": "Flash sales, loyalty rewards, clearance alerts",
            "accuracy": "65%"
        },
        "Casual Shoppers": {
            "description": "Standard customers, steady but unexciting",
            "traits": ["Average engagement", "Mixed behavior", "Baseline segment"],
            "strategy": "Standard nurture, occasional promotions",
            "accuracy": "Default category"
        }
    }
    
    if selected_persona in personas_info:
        info = personas_info[selected_persona]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Description:** {info['description']}")
            st.markdown(f"**Detection Accuracy:** {info['accuracy']}")
            st.markdown("**Key Traits:**")
            for trait in info['traits']:
                st.markdown(f"- {trait}")
        
        with col2:
            st.markdown("**Marketing Strategy:**")
            st.info(info['strategy'])
    
    # Comparison chart
    st.markdown("### 📊 Persona Comparison")
    
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=('LTV Distribution', 'Session Activity', 'Purchase Frequency')
    )
    
    fig.add_trace(
        go.Bar(x=cluster_df['cluster_name'], y=cluster_df['avg_ltv'], name='Avg LTV'),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(x=cluster_df['cluster_name'], y=cluster_df['avg_sessions'], name='Avg Sessions'),
        row=1, col=2
    )
    
    fig.add_trace(
        go.Bar(x=cluster_df['cluster_name'], y=cluster_df['avg_orders'], name='Avg Orders'),
        row=1, col=3
    )
    
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
elif page == "💰 LTV Forecast":
    st.title("💰 Lifetime Value Forecasting")
    st.markdown("### 12-Month Revenue Predictions")
    
    # Test if we even get here
    st.write("🔍 DEBUG: Page loaded")
    
    try:
        with st.spinner("Loading LTV forecast data..."):
            ltv_df = load_ltv_forecast()
        
        st.write(f"🔍 DEBUG: Data loaded, type: {type(ltv_df)}, is None: {ltv_df is None}")
        
        if ltv_df is not None:
            st.write(f"🔍 DEBUG: DataFrame length: {len(ltv_df)}")
            st.write(f"🔍 DEBUG: Columns: {ltv_df.columns.tolist()}")
    
    except Exception as e:
        st.error(f"❌ Exception occurred: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        ltv_df = None
    
    # Debug: show what we loaded
    if ltv_df is None:
        st.error("❌ Failed to load LTV forecast data")
        st.info("Trying to query database directly...")
        
        try:
            conn = get_db_connection()
            test_query = "SELECT COUNT(*) as count FROM rpt_ltv_forecast_v2"
            count = conn.execute(test_query).fetchone()[0]
            st.write(f"Records in database: {count}")
            
            if count > 0:
                st.warning("Data exists but failed to load. Check the query.")
                # Try simpler query
                simple_df = conn.execute("SELECT * FROM rpt_ltv_forecast_v2 LIMIT 5").fetchdf()
                st.dataframe(simple_df)
        except Exception as e2:
            st.error(f"Database query failed: {str(e2)}")
        
    elif len(ltv_df) == 0:
        st.error("❌ Failed to load LTV forecast data")
        st.info("Trying to query database directly...")
        
        conn = get_db_connection()
        test_query = "SELECT COUNT(*) as count FROM rpt_ltv_forecast_v2"
        count = conn.execute(test_query).fetchone()[0]
        st.write(f"Records in database: {count}")
        
        if count > 0:
            st.warning("Data exists but failed to load. Check the query.")
            # Try simpler query
            simple_df = conn.execute("SELECT * FROM rpt_ltv_forecast_v2 LIMIT 5").fetchdf()
            st.dataframe(simple_df)
        
    elif len(ltv_df) == 0:
        st.error("❌ LTV forecast data is empty")
        
    else:
        # Data loaded successfully
        st.success(f"✅ Loaded {len(ltv_df)} personas")
        
        # Summary metrics - using totals
        total_current = ltv_df['total_current_ltv'].sum()
        total_predicted = ltv_df['total_predicted_ltv'].sum()
        total_future = ltv_df['total_future_revenue'].sum()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Current Portfolio Value", f"${total_current:,.0f}")
        with col2:
            st.metric("Predicted 12M Value", f"${total_predicted:,.0f}", delta=f"+${total_future:,.0f}")
        with col3:
            growth = (total_future / total_current) * 100 if total_current > 0 else 0
            st.metric("Growth Potential", f"{growth:.1f}%")
        
        st.markdown("---")
        
        # LTV Forecast Chart - using averages for comparison
        st.markdown("### 📈 Average LTV Forecast by Persona")
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Current Avg LTV',
            x=ltv_df['cluster_name'],
            y=ltv_df['avg_current_ltv'],
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            name='Predicted Avg LTV',
            x=ltv_df['cluster_name'],
            y=ltv_df['avg_predicted_ltv'],
            marker_color='darkblue'
        ))
        
        fig.update_layout(
            barmode='group',
            xaxis_title="Persona",
            yaxis_title="Average LTV ($)",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Churn risk
        st.markdown("### ⚠️ Churn Risk by Persona")
        
        fig = px.bar(
            ltv_df.sort_values('avg_churn_pct', ascending=False),
            x='cluster_name',
            y='avg_churn_pct',
            title='',
            color='avg_churn_pct',
            color_continuous_scale='Reds'
        )
        fig.update_layout(
            xaxis_title="Persona",
            yaxis_title="Average Churn Probability (%)",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed table
        st.markdown("### 📋 Forecast Details")
        display_df = ltv_df[['cluster_name', 'customers', 'avg_current_ltv', 'avg_predicted_ltv', 'avg_future_revenue', 'avg_churn_pct']].copy()
        display_df['avg_current_ltv'] = display_df['avg_current_ltv'].apply(lambda x: f"${x:,.2f}")
        display_df['avg_predicted_ltv'] = display_df['avg_predicted_ltv'].apply(lambda x: f"${x:,.2f}")
        display_df['avg_future_revenue'] = display_df['avg_future_revenue'].apply(lambda x: f"${x:,.2f}")
        display_df['avg_churn_pct'] = display_df['avg_churn_pct'].apply(lambda x: f"{x:.1f}%")
        display_df.columns = ['Persona', 'Customers', 'Avg Current LTV', 'Avg Predicted LTV', 'Avg Future Revenue', 'Churn Risk']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# ============================================================================
elif page == "🛒 Product Affinity":
    st.title("🛒 Product Affinity Analysis")
    st.markdown("### Market Basket Insights")
    
    cluster_df = load_cluster_stats()
    
    # Persona selector
    selected_persona = st.selectbox(
        "Select Persona",
        cluster_df['cluster_name'].tolist(),
        key="affinity_persona"
    )
    
    # Load affinity data
    affinity_df = load_product_affinity(selected_persona)
    
    if len(affinity_df) > 0:
        # Top recommendation
        top_rec = affinity_df.iloc[0]
        
        st.markdown("### 🔥 Top Recommendation")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Product Pair", f"{top_rec['category_a']} + {top_rec['category_b']}")
        with col2:
            st.metric("Times Bought Together", f"{int(top_rec['times_bought_together']):,}")
        with col3:
            st.metric("Confidence", f"{top_rec['confidence_pct']:.1f}%")
        with col4:
            st.metric("Lift", f"{top_rec['lift']:.2f}x")
        
        st.markdown("---")
        
        # Affinity matrix
        st.markdown("### 📊 Product Affinity Heatmap")
        
        # Create matrix
        categories = list(set(affinity_df['category_a'].tolist() + affinity_df['category_b'].tolist()))
        matrix = pd.DataFrame(0, index=categories, columns=categories)
        
        for _, row in affinity_df.iterrows():
            matrix.loc[row['category_a'], row['category_b']] = row['confidence_pct']
            matrix.loc[row['category_b'], row['category_a']] = row['confidence_pct']
        
        fig = px.imshow(
            matrix,
            labels=dict(x="Category", y="Category", color="Confidence %"),
            color_continuous_scale='Blues',
            title=''
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed table
        st.markdown("### 📋 Affinity Details")
        display_df = affinity_df.copy()
        display_df['confidence_pct'] = display_df['confidence_pct'].apply(lambda x: f"{x:.1f}%")
        display_df['lift'] = display_df['lift'].apply(lambda x: f"{x:.2f}x")
        display_df.columns = ['Category A', 'Category B', 'Times Together', 'Confidence', 'Lift', 'Strength']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
    else:
        st.warning(f"No product affinity data available for {selected_persona}")

# ============================================================================
elif page == "🚨 At Risk":
    st.title("🚨 At-Risk Customers")
    st.markdown("### Win-Back Campaign Targets")
    
    at_risk_df = load_at_risk_customers()
    
    if len(at_risk_df) > 0:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_value = at_risk_df['predicted_ltv'].sum()
        avg_churn = at_risk_df['churn_pct'].mean()
        recovery_20 = total_value * 0.20
        recovery_30 = total_value * 0.30
        
        with col1:
            st.metric("At-Risk Customers", f"{len(at_risk_df):,}")
        with col2:
            st.metric("Total Value at Risk", f"${total_value:,.2f}")
        with col3:
            st.metric("20% Recovery", f"${recovery_20:,.2f}")
        with col4:
            st.metric("30% Recovery", f"${recovery_30:,.2f}")
        
        st.markdown("---")
        
        # Risk distribution
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Risk Distribution by Persona")
            risk_by_persona = at_risk_df.groupby('cluster_name').agg({
                'customer_id': 'count',
                'predicted_ltv': 'sum'
            }).reset_index()
            risk_by_persona.columns = ['cluster_name', 'customers', 'total_value']
            
            fig = px.pie(
                risk_by_persona,
                values='customers',
                names='cluster_name',
                title='',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### 💰 Value at Risk by Persona")
            fig = px.bar(
                risk_by_persona.sort_values('total_value', ascending=False),
                x='cluster_name',
                y='total_value',
                title='',
                color='total_value',
                color_continuous_scale='Reds'
            )
            fig.update_layout(showlegend=False, xaxis_title="Persona", yaxis_title="Total Value ($)")
            st.plotly_chart(fig, use_container_width=True)
        
        # Campaign tiers
        st.markdown("### 🎯 Recommended Campaign Tiers")
        
        tier1 = at_risk_df[at_risk_df['predicted_ltv'] >= 3000]
        tier2 = at_risk_df[(at_risk_df['predicted_ltv'] >= 2000) & (at_risk_df['predicted_ltv'] < 3000)]
        tier3 = at_risk_df[at_risk_df['predicted_ltv'] < 2000]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Tier 1: Critical (LTV ≥ $3K)**")
            st.metric("Customers", f"{len(tier1):,}")
            st.metric("Value", f"${tier1['predicted_ltv'].sum():,.2f}")
            st.info("CEO email + phone call + 30% discount")
        
        with col2:
            st.markdown("**Tier 2: High (LTV $2K-3K)**")
            st.metric("Customers", f"{len(tier2):,}")
            st.metric("Value", f"${tier2['predicted_ltv'].sum():,.2f}")
            st.info("Personalized email series + 25% discount")
        
        with col3:
            st.markdown("**Tier 3: Standard (LTV < $2K)**")
            st.metric("Customers", f"{len(tier3):,}")
            st.metric("Value", f"${tier3['predicted_ltv'].sum():,.2f}")
            st.info("Automated email + 15% discount")
        
        # Customer list
        st.markdown("### 📋 Top 50 At-Risk Customers")
        
        display_df = at_risk_df.head(50).copy()
        display_df['actual_ltv'] = display_df['actual_ltv'].apply(lambda x: f"${x:,.2f}")
        display_df['predicted_ltv'] = display_df['predicted_ltv'].apply(lambda x: f"${x:,.2f}")
        display_df['churn_pct'] = display_df['churn_pct'].apply(lambda x: f"{x:.1f}%")
        display_df.columns = ['Customer ID', 'Persona', 'Actual LTV', 'Predicted LTV', 'Days Inactive', 'Churn Risk', 'Risk Status']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
    else:
        st.success("No customers at risk! 🎉")

# ============================================================================
elif page == "🔮 Predict":
    st.title("🔮 Persona Prediction")
    st.markdown("### Predict Customer Persona in Real-Time")
    
    st.markdown("""
    Enter customer behavior from their **first 7 days** to predict their persona.
    The model achieves **79-95% accuracy** depending on the persona.
    """)
    
    # Input form
    with st.form("prediction_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            sessions = st.number_input(
                "Sessions (First 7 Days)",
                min_value=0,
                max_value=100,
                value=5,
                help="Number of browsing sessions in first week"
            )
        
        with col2:
            purchases = st.number_input(
                "Purchases (First 7 Days)",
                min_value=0,
                max_value=20,
                value=0,
                help="Number of purchases in first week"
            )
        
        with col3:
            first_order = st.number_input(
                "First Order Value ($)",
                min_value=0.0,
                max_value=1000.0,
                value=0.0,
                step=10.0,
                help="Value of first order (if any)"
            )
        
        submitted = st.form_submit_button("🔮 Predict Persona", use_container_width=True)
    
    if submitted:
        # Call API
        with st.spinner("Predicting persona..."):
            result = predict_persona(
                sessions=sessions,
                purchases=purchases,
                first_order_value=first_order if first_order > 0 else None
            )
        
        if result:
            st.success("✅ Prediction Complete!")
            
            # Display result
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown(f"### {result['predicted_persona']}")
                st.metric("Confidence", f"{result['confidence']*100:.1f}%")
                st.metric("Forecasted LTV", f"${result.get('ltv_forecast', 0):.2f}")
            
            with col2:
                chars = result['persona_characteristics']
                st.markdown("**Persona Characteristics:**")
                st.markdown(f"- Typical LTV: ${chars['typical_ltv']:,.2f}")
                st.markdown(f"- Typical Sessions: {chars['typical_sessions']}")
                st.markdown(f"- Typical Orders: {chars['typical_orders']}")
                if 'monthly_velocity' in chars:
                    st.markdown(f"- Monthly Velocity: ${chars['monthly_velocity']}/month")
            
            st.markdown("---")
            st.markdown("### 📋 Recommended Actions")
            for i, action in enumerate(result['recommended_actions'], 1):
                st.markdown(f"{i}. {action}")
        
        else:
            st.error("⚠️ Unable to connect to prediction API. Make sure it's running at http://localhost:8000")
            st.code("python persona_api.py")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    StyleHub Analytics Dashboard | Built with Streamlit, FastAPI, dbt, DuckDB
</div>
""", unsafe_allow_html=True)