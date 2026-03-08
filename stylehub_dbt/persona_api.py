"""
StyleHub Persona Prediction API 
Real-time customer persona classification with database integration

Features:
- Real-time persona prediction
- Customer lookup from database
- Batch predictions
- Product recommendations by persona
- LTV forecasting
- Campaign recommendations

Usage:
    pip install fastapi uvicorn duckdb pydantic
    python persona_api.py

API Docs: http://localhost:8000/doc
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import duckdb 
import uvicorn
from datetime import datetime 

app = FastAPI(
    title='StyleHub Persona API',
    description='Real-time customer persona prediction and recommendations',
    version='1.0.0'
)


#enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#database connection
DB_PATH="stylehub.db"

class CustomerData(BaseModel):
    """Input data for persona prediction """
    customer_id: Optional[str] = None
    sessions_first_7d: int = Field(..., ge=0, description="Number of sessions in the first seven days")
    avg_products_viewed: Optional[float] = Field(0, ge=0)
    purchases_first_7d: int = Field(0, ge=0)
    first_order_value: Optional[float] = Field(None, ge=0)
    days_to_first_purchase: Optional[int] = Field(None, ge=0)
    used_discount: Optional[bool] = False

class PersonaPrediction(BaseModel):
    """Prediction response """
    predicted_persona: str 
    confidence: float 
    persona_characteristics: Dict 
    recommended_actions: List[str]
    ltv_forecast: Optional[float] = None 

class CustomerProfile(BaseModel):
    """Full customer profile from database """
    customer_id: str 
    cluster_name: str 
    actual_ltv: float 
    predicted_12m_ltv: float 
    total_sessions: int 
    total_orders: int 
    risk_status: str 
    days_since_last_order: Optional[int]
    churn_probability: float 
    recommended_actions: List[str]

class BatchPredictionRequest(BaseModel):
    """Request for batch predictions """
    customers: List[CustomerData]

def get_db_connection():
    """Gete database connection """
    try:
        return duckdb.connect(DB_PATH, read_only=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


def predict_persona(data: CustomerData) -> PersonaPrediction:
    """
    Predict customer persona based on early signals

    Rules (from our analysis - 79-95% accuracy):
    - Window Browsers: 15+ sessions, 0 purchases (95% accuracy)
    - VIP Loyalists: 2+ purchases in first week, quick conversion (92% accuracy)
    - Big Ticket Buyers: First order >= $300 (79% accuracy)
    - Serial Returners: Can't predict early, need return data
    - Casual Shoppers: Default
    """

    #rule-based classification
    if data.sessions_first_7d >= 15 and data.purchases_first_7d == 0:
        return PersonaPrediction(
            predicted_persona='Window Browser',
            confidence=0.95,
            persona_characteristics={
                'typical_ltv': 154,
                'typical_sessions': 70,
                'typical_orders': 1.5, 
                'monthly_velocity': 17,
                'browse_heavy': True 
            },
            recommended_actions=[
                "Trigger card abandonment email after 3 sessions",
                "Offer first-purchase discount (15% off)",
                "Send browser retargeting ads",
                "Add to 'High Intent Browser' nurture campaign",
                "Show social proof (reviews, bestsellers)"
            ],
            ltv_forecast=173.0
        )
    elif data.purchases_first_7d >= 2 and data.days_to_first_purchase and data.days_to_first_purchase <= 2:
        return PersonaPrediction(
            predicted_persona="VIP Loyalist",
            confidence=0.92,
            persona_characteristics={
                "typical_ltv": 2356,
                "typical_sessions": 52,
                "typical_orders": 8.4,
                "monthly_velocity": 280,
                "high_value": True 
            },
            recommended_actions=[
                "⭐️ IMMEDIATE: Invite to VIP loyalty program",
                "Offer early access to new products",
                "Assign dedicated account manager",
                "Send personalized thank-you with exclusive perks",
                "Free shipping on all future orders",
                "Birthday/anniversary recognition"
            ],
            ltv_forecast=3111.0
        )
    
    elif data.first_order_value and data_first_order_value >= 300:
        return PersonaPrediction(
            predicted_persona='Big Ticket Buyer',
            confidence=0.79,
            persona_characteristics={
                "typical_ltv": 674,
                "typical_sessions": 20,
                "typical_orders": 1.8,
                "monthly_velocity": 95,
                "high_aov": True,
                "likely_gift_shopper": True 
            },
            recommended_actions=[
                "Send gift guide recommendations",
                "Offer bundling discounts for multiple items",
                "Target with holiday/seasonal campaigns (Nov-Dec, Feb, May)",
                "Add to 'Gift Shopper' segment to Q4 marketing",
                "Show gift wrapping options prominently"
            ],
            ltv_forecast=891.0
        )
    elif data.used_discount:
        return PersonaPrediction(
            predicted_person='Deal Hunter',
            confidence=0.65,
            persona_characteristics={
                "typical_ltv": 312,
                "typical_sessions": 34,
                "typical_orders": 1.9,
                "monthly_velocity": 56,
                "price_sensitive": True 
            },
            recommended_actions=[
                "Send flash sale notifications",
                "Offer loyalty rewards program",
                "Target with clearance/sale campaigns",
                "Limit full-price marketing",
                "Show 'Deal of the Day' prominently"
            ],
            ltv_forecast=557.0
        )
    else:
        return PersonaPrediction(
            predicted_persona='Casual Shopper',
            confidence=0.70,
            persona_characteristics={
                "typical_ltv": 525,
                "typical_sessions": 40,
                "typical_orders": 2.6,
                "monthly_velocity": 73,
                "standard_buyer": True 
            },
            recommended_actions=[
                "Standard nurture email campaign (Weekly)",
                "Send new arrival notifications",
                "Offer occasional promotions (20% off)",
                "Monitor for upgrade to VIP status",
                "Cross-sell complementary products"
            ],
            ltv_forecast=682.0
        )


@app.get("/")
async def root():
    """API health check """
    return {
        "status": "healthy",
        "service": "StyleHub Persona Prediction API",
        "version": "1.0.0",
        "endpoints": {
            "predict": "/predict - Predict persona from early signals",
            "customer": "/customer/{id} - Get full customer profile",
            "batch": "/batch - Batch predictions",
            "personas": "/personas - List all personas",
            "stats": "/stats - Database statistics",
            "recommendations": "/recommendations/{persona} - Get product recommendations"
        }
    }


@app.post("/predict", response_model=PersonaPrediction)
async def predict(data: CustomerData):
    """
    Predict customer persona based on early behavioral signals

    Example request:
    ```json
    {
        "sessions_first_7d": 15,
        "purchases_first_7d": 0,
        "first_order_value": null
    }
    ```
    """
    try:
        prediction = predict_persona(data)
        return prediction 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/customer/{customer_id}", response_model=CustomerProfile)
async def get_customer(customer_id: str):
    """
    Get full customer profile from database including:
    - Current persona
    - LTV (actual and predicted)
    - Risk status
    - Recommended actions
    """
    try:
        conn = get_db_connection()

        query = """ 
            SELECT
                ltv.customer_id,
                ltv.cluster_name,
                ltv.actual_ltv_to_date as actual_ltv,
                ltv.predicted_12m_ltv,
                ltv.total_sessions,
                ltv.orders_to_date as total_orders,
                ltv.risk_status,
                ltv.days_since_last_order,
                ltv.churn_probability
            FROM rpt_ltv_forecast_v2 ltv
            WHERE ltv.customer_id = ?
        """

        result = conn.execute(query, [customer_id]).fetchone()
        conn.close()

        if not result:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

        #generate recommendations based on risk status
        recommendations = []
        if result[6] == 'High Value At Risk':
            recommendations = [
                "🚨 URGENT: Launch win-back campaign immediately",
                "Personal outreach from CEO/founder",
                "Offer 30% discount + free shipping",
                "Phone call from account manager",
                "Investigate reason for inactivity"
            ]
        elif result[6] == "At Risk":
            recommendations = [
                "Send re-engagement email series (3 emails)",
                "Offer 25% discount",
                "Show new products since last visit",
                "Enable retargeting ads"
            ]
        elif result[6] == "Healthy":
            recommendations = [
                "Continue standard nurture campaign",
                "Recognize loyalty with thank-you",
                "Offer exclusive early access to sales",
                "Consider VIP program upgrade"
            ]
        return CustomerProfile(
            customer_id=result[0],
            cluster_name=result[1],
            actual_ltv=round(result[2], 2),
            predicted_12m_ltv=round(result[3], 2),
            total_sessions=result[4],
            total_orders=result[5],
            risk_status=result[6],
            days_since_last_order=result[7],
            churn_probability=result[8],
            recommended_actions=recommendations
        )
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/batch", response_model=List[PersonaPrediction])
async def batch_predict(request: BatchPredictionRequest):
    """
    Predict personas for multiple customers at once

    Example request:
    ```json
    {
        "customers": [
            {"sessions_first_7d": 15, "purchases_first_7d": 0},
            {"sessions_first_7d: 2, "purchase_first_7d": 2, "days_to_first_purchase": 1}
        ]
    }
    ``` 
    """
    try:
        predictions = [predict_persona(customer) for customer in request.customers]
        return predictions 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/persona")
async def get_personas():
    """Get list of all personas with characteristics and detection accuracy """
    return {
        "personas": [
        {
            "name": "VIP Loyalist",
            "description": "Frequent buyers with high lifetime value",
            "ltv": 2356,
            "monthly_velocity": 280,
            "sessions": 52,
            "orders": 8.4,
            "detection_accuracy": "92%",
            "key_traits": ["Fast conversion", "High Frequency", "Low Returns"],
            "marketing_strategy": "Retain at all costs, VIP perks, early access"
        
    },
    {
        "name": "Serial Returner",
        "description": "High spenders but return frequently",
        "ltv": 2323,
        "monthly_velocity": 267,
        "sessions": 61,
        "orders": 8.4,
        "returns_per_customer": 2.8,
        "detection_accuracy": "Cannot predict early (need return data)",
        "key_traits": ["High spend", "High returns", "Same revenue as VIPs"],
        "marketing_strategy": "Implement return fees, improve descriptions"
    },
    {
        "name": "Big Ticket Buyer",
        "description": "Infrequent but high-value purchases",
        "ltv": 674,
        "monthly_velocity": 95,
        "sessions": 20,
        "orders": 1.8,
        "avg_order_value": 379,
        "detection_accuracy": "79%",
        "key_traits": ["High AOV", 'Seasonal', "Gift shoppers"],
        "marketing_strategy": "Holiday campaigns, gift guides, bundling"
    },
    {
        "name":  "Window Browser",
        "description": "Browser heavily but rarely purchase",
        "ltv": 154,
        "monthly_velocity": 17,
        "sessions": 70,
        "orders": 1.5,
        "detection_accuracy": "95%",
        "key_traits": ["High sessions", "Low conversion", "Research shoppers"],
        "marketing_strategy": "Cart abandonment, browser retargeting, minimal investment"
    },
    {
        "name": "Deal Hunter",
        "description": "Price-sensitive, waits for sales",
        "ltv": 312,
        "monthly_velocity": 56,
        "sessions": 34,
        "orders": 1.9,
        "detection_accuracy": "65%",
        "key_traits": ["Discount seekers", "Flash sale buyers"],
        "marketing_strategy": "Flash sales, loyalty rewards, clearance alerts"
    },
    {
        "name": "Casual Shopper",
        "description": "Standard customers, steady but unexciting",
        "ltv": 525,
        "monthly_velocity": 73,
        "sessions": 40,
        "orders": 2.6,
        "detection_accuracy": "Default category",
        "key_traits": ["Average engagement", "Mixed Behavior"],
        "marketing_strategy": "Standard nurture, occasional promotions"
    }
    ],
    "total_customers": 7282,
    "total_portfolio_value": 9171340,
    "value_at_risk": 1149037
}

@app.get("/stats")
async def get_stats():
    """ Get customer statistics from database"""
    try:
        conn = get_db_connection()

        #cluster distribution
        cluster_stats = conn.execute(""" 
            SELECT 
                cluster_name,
                COUNT(*) as customers,
                ROUND(AVG(monetary_total), 2) as avg_ltv,
                ROUND(AVG(total_sessions), 1) as avg_sessions,
                ROUND(AVG(frequency_orders), 1) as avg_orders 
            FROM rpt_behavioral_cluster
            GROUP BY cluster_name 
            ORDER BY avg_ltv DESC
            ORDER BY avg_ltv DESC
        """).fetchdf().to_dict(orient='records')

        #portfolio value
        portfolio = conn.execute("""
            SELECT 
                COUNT(*) as total_customers,
                ROUND(SUM(actual_ltv_to_date), 2) as current_value,
                ROUND(SUM(predicted_12m_ltv), 2) as predicted_value,
                ROUND(SUM(predicted_future_revenue), 2) as future_opportunity
            FROM rpt_ltv_forecast_v2
         """).fetchone()

         #risk analysis
        risk_stats = conn.execute(""" 
            SELECT
                risk_status,
                COUNT(*) as customers,
                ROUND(SUM(predicted_12m_ltv), 2) as value
            FROM rpt_ltv_forecast_v2
            GROUP BY risk_status
            ORDER BY value
         """).fetchdf().to_dict(orient='records')

        conn.close()

        return {
            "cluster_distribution": cluster_stats,
            "portfolio": {
                "total_customers": portfolio[0],
                "current_value": portfolio[1],
                "predicted_12m_value": portfolio[2],
                "future_opportunity": portfolio[3],
                "growth_potential_pct": round((portfolio[3] / portfolio[1]) * 100, 1)
            },
            "risk_status": risk_stats
         }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/recommendations/{persona}")
async def get_recommendations(persona: str):
    """
    Get product recommendations for a specific persona based on actual purchase affinity
    Returns top product pairs that are frequently bought together by this persona
    """
    try:
        conn = get_db_connection()

        persona_map = {
            "vip loyalist": "VIP Loyalists",
            "vip loyalists": "VIP Loyalists",
            "big ticket buyer": "Big Ticket Buyers",
            "big ticket buyers": "Big Ticket Buyers",
            "window browser": "Window Browsers",
            "window browsers": "Window Browers",
            "serial returner": "Serial Returners",
            "serial returners": "Serial Returners",
            "deal hunter": "Deal Hunters",
            "deal hunters": "Deal Hunters",
            "casual shopper": "Casual Shoppers",
            "casual shoppers": "Casual Shoppers"
        }

        #normalize persona name
        persona_normalized = persona_map.get(persona.lower(), persona.replace("_", " ").title())

        query = """
            SELECT 
                category_a,
                category_b,
                times_bought_together,
                confidence_pct,
                lift,
                recommendation_strength,
                recommendation_text
            FROM rpt_product_affinity_v2
            WHERE cluster_name = ?
                AND recommendation_strength IN ('Very Strong', 'Strong')
            ORDER BY times_bought_together DESC
            LIMIT 10
         """

        results = conn.execute(query, [persona_normalized]).fetchdf().to_dict(orient='records')
        conn.close()

        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No recommendations found for persona '{persona_normalized}'"
            )
        
        #extract insights
        top_combo = results[0]
        highest_lift = max(results, key=lambda x: x['lift'])

        return {
            "persona": persona_normalized,
            "top_recommendation": {
                "buy_together": f"{top_combo['category_a']} + {top_combo['category_b']}",
                "times_bought": top_combo['times_bought_together'],
                "confidence": f"{top_combo['confidence_pct']}%",
                "strength": top_combo['recommendation_strength']
            },
            "highest_lift": {
                "combo": f"{highest_lift['category_a']} + {highest_lift['category_b']}",
                "lift": f"{highest_lift['lift']}x more likely than random",
                "recommendation": f"Premium upsell opportunity - customers rarely but these separately"
            },
            "all_recommendations": results,
            "marketing_strategy": get_marketing_strategy(persona_normalized, results)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def get_marketing_strategy(persona: str, affinity_data: list) -> dict:
    """ Generate marketing strategy based on affinity patterns"""

    #find most common companion category
    category_counts = {}
    for item in affinity_data:
        cat_b = item['category_b']
        category_counts[cat_b] = category_counts.get(cat_b, 0) + item['times_bought_together']

    top_companion = max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else 'tops'

    strategies = {
        "VIP Loyalist": {
            "primary_tactic": "Bundle recommendations at checkout",
            "discount_strategy": "None needed - willing to pay full price",
            "messaging": f"Complete your look: Add {top_companion}",
            "email_frequency": "Weekly with exclusive new arrivals",
            "upsell_timing": "Immediately at card add"
        },
        "Big Ticket Buyer": {
            "primary_tactic": "Bundle recommendations at checkout",
            "discount_strategy": "None needed - willing to pay full price",
            "messaging": "Perfect gift combination: Outerwear + Accessories",
            "email_frequency": "Monthly, seasonal focus (Nov-Dec, Feb, May)",
            "upself_timing": "After first item added to cart"
        },
        "Serial Returner": {
            "primary_tactic": "Show complementary items with size guides",
            "discount_strategy": "None - control return rate",
            "messaging": f"Customers also bought {top_companion} in similar sizes",
            "email_frequency": "Standard weekly",
            "upsell_timing": "On product page, not at checkout"
        },
        "Window Browser": {
            "primary_tactic": "Show social proof - 'Others bought together'",
            "discount_strategy": "15% off bundle to encourage first purchase",
            "messaging": f"Bestseller combo: Outerwear + {top_companion}",
            "email_frequency": "After 3+ browsing sessions",
            "upsell_timing": "Persistent cart reminder"
        },
        "Deal Hunter": {
            "primary_tactic": "Flash sale bundles",
            "discount_strategy": "20% off when buying both categories",
            "messaging": f"Limited time: Dresses + {top_companion} bundle",
            "email_frequency": "Flash sales only (2-3x per month)",
            "upsell_timing": "During sale events only"
        },
        "Casual Shopper": {
            "primary_tactic": "Standard cross-sell at cart",
            "discount_strategy": "15% off second time occasionally",
            "messaging": f"Complete your outfit with {top_companion}",
            "email_frequency": "Weekly new arrivals",
            "upself_timing": "At cart or after first purchase"
        }

    }
    return strategies.get(persona, strategies["Casual Shopper"])


@app.get("/recommend-products")
async def recommend_products(
    persona: str =  Query(..., description='Customer persona'),
    current_cart: str = Query(None, description="Comma-separated categories in cart (e.g., 'dresses, shoes')"),
    limit: int = Query(3, ge=1, le=10, description="Number of recommendations")
):

    """
    Get specific product recommendations based on persona and current cart

    Example: /recommend-product?persona=VIP%20Loyalist&current_cart=dressess,outerwear&limit=3
    """
    try:
        conn = get_db_connection()

    #if cart is provided, find what's frequently bought with those items
        if current_cart:
            cart_categories = [c.strip() for c in current_cart.split(',')]

            query = """
                SELECT 
                    category_b as recommended_category,
                    AVG(confidence_pct) as avg_confidence,
                    AVG(lift) as avg_lift,
                    STRING_AGG(category_a, ', ') as pairs_with
                FROM rpt_product_affinity_v2
                WHERE cluster_name = ?
                    AND category_a IN ({})
                    AND recommendation_strength IN ('Very Strong', 'Strong')
                GROUP BY category_b
                ORDER BY avg_confidence DESC
                LIMIT ?
            """.format(','.join(['?'] * len(cart_categories)))

            params = [persona] + cart_categories + [limit]
            results = conn.execute(query, params).fetchdf().to_dict(orient='records')

            #get actual products from recommended categories
            recommendations = []
            for rec in results:
                try:
                    products_query = conn.execute(""" 
                        SELECT product_id, product_name, category, brand, base_price
                        FROM stg_products
                        WHERE category = ?
                        ORDER BY random()
                        LIMIT 3
                    """, [rec['recommended_category']])
                except:
                    #fallback to raw products table
                    products_query = conn.execute("""
                        SELECT product_id, product_name, category, brand, base_price
                        FROM main.products
                        WHERE lower(trim(category)) = ?
                        ORDER BY random()
                        LIMIT 3
                     """, [rec['recommended_category']])

                products = products_query.fetchdf().to_dict(orient='records')

                recommendations.append({
                    'category': rec['recommended_category'],
                    'confidence': f"{rec['avg_confidence']:.1f}%",
                    'why': f"Frequently bought with {rec['pairs_with']}",
                    'products': products 
                })

        else:
            #no cart - recommend based on persona's top categories
            query = """ 
                SELECT DISTINCT category_a as category
                FROM rpt_product_affinity_v2
                WHERE cluster_name = ?
                    AND recommendation_strength = 'Very Strong'
                ORDER BY times_bought_together DESC
                LIMIT ?
            """

            result_df = conn.execute(query, [persona, limit]).fetchdf()

            if len(result_df) == 0:
                conn.close()
                raise HTTPException(
                    status_code=404,
                    detail=f"No product affinity data found for persona '{persona}'. Try: VIP Loyalists, Big Ticket Buyers, Serial Returners, Deal Hunters, Causal Shoppers, Window Browsers"
                )

            categories = result_df['category'].tolist()

            recommendations = []
            for cat in categories:
                try:
                    products_query = conn.execute("""
                        SELECT product_id, product_name, category, brand, base_price
                        FROM stg_products
                        WHERE category = ?
                        ORDER BY random()
                        LIMIT 3
                    """, [cat])
                except:
                    products_query = conn.execute("""
                        SELECT product_id, product_name, category, brand, base_price
                        FROM main.products
                        WHERE lower(trim(category)) = ?
                        ORDER BY random()
                        LIMIT 3
                     """, [cat])

                products = products_query.fetchdf().to_dict(orient='records')

                recommendations.append({
                    'category': cat,
                    'why': f"Popular category for {persona}",
                    "products": products 
                })
        conn.close()

        return {
            "persona": persona,
            "current_cart": current_cart.split(',') if current_cart else [],
            "recommendations": recommendations,
            "recommendation_type": "cart-based" if current_cart else "persona-based"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/at-risk")
async def get_at_risk_customers(
    limit: int = Query(100, ge=1, le=500, description="Number of customers to return"),
    min_ltv: float = Query(1000, ge=0, description="Minimum LTV threshold")
):
    """
    Get list of high-value at-risk customers for win-back campaigns

    Returns customers with:
    - Risk status: "High Value At Risk" or "At Risk"
    - LTV above threshold
    - Sorted by predicted LTV (highest first)
    """
    try:
        conn = get_db_connection()

        query = """
            SELECT 
                customer_id,
                cluster_name,
                ROUND(actual_ltv_to_date, 2) as actual_ltv,
                ROUND(predicted_12m_ltv, 2) as predicted_ltv,
                days_since_last_order,
                churn_probability,
                risk_status
            FROM rpt_ltv_forecast_v2
            WHERE risk_status IN ('High Value At Risk', 'At Risk')
                AND actual_ltv_to_date >= ?
            ORDER BY predicted_12m_ltv DESC
            LIMIT ?
        """

        results = conn.execute(query, [min_ltv, limit]).fetchdf().to_dict(orient='records')
        conn.close()

        return {
            'count': len(results),
            'total_value_at_risk': sum(r['predicted_ltv'] for r in results),
            'customers': results,
            'recommended_campaign': {
                'tier_1_count': len([r for r in results if r['predicted_ltv'] >= 3000]),
                'tier_2_count': len([r for r in results if 2000 <= r['predicted_ltv'] < 3000]),
                'tier_3_count': len([r for r in results if r['predicted_ltv'] < 2000]),
                'estimated_recovery_20pct': sum(r['predicted_ltv'] for r in results) * 0.20,
                'estimated_recovery_30pct': sum(r['predicted_ltv'] for r in results) * 0.30
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")



if __name__ == "__main__":
    print("🚀 Starting StyleHub Persona Prediction API...")
    print("📊 API docs: http://localhost:8000/docs")
    print("🔍 Interactive docs: http://localhost:8000/redoc")
    print("\n📡 Available endpoints:")
    print("  POST /predict - Predict persona from early signals")
    print("  GET /custoemr/{id} - Get full customer profile")
    print("  POST /batch - Batch predictions")
    print("  GET /persona - List all personas")
    print("  GET /stats - Database statistics")
    print("  GET /recommendations/{persona} - Get recommendations")
    print("  GET /at-risk - Get at-risk customers for win-back")
    print("\n🧪 Test prediction:")
    print("  curl -X POST http://localhost:8000/predict \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"sessions_first_7d\": 15, \"purchases_first_7d\": 0}'")

uvicorn.run(app, host="0.0.0.0", port=8000)