from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
from sqlalchemy.orm import Session
import json
import os
from dotenv import load_dotenv

from database import engine, get_db, Base
from models import ChatHistory, Order
from tools import search_products, get_product_details

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_HISTORY = 20

FIXED_WELCOME = (
    "👋 Hello! Welcome to ShopBot, your AI shopping assistant. "
    "I can help you find the best products, check prices, and place orders easily. "
    "What are you looking for today? 😊"
)

FIXED_GOODBYE = (
    "🙏 It was a pleasure chatting with you! I hope you found what you were looking for. "
    "If you need anything else, I'm here to help. Take care! 😊"
)

# Load system prompt from file
def load_system_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()
    # Format with FIXED_GOODBYE (and maybe FIXED_WELCOME if used)
    return template.format(FIXED_GOODBYE=FIXED_GOODBYE)

SYSTEM_PROMPT = load_system_prompt()

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search products by keyword or description with optional filters",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword e.g. smartphone, laptop, shoes"},
                    "category": {"type": "string", "description": "Filter by category e.g. smartphones, laptops, skin-care"},
                    "max_price": {"type": "number", "description": "Maximum price in USD e.g. 50 means under 50 dollars"},
                    "min_price": {"type": "number", "description": "Minimum price in USD"},
                    "min_rating": {"type": "number", "description": "Minimum rating out of 5 e.g. 4.0 for top rated"},
                    "in_stock": {"type": "boolean", "description": "If true, return only in-stock products"},
                    "limit": {"type": "integer", "description": "Maximum number of products to return (default 4)"},
                    "sort_by": {"type": "string", "description": "Sort order: 'rating', 'price_asc', 'price_desc' (default 'rating')"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get full details of a specific product by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "Product ID from search results"}
                },
                "required": ["product_id"]
            }
        }
    },

    {
    "type": "function",
    "function": {
        "name": "place_order",
        "description": "Place an order for a product. Call this when the customer wants to buy a product.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "Product ID from search results"},
                "product_name": {"type": "string", "description": "Name of the product"},
                "quantity": {"type": "integer", "description": "Number of items to order (default 1)"},
                "customer_name": {"type": "string", "description": "Full name of the customer"},
                "customer_email": {"type": "string", "description": "Email address of the customer"},
                "address": {"type": "string", "description": "Shipping address"},
                "phone": {"type": "string", "description": "Phone number for contact"},
                "notes": {"type": "string", "description": "Any special instructions"}
            },
            "required": ["product_id", "product_name", "customer_name", "customer_email", "address"]
        }
    }
}
]


def run_tool(tool_name: str, args: dict) -> str:
    if tool_name == "search_products":
        result = search_products(
            query=args.get("query", ""),
            category=args.get("category"),
            max_price=args.get("max_price"),
            min_price=args.get("min_price"),
            min_rating=args.get("min_rating"),
            in_stock=args.get("in_stock"),
            limit=args.get("limit", 4),
            sort_by=args.get("sort_by", "rating")
        )
    elif tool_name == "get_product_details":
        result = get_product_details(args["product_id"])
    else:
        result = {"error": "Unknown tool"}
    return json.dumps(result, ensure_ascii=False)


def get_history(user_id: str, db: Session) -> list:
    rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(MAX_HISTORY)
        .all()
    )
    rows.reverse()

    history = []
    for r in rows:
        item = {"role": r.role, "content": r.content}
        if r.metadata_json:
            try:
                extra = json.loads(r.metadata_json)
                if extra.get("products"):
                    item["products"] = extra["products"]
                if extra.get("image_url"):
                    item["image_url"] = extra["image_url"]
                if extra.get("order_link"):
                    item["order_link"] = extra["order_link"]
            except Exception:
                pass
        history.append(item)
    return history


def save_message(user_id: str, role: str, content: str, db: Session, metadata: dict | None = None):
    history_item = ChatHistory(user_id=user_id, role=role, content=content)
    if metadata:
        history_item.metadata_json = json.dumps(metadata, ensure_ascii=False)
    db.add(history_item)
    db.commit()

def save_order(user_id: str, order_args: dict, db: Session) -> dict:
    order = Order(
        user_id=user_id,
        customer_name=order_args["customer_name"],
        customer_email=order_args["customer_email"],
        product_id=order_args["product_id"],
        product_name=order_args["product_name"],
        quantity=order_args.get("quantity", 1),
        address=order_args["address"],
        phone=order_args.get("phone", ""),
        notes=order_args.get("notes", "")
    )
    db.add(order)
    db.commit()
    return {"success": True, "message": "Your order has been placed! Thank you for shopping with us."}


# ============================================================
# Chat UI
# ============================================================

@app.get("/", response_class=HTMLResponse)
def chat_ui():
    return HTMLResponse(content=open("static/index.html", "r", encoding="utf-8").read(), status_code=200)

# API Endpoints
class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    image_url: str | None = None
    order_link: str | None = None
    products: list | None = None


@app.get("/history/{user_id}")
def get_chat_history(user_id: str, db: Session = Depends(get_db)):
    return get_history(user_id, db)


@app.delete("/history/{user_id}")
def delete_chat_history(user_id: str, db: Session = Depends(get_db)):
    deleted = db.query(ChatHistory).filter(ChatHistory.user_id == user_id).delete()
    db.commit()
    return {"deleted": deleted}


@app.post("/reply", response_model=ChatResponse)
def generate_reply(data: ChatRequest, db: Session = Depends(get_db)):
    # Removed automatic welcome – let the conversation start naturally.
    history = get_history(data.user_id, db)
    # Add the user message to history (for saving later)
    # We'll save after we generate the reply, but we need the user message in context.
    # We'll create a new list with the user message appended for the AI.
    messages_for_ai = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        messages_for_ai.append({"role": msg["role"], "content": msg["content"]})
    messages_for_ai.append({"role": "user", "content": data.message})

    # Save the user message now (so it appears in history even if something fails)
    save_message(data.user_id, "user", data.message, db)

    image_url = None
    order_link = None
    products = []

    while True:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_for_ai,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=700,
        )

        ai_message = response.choices[0].message

        if ai_message.tool_calls:
            messages_for_ai.append(ai_message)   # append the assistant message with tool calls
            for tool_call in ai_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                if tool_name == "place_order":
                    # Save order directly using our function
                    result = save_order(data.user_id, tool_args, db)
                    tool_result_str = json.dumps(result, ensure_ascii=False)
                else:
                    # For search_products and get_product_details
                    tool_result_str = run_tool(tool_name, tool_args)

                tool_result = json.loads(tool_result_str)

                # Process products from search_products (as before)
                if tool_result.get("found"):
                    if "products" in tool_result:
                        for p in tool_result["products"]:
                            products.append({
                                "name":        p.get("name", ""),
                                "price":       p.get("price", ""),
                                "description": p.get("description", ""),
                                "image_url":   p.get("image_url", ""),
                                # No order_link
                            })
                        if products:
                            image_url = products[0]["image_url"]
                    elif "image_url" in tool_result:
                        image_url = tool_result["image_url"]
                        products = [{
                            "name":        tool_result.get("name", ""),
                            "price":       tool_result.get("price", ""),
                            "description": tool_result.get("description", ""),
                            "image_url":   tool_result["image_url"],
                        }]

                messages_for_ai.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result_str,
                })
            continue   # loop again to get the final answer after tools

        reply_text = ai_message.content
        break

    save_message(
        data.user_id, "assistant", reply_text, db,
        metadata={
            "products":   products   if products   else None,
            "image_url":  image_url,
            "order_link": order_link,
        },
    )

    return ChatResponse(
        reply=reply_text,
        image_url=image_url,
        order_link=order_link,
        products=products if products else None,
    )

@app.get("/conversations")
def get_conversations(db: Session = Depends(get_db)):
    from sqlalchemy import func, and_
    # Get first user message for each user_id
    subq = db.query(
        ChatHistory.user_id,
        func.min(ChatHistory.created_at).label('first_time')
    ).filter(ChatHistory.role == 'user').group_by(ChatHistory.user_id).subquery()
    first_msgs = db.query(ChatHistory).join(
        subq,
        and_(ChatHistory.user_id == subq.c.user_id, ChatHistory.created_at == subq.c.first_time)
    ).all()
    
    # Get latest timestamp per user_id
    latest_times = db.query(
        ChatHistory.user_id,
        func.max(ChatHistory.created_at).label('last_time')
    ).group_by(ChatHistory.user_id).all()
    time_map = {t.user_id: t.last_time for t in latest_times}
    
    conversations = []
    for msg in first_msgs:
        conversations.append({
            "user_id": msg.user_id,
            "title": msg.content[:50],
            "last_updated": time_map.get(msg.user_id, msg.created_at).isoformat()
        })
    conversations.sort(key=lambda x: x['last_updated'], reverse=True)
    return conversations