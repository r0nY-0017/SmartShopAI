import httpx

DUMMYJSON_BASE = "https://dummyjson.com"

CATEGORIES = [
    "beauty", "fragrances", "furniture", "groceries", "home-decoration",
    "kitchen-accessories", "laptops", "mens-shirts", "mens-shoes", "mens-watches",
    "mobile-accessories", "motorcycle", "skin-care", "smartphones", "sports-accessories",
    "sunglasses", "tablets", "tops", "vehicle", "womens-bags", "womens-dresses",
    "womens-jewellery", "womens-shoes", "womens-watches"
]


def find_matching_category(query: str) -> str | None:
    q = query.lower().replace(" ", "-")
    for cat in CATEGORIES:
        if q in cat or cat in q:
            return cat
    return None


def apply_filters(products: list, min_price=None, max_price=None, min_rating=None, in_stock=None) -> list:
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


def format_products(products: list) -> list:
    return [
        {
            "id": p["id"],
            "name": p["title"],
            "price": f"${p['price']}",
            "raw_price": p["price"],
            "description": p["description"],
            "category": p.get("category", ""),
            "rating": p.get("rating", "N/A"),
            "stock": p.get("stock", 0),
            "image_url": p["thumbnail"],
            "order_link": f"https://yoursite.com/order/{p['id']}",
        }
        for p in products
    ]


def search_products(
    query: str,
    max_price: float = None,
    min_price: float = None,
    min_rating: float = None,
    in_stock: bool = None,
    category: str = None,
) -> dict:
    try:
        with httpx.Client(timeout=10) as client:
            if category:
                matched_cat = find_matching_category(category)
                if matched_cat:
                    res = client.get(f"{DUMMYJSON_BASE}/products/category/{matched_cat}?limit=50")
                    products = res.json().get("products", [])
                else:
                    products = []
            else:
                res = client.get(f"{DUMMYJSON_BASE}/products/search?q={query}&limit=50")
                products = res.json().get("products", [])

                if not products:
                    matched_cat = find_matching_category(query)
                    if matched_cat:
                        res = client.get(f"{DUMMYJSON_BASE}/products/category/{matched_cat}?limit=50")
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
            return {
                "found": False,
                "message": "No products match your filters. Try relaxing them."
            }

        filtered.sort(key=lambda x: x.get("rating", 0), reverse=True)

        return {
            "found": True,
            "total_found": len(filtered),
            "products": format_products(filtered[:4]),
        }

    except Exception as e:
        return {"found": False, "message": f"API error: {str(e)}"}


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
            "order_link": f"https://yoursite.com/order/{p['id']}",
        }

    except Exception as e:
        return {"found": False, "message": f"API error: {str(e)}"}