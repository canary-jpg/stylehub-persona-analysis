select 
    product_id,
    product_name,
    lower(trim(category)) as category,
    lower(trim(brand)) as brand,
    base_price,
    avg_rating,
    num_reviews
from products