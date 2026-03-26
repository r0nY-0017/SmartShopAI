import httpx
import os
from difflib import get_close_matches
from typing import Optional

DUMMYJSON_BASE = "https://dummyjson.com"
ORDER_BASE_URL = os.getenv("ORDER_BASE_URL", "https://yoursite.com/order")

CATEGORIES = [
    "beauty", "fragrances", "furniture", "groceries", "home-decoration",
    "kitchen-accessories", "laptops", "mens-shirts", "mens-shoes", "mens-watches",
    "mobile-accessories", "motorcycle", "skin-care", "smartphones", "sports-accessories",
    "sunglasses", "tablets", "tops", "vehicle", "womens-bags", "womens-dresses",
    "womens-jewellery", "womens-shoes", "womens-watches"
]

CATEGORY_MAP = {
    # Smartphones
    "phone": "smartphones",
    "phones": "smartphones",
    "mobile": "smartphones",
    "mobiles": "smartphones",
    "smartphone": "smartphones",
    "smart phones": "smartphones",
    "cellphone": "smartphones",
    "cell phones": "smartphones",
    "handphone": "smartphones",

    # Laptops
    "laptop": "laptops",
    "laptops": "laptops",
    "notebook": "laptops",
    "notebooks": "laptops",
    "computer": "laptops",
    "pc": "laptops",

    # Shoes
    "shoe": "mens-shoes",
    "shoes": "mens-shoes",
    "footwear": "mens-shoes",
    "sneakers": "mens-shoes",
    "boots": "mens-shoes",
    "sandals": "mens-shoes",

    # Watches
    "watch": "mens-watches",
    "watches": "mens-watches",
    "wristwatch": "mens-watches",

    # Shirts
    "shirt": "mens-shirts",
    "shirts": "mens-shirts",
    "t-shirt": "mens-shirts",
    "tshirt": "mens-shirts",

    # Beauty / skincare
    "beauty": "beauty",
    "skincare": "skin-care",
    "skin care": "skin-care",
    "cosmetics": "beauty",
    "makeup": "beauty",

    # Furniture
    "furniture": "furniture",
    "chair": "furniture",
    "table": "furniture",
    "sofa": "furniture",

    # Fragrances
    "fragrance": "fragrances",
    "perfume": "fragrances",
    "cologne": "fragrances",

    # Electronics
    "tablet": "tablets",
    "tablets": "tablets",
    "accessory": "mobile-accessories",
    "accessories": "mobile-accessories",
    "charger": "mobile-accessories",
    "case": "mobile-accessories",

    # Home
    "kitchen": "kitchen-accessories",
    "home": "home-decoration",
    "decoration": "home-decoration",

    # Sports
    "sport": "sports-accessories",
    "sports": "sports-accessories",
    "fitness": "sports-accessories",
}

def find_matching_category(query: str) -> Optional[str]:
    q = query.lower().strip()
    if q in CATEGORY_MAP:
        return CATEGORY_MAP[q]
    q_hyphen = q.replace(" ", "-")
    for cat in CATEGORIES:
        if q in cat or cat in q or q_hyphen in cat or cat in q_hyphen:
            return cat
    close_matches = get_close_matches(q, CATEGORIES, n=1, cutoff=0.6)
    if close_matches:
        return close_matches[0]
    return None

def apply_filters(products, min_price=None, max_price=None, min_rating=None, in_stock=None):
    filtered = []
    for p in products:
        if min_price is not None and p["price"] < min_price:
            continue
        if max_price is not None and p["price"] > max_price:
            continue
        if min_rating is not None and p.get("rating", 0) < min_rating:
            continue
        if in_stock is True and p.get("stock", 0) <= 0:
            continue
        filtered.append(p)
    return filtered

def sort_products(products, sort_by="rating"):
    if sort_by == "price_asc":
        return sorted(products, key=lambda x: x["price"])
    elif sort_by == "price_desc":
        return sorted(products, key=lambda x: x["price"], reverse=True)
    elif sort_by == "rating":
        return sorted(products, key=lambda x: x.get("rating", 0), reverse=True)
    else:
        return products

def format_products(products, limit=4):
    formatted = []
    for p in products[:limit]:
        formatted.append({
            "id": p["id"],
            "name": p["title"],
            "price": f"${p['price']}",
            "raw_price": p["price"],
            "description": p["description"],
            "category": p.get("category", ""),
            "rating": p.get("rating", "N/A"),
            "stock": p.get("stock", 0),
            "image_url": p["thumbnail"],
            "order_link": f"{ORDER_BASE_URL}/{p['id']}",
        })
    return formatted

def search_products(
    query: str,
    max_price: float = None,
    min_price: float = None,
    min_rating: float = None,
    in_stock: bool = None,
    category: str = None,
    sort_by: str = "rating",
    limit: int = 4,
) -> dict:
    try:
        with httpx.Client(timeout=10) as client:
            if category:
                matched_cat = find_matching_category(category)
                if matched_cat:
                    url = f"{DUMMYJSON_BASE}/products/category/{matched_cat}"
                else:
                    return {"found": False, "message": f"Unknown category: {category}"}
            else:
                # Search by query first
                search_url = f"{DUMMYJSON_BASE}/products/search?q={query}&limit=50"
                res = client.get(search_url)
                products = res.json().get("products", [])
                if not products:
                    inferred_cat = find_matching_category(query)
                    if inferred_cat:
                        url = f"{DUMMYJSON_BASE}/products/category/{inferred_cat}"
                    else:
                        return {"found": False, "message": "No products found."}
                else:
                    # We already have products from search
                    pass

            if 'url' in locals():
                res = client.get(f"{url}?limit=50")
                products = res.json().get("products", [])

        if not products:
            return {"found": False, "message": "No products found."}

        filtered = apply_filters(
            products,
            min_price=min_price,
            max_price=max_price,
            min_rating=min_rating,
            in_stock=in_stock,
        )

        if not filtered:
            return {"found": False, "message": "No products match your filters. Try relaxing them."}

        sorted_products = sort_products(filtered, sort_by)
        formatted = format_products(sorted_products, limit)

        return {
            "found": True,
            "total_found": len(sorted_products),
            "products": formatted,
        }

    except httpx.ConnectError:
        return {"found": False, "message": "Could not connect to product API."}
    except httpx.TimeoutException:
        return {"found": False, "message": "Product API request timed out."}
    except Exception as e:
        return {"found": False, "message": f"Unexpected error: {str(e)}"}

def get_product_details(product_id: int) -> dict:
    try:
        with httpx.Client(timeout=10) as client:
            res = client.get(f"{DUMMYJSON_BASE}/products/{product_id}")
            p = res.json()

        if "id" not in p:
            return {"found": False, "message": "Product not found."}

        return {
            "found": True,
            "id": p["id"],
            "name": p["title"],
            "price": f"${p['price']}",
            "description": p["description"],
            "category": p["category"],
            "rating": p.get("rating", "N/A"),
            "stock": p.get("stock", "N/A"),
            "image_url": p["thumbnail"],
            "order_link": f"{ORDER_BASE_URL}/{p['id']}",
        }

    except Exception as e:
        return {"found": False, "message": f"API error: {str(e)}"}