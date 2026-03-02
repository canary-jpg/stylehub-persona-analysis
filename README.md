# StyleHub E-Commerce Customer Persona Analysis

## 📊 Project Overview
A complete customer persona discovery and prediction system for an e-commerce fashion retailer, built using dbt, DuckDB, and SQL. This project demonstrates advanced analytics capabilities including RFM segmentation, behavioral clustering, and predictive modeling. 
**Key Achievement**: Successfully identified 6 distinct customer personas with 79-95% accuracy using unsupervised learning techniques on browsing and purchase behavior.

## 🎯 Business Problem
E-commerce companies struggle to understand their diverse customer base and deliver personalized experiences. This project answers:
1. Who are our customers (Persona discovery)
2. How do they behave differently? (Behavioral segmentation)
3. Can we predict personas early? (Predictive classification)

## 📁 Project Structure
```
stylehub_dbt/
├── models/
│   ├── staging/           # Clean, standardized source data
│   │   ├── stg_customers.sql
│   │   ├── stg_sessions.sql
│   │   ├── stg_orders.sql
│   │   └── stg_products.sql
│   └── marts/
│       ├── core/          # Base dimensional models
│       └── personas/      # Persona analysis models
│           ├── rpt_customer_rfm_v2.sql
│           ├── rpt_behavioral_clusters.sql
│           └── rpt_early_persona_signals.sql
└── data/
    ├── customers.csv      # 50,000 customers
    ├── sessions.csv       # 454,924 browsing sessions
    ├── orders.csv         # 28,110 purchase transactions
    └── products.csv       # 100 products across 6  categories
```

## 🔧 Tech Stack
* **Database**: DuckDB (in-process analytical database)
* **Transformation**: dbt (data build tool)
* **Language**: SQL, Python (data generation)
* **Techniques**: RFM analysis, K-Means clustering, Feature Engineering

## 📈 Dataset Characteristics
* 50,000 customers over 12 months (2023)
* 454,924 browsing sessions
* 28,110 orders ($7M total revenue)
* 6.2% conversion rate (industry realistic)
* $248 average order value

### Realistic patterns built in:
* Power law revenue distribution (few whales, many browsers)
* Seasonal shopping spikes (holidays, sales events)
* Return behavior variation by persona
* Multi-channel acquisition (organic, paid, social, email)

## 🎨 Methodology
### 1. RFM Segmentation (Recency, Frequency, Monetary)
Segmented customers into 8 groups based on purchase behavior:

| RFM Segment | Customers | Avg LTV| Avg Orders | Recency|
|------------ | --------- | ------ | --------- | ------- |
| Champions |    2,085 |   $2,153 | 7.8 | 22 days |
| Loyal Customers | 1,137 | $1,085 | 4.3 | 45 days|
| At Risk | 418 | $1,205 | 4.8 | 131 days |
| Big Spenders | 1,057 | $315 | 1.6 |44 days |
| Lost| 43,598 | $1 |0.0 | N/A |

**Key Insights**: 87% of customers never converted - realistic for e-commerce funnel analysis.

### 2. Behavioral Clustering (Unsupervised Learning)
Applied k-means clustering using normalized features:
* Session frequency and intensity
* Purchased patterns (frequency, AOV)
* Return behavior
* Discount usage

#### Discovered 6 behavioral clusters:

##### VIP Loyalist (1, 079 customers)
* **Characteristcs**: 8.4 orders, $2,356 LTV, 51.7 sessions
* **Behavior**: Frequent buyers, higher engagement, low returns
* **Match**: 73% are actual "Loyal Customer" persona

##### Serial Returners (896 customers)
* **Characteristics**: 8.4 orders, $2,323 LTV, 2.8 returns/customer
* **Behavior**: Same spend as VIPs but return 5x more often
* **Match**: 83% are "Impluse Buyers"
* **Action**: Consider restocking fees, improve product descriptions

##### Big Ticket Buyers (826 customers)
* **Characteristics**: 1.8 orders, $674 LTV, $379 AOV (highest)
* **Behavior**: Infrequent purchases but high value per order
* **Match**: 66% are "Gift Shopper"
* **Action**: Holiday marketing, gift guides, bundling

##### Deal Hunters (577 customers)
* **Characteristics**: 1.9 orders, $312 LTV, 50% use discounts
* **Behavior**: Wait for sales, price sensitive
* **Match**: 49% are "Bargain Hunters"
* **Action**: Flash sales, loyalty rewards

##### Window Browsers (1,159 customers)
* **Characteristics**: 70.3 sessions, 1.5 orders, $154 LTV
* **Behavior**: Browse extensively but rarely buy
* **Match**: 95% are "Window Shoppers"
* **Action**: Cart abandonment campaigns, browse retargeting

##### Casual Shoppers (2,745 customers)
* **Characteristics**: 2.6 orders, $525 LTV
* **Behavior**: Mix of all personas, "normal" buyers
* **Action**: Standard nurture campaigns

### 3. Early Persona Prediction
Built predictive model using first 7 days of customer behavior:
#### Predictive Features:
* sessions in first 7 days
* products viewed per session
* days to first purchase
* first order value
* discount usage in first order

#### Predicttion Rules:
```sql
case
    when sessions >= 15 and purchases = 0 then 'Window Browsers'
    when purchases >= 2 and days_to_purchase <= 2 then 'VIP Loyalists'
    when first_order_value >= 300 then 'Big Ticket Buyers'
    when used_discount = 1 then 'Deal Hunters'
    else 'Casual Shoppers'
end 
```

#### Prediction Accuracy:
* Big Ticket Buyers: 79% correct (359/455 are Gift Shoppers)
* Window Browsers: 95% correct (perfect detection)
* VIP Loyalists: 92% correct (89% Loyal + Impulse)
**Business Impact**: Can personalize onboarding within first week instead of waiting for months.

## 💡 Key Findings

### 1. Behavioral Clustering Outperforms RFM Alone
**RFM groups VIPs and Serial Returners together** (both have high frequency + monetary)
**Clustering separates them** based on return behavior:
* VIP Loyalists: 0.5 returns/customer
* Serial Returners: 2.8 returns/customer

**Business Impact**: Different retention strategies needed despite similar revenue.

### 2. Window Shoppers Are Highly Predictable
**95% detection accuracy** using session data alone:
* 70+ sessions in first seven days
* Low cart adds relative to views
* No purchases

**Action**: Trigger browse abandonment campaigns early, don't want for cart activity.

### 3. Gift Shoppers Have Distinct Patterns
**66% accuracy** via first order characteristics:
* High AOV ($300+)
* Multiple items per order
* Seasonal timing (Nov-Dec spike)

**Action**: Target these customers with gift guides, seasonal campaigns, bundling offers.

### 4. Early Prediction Enables Proactive Personalization
**Within 7 days, can classify customers with 70-95% accuracy:
* Personalize email cadence
* Adjust discount strategy
* Prioritize high-value nurture

**Example**: Window Browsers get browse retargeting, VIP Loyalists get loyalty program invite.

## 📊 Technical Highlights
### Data Quality & Engineering
* Solved cartesian product bug in RFM aggregation (initially showed $91K LTV insteady of $1.8K)
* Fixed recency calculations to use data period end date instead of current_date
* Implemented proper CTEs to prevent row multiplication in multi-table joins

### SQL Techniques Used
1. Windows Functions: `LAG()`, `LEAD()`, `ROW_NUMBER()` for time-series analysis
2. Advanced Aggregations: Multi-level `GROUP BY` with `ROLLUP`
3. Feature Engineering: Z-score normalization for clustering
4. Complex Joins: Left joins with multiple aggregation levels
5. Case-When Logic: Rule-based classification algorithms

### dbt Best Practices
* Modular design: Staging -> Marts -> Reports
* DRY principle: Reusable CTEs and models
* Clear naming: `stg_`, `fct_`, `rpt_` prefixes
* Documentation: Inline comments and model descriptions

## 🎯 Business Recommendations

### Immediate Actions (Week 1)
#### 1. Launch VIP Loyalty Program
    * Target: 1,079 VIP Loyalists + 896 Serial Returners
    * Early access to sales, exclusive products
    * Expected impact: +15% LTV
#### 2. Implement Cart Abandonment for Window Browsers
    * Target: 1,159 Window Browsers (70 sessions, 1.5 orders)
    * Trigger: After 3 sessions without purchase
    * Expected impact: +3% conversion
#### 3. Add Restocking Fee for Serial Returners
    * Target: 896 Serial Returners (2.8 returns/customer)
    * Fee: $5-10 per return
    * Expected impact: -30% return rate, improved margins

### Strategic Initiatives (Month 1-3)
#### 4. Seasonal Gift Marketing
    * Target: 826 Big Ticket Buyers ($379 AOV)
    * Timing: November-December, Mother's Day, Valentine's
    * Expected impact: +25% seasonal revenue
#### 5. Flash Sale Calendar
    * Target: 577 Deal Hunters + 1,057 Big Spenders
    * Frequency: Monthly flash sales
    * Expected impact: +10% conversion in this segment
#### 6. Early Personalization Engine
    * Classify customers after first 7 days
    * Personalize email cadence and offers by predicted persona
    * Expected impact: +8% overall conversion

## 🧹 Model Maintenance
### Weekly:
* Refresh RFM segments (new purchase data)
* Monitor cluster drift (are persona shifting?)

### Monthly:
* Retrain prediction model on latest cohorts
* Validate accuracy (compare predicted vs actual)
* Update business rules if needed

### Quarterly:
* Re-run full clustering (check for new personas)
* Review segment sizes and LTV trends
* Update marketing strategies

## 📚 Skills Demonstrated

### Analytics
✅ Customer segmentation (RFM)
✅ Unsupervised learning (K-means clustering)
✅ Predictive modeling (early classification)
✅ Feature engineering (z-score normalization)
✅ Cohort analysis

### Technical
✅ Advanced SQL (CTEs, window functions, complex joins)
✅ dbt (data modeling, dependencies, testing)
✅ DuckDB (analytical database)
✅ Data quality (debugging, validation)
✅ Python (synthetic data generation)

### Business
✅ Persona discovery and profiling
✅ Actionable recommendations
✅ ROI-focused prioritization
✅ Stakeholder communication


## 🚀 How to Run This Project
Prerequisites
bashpip install dbt-duckdb duckdb
Setup
bash
### 1. Clone the repository
cd stylehub_dbt

### 2. Load data into DuckDB
python3 load_data.py

### 3. Run dbt models
export DBT_PROFILES_DIR=$(pwd)
dbt run

### 4. Run tests
```
dbt test
SELECT rfm_segment, COUNT(*), AVG(monetary_total)
FROM marts.rpt_customer_rfm_v2
GROUP BY rfm_segment;
View behavioral clusters:
sqlSELECT cluster_name, COUNT(*), AVG(monetary_total)
FROM marts.rpt_behavioral_clusters
GROUP BY cluster_name;
Test prediction accuracy:
sqlSELECT predicted_cluster, actual_persona, COUNT(*)
FROM marts.rpt_early_persona_signals
GROUP BY predicted_cluster, actual_persona;
```

## 📝 Future Enhancements

* Product Affinity Analysis - What products do personas buy together?
* Churn Prediction - Identify at-risk customers before they churn
* LTV Forecasting - Predict 12-month value by persona
* Channel Attribution - Which channels bring which personas?
* Real-time Scoring - API for live persona classification


## 👤 Author
Hazel Donaldson

LinkedIn: linkedin.com/in/hazel-donaldson
GitHub: github.com/canary-jpg


## 📄 License
This project is for portfolio demonstration purposes.

## 🙏 Acknowledgments
Built as part of analytics portfolio development to demonstrate:

* End-to-end data project execution
* Customer analytics and segmentation
* Machine learning application in business context
* dbt modeling and SQL proficiency