# StyleHub E-Commerce Analytics Platform

**Complete customer persona discovery, LTV forecasting, product recommendations, and real-time prediction API**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![dbt](https://img.shields.io/badge/dbt-1.7+-orange.svg)](https://www.getdbt.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

---

## 📊 Executive Summary

Built a complete analytics platform for e-commerce customer intelligence:
- **6 personas discovered** with 79-95% prediction accuracy
- **$9.17M portfolio value** tracked ($1.15M at risk identified)
- **Real-time API** with 8 endpoints for predictions & recommendations
- **Market basket analysis** with 99.98% confidence product pairs

**Business Impact:** Identified $1.15M at risk, designed win-back campaign with 785-1,227% ROI.

---

## 🚀 Quick Start

### **Using Docker (Recommended)**
```bash
# Coming soon!
docker-compose up
# API: http://localhost:8000
# Dashboard: http://localhost:8501
```

### **Local Setup**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Load data
cd stylehub_dbt
python load_data.py

# 3. Run dbt
export DBT_PROFILES_DIR=$(pwd)
dbt run

# 4. Start API
python persona_api_enhanced.py

# 5. Launch dashboard (coming soon)
streamlit run dashboard.py
```

**Interactive API Docs:** http://localhost:8000/docs

---

## 🎯 What It Does

### **1. Persona Discovery (95% Accuracy)**
Identifies 6 customer types using RFM + behavioral clustering:
- VIP Loyalists ($2,356 LTV, 92% accuracy)
- Serial Returners (high spend + high returns, 83% match)
- Big Ticket Buyers ($379 AOV, 79% accuracy)
- Window Browsers (95% accuracy - perfect detection)
- Deal Hunters (price-sensitive)
- Casual Shoppers (baseline)

### **2. Early Prediction (First 7 Days)**
Classifies new customers in their first week:
```python
# 15 sessions, no purchases → Window Browser (95% confidence)
POST /predict {"sessions_first_7d": 15, "purchases_first_7d": 0}
```

### **3. LTV Forecasting**
Predicts 12-month customer value:
- **Portfolio:** $9.17M total ($6.98M current + $2.19M forecast)
- **At Risk:** $1.15M from 555 customers
- **Growth:** +31% potential from existing base

### **4. Product Recommendations**
Cart-aware recommendations using affinity analysis:
```bash
# Customer has dresses in cart → recommend tops (99.98% bought together)
GET /recommend-products?persona=VIP%20Loyalists&current_cart=dresses
```

### **5. Win-Back Campaigns**
Identifies at-risk customers:
```bash
GET /at-risk?limit=100&min_ltv=1000
# Returns 555 customers worth $1.15M
# Campaign ROI: 785-1,227%
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predict` | POST | Predict persona from early signals |
| `/customer/{id}` | GET | Full customer profile + LTV forecast |
| `/recommend-products` | GET | Cart-aware product recommendations |
| `/recommendations/{persona}` | GET | Affinity analysis + marketing strategy |
| `/at-risk` | GET | High-value customers for win-back |
| `/batch` | POST | Batch persona predictions |
| `/stats` | GET | Portfolio analytics ($9.17M value) |
| `/personas` | GET | List all 6 personas |

**Full API documentation:** http://localhost:8000/docs

---

## 📈 Key Findings

### **Finding 1: Window Browsers = 95% Predictable**
- 70+ sessions, zero purchases in first week
- **Action:** Trigger abandonment emails immediately
- **Impact:** +3% conversion on 1,159 customers

### **Finding 2: Serial Returners Hidden in VIP Segment**
- Same revenue as VIPs ($2,323 vs $2,356)
- But 2.8 returns vs 0.5 returns
- **Action:** Different retention strategy needed
- **Impact:** -30% return rate with fees

### **Finding 3: Accessories + Outerwear = 10.72x Lift**
- Premium upsell for Big Ticket Buyers
- **Action:** Gift bundling campaigns
- **Impact:** +25% seasonal revenue

### **Finding 4: $1.15M Revenue at Risk**
- 555 high-value customers inactive 90+ days
- 75-90% churn probability
- **Action:** Win-back campaign (3-tier approach)
- **Impact:** $230K-$345K recovery

---

## 💻 Tech Stack

- **Database:** DuckDB (in-process OLAP)
- **Transformation:** dbt 1.7+
- **API:** FastAPI, Uvicorn
- **Dashboard:** Streamlit (coming soon)
- **Deployment:** Docker, Docker Compose (coming soon)
- **Language:** Python 3.8+, SQL

---

## 📊 Data Models

```
staging/
├── stg_customers     # 50K customers, 5 channels
├── stg_sessions      # 455K sessions, browsing behavior  
├── stg_orders        # 28K orders, $7M revenue
└── stg_products      # 100 products, 6 categories

marts/personas/
├── rpt_customer_rfm_v2          # RFM segmentation
├── rpt_behavioral_clusters      # K-means personas
├── rpt_ltv_forecast_v2          # 12-month predictions
├── rpt_customer_journey         # Touchpoint analysis
└── rpt_early_persona_signals    # First-week features

marts/product/
├── fct_order_items              # Line-item details
└── rpt_product_affinity_v2      # Market basket analysis
```

---

## 🎯 Use Cases

### **E-Commerce Team**
- Segment customers for personalized campaigns
- Identify at-risk VIPs before they churn
- Optimize product bundling strategies

### **Marketing Team**
- Target right persona with right message
- Design win-back campaigns (785% ROI)
- A/B test personalization strategies

### **Product Team**
- Understand shopping patterns
- Improve recommendation algorithms
- Reduce cart abandonment

### **Executive Team**
- Portfolio value tracking ($9.17M)
- Revenue at risk monitoring ($1.15M)
- Strategic persona insights

---

## 📚 Project Structure

```
stylehub_dbt/
├── models/
│   ├── staging/              # Source data cleaning
│   └── marts/
│       ├── personas/         # Customer analytics
│       └── product/          # Product analytics
├── persona_api_enhanced.py   # FastAPI application
├── dashboard.py              # Streamlit dashboard (soon)
├── Dockerfile                # Container config (soon)
├── docker-compose.yml        # Multi-service (soon)
├── requirements.txt          # Python dependencies
├── load_data.py              # Data loader
└── data/
    ├── customers.csv         # 50K records
    ├── sessions.csv          # 455K records  
    ├── orders.csv            # 28K records
    └── products.csv          # 100 records
```

---

## 🧪 Example API Calls

### **Predict Persona**
```bash
curl -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{
    "sessions_first_7d": 15,
    "purchases_first_7d": 0
  }'

# Response: Window Browser (95% confidence)
```

### **Get Customer Profile**
```bash
curl http://localhost:8000/customer/C003118

# Response: VIP at risk ($4,791 LTV, 122 days inactive)
```

### **Product Recommendations**
```bash
curl "http://localhost:8000/recommend-products?\
persona=VIP%20Loyalists&current_cart=dresses&limit=3"

# Response: Tops (99.98% confidence, 3 products)
```

### **Portfolio Stats**
```bash
curl http://localhost:8000/stats

# Response: $9.17M total, $1.15M at risk, 6 clusters
```

---

## 📊 Business Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Customers Analyzed** | 50,000 | 12 months of data |
| **Purchase Conversion** | 14.6% | 7,282 buyers |
| **Portfolio Value** | $9.17M | 12-month forecast |
| **Value at Risk** | $1.15M | 555 customers |
| **Prediction Accuracy** | 79-95% | By persona type |
| **Product Affinity Confidence** | 99.98% | Dresses + Tops |
| **Win-Back ROI** | 785-1,227% | Campaign projection |

---

## 🚀 Deployment

### **Docker (Coming Soon)**
```bash
# Build and run
docker-compose up --build

# Services:
# - API: http://localhost:8000
# - Dashboard: http://localhost:8501
# - Database: DuckDB (persistent volume)
```

### **Production Considerations**
- Add authentication (OAuth2, API keys)
- Set up monitoring (Prometheus, Grafana)
- Configure rate limiting
- Enable HTTPS
- Add caching (Redis)
- Set up CI/CD pipeline

---

## 📈 Roadmap

- [x] Customer persona discovery
- [x] LTV forecasting  
- [x] Product recommendations
- [x] Real-time prediction API
- [ ] **Streamlit dashboard** (in progress)
- [ ] **Docker deployment** (in progress)
- [ ] Channel attribution analysis
- [ ] Automated email campaigns
- [ ] Real-time scoring pipeline
- [ ] A/B testing framework

---

## 🤝 Contributing

This is a portfolio project. Feel free to fork and adapt for your own use cases!

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 👤 Contact

**[Your Name]**
- LinkedIn: [linkedin.com/in/hazel-donaldson]
- GitHub: [github.com/canary-jpg]
- Email: hazel90.hd@gmail.com

---

## ⭐ Acknowledgments

Built to demonstrate:
- End-to-end analytics platform development
- Customer segmentation & persona discovery
- ML application in e-commerce
- Production API development
- Data engineering best practices

**Star this repo** if you found it helpful! 🌟