from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
from sqlalchemy.orm import Session
import json
import os
from dotenv import load_dotenv

from database import engine, get_db, Base
from models import ChatHistory
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

SYSTEM_PROMPT = f"""You are a friendly shopping assistant chatbot for an e-commerce platform.

You have 2 tools:
- search_products: when the customer asks about any product or category
- get_product_details: when the customer wants details about a specific product (use product id from search)

**General Approach:**
- Before calling any tool, try to understand what the customer really wants.
- If the request is vague (e.g., "I need a laptop", "show me shoes"), politely ask follow-up questions:
  - "What kind of [product] are you looking for?"
  - "Do you have a budget in mind?"
  - "Any preferred brand or features?"
- Only after you have enough details (at least the type and budget range) should you call `search_products` with appropriate filters.

**Phone Inquiries (example flow):**
- If the customer says "I need a mobile", "I need a phone", etc., do **not** search immediately.
- Ask: "What type of phone are you looking for – a smartphone or a basic phone?"
- Then ask: "What's your budget range? (low / mid / high, or a specific amount)"
- Only then search with:
  - `category`: "smartphones" (or whatever type they said)
  - `min_price` / `max_price` based on budget (low: <300, mid: 300-700, high: >700)

**Other Product Categories:**
- For laptops, shoes, watches, etc., follow the same principle:
  - Ask for the category (if not already clear), budget, and any specific features.
- Use the `category` filter when possible (e.g., "laptops", "mens-shoes") and price filters.

**Rules:**
1. Always respond in English.
2. When showing products, use the tool results – never invent products.
3. Keep your text reply short and friendly. The frontend will display product images, prices, and descriptions automatically from the tool response.
4. If the customer wants to order or buy, politely provide the order link (included in the product data).
5. If the customer says bye, thanks, or goodbye, reply with EXACTLY this message and nothing else:
{FIXED_GOODBYE}
"""

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
                    "in_stock": {"type": "boolean", "description": "If true, return only in-stock products"}
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


# ============================================================
# Chat UI
# ============================================================

@app.get("/", response_class=HTMLResponse)
def chat_ui():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no"/>
<title>ShopBot</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
    background: #0b141a;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 20px;
  }

  .chat-container {
    width: 100%;
    max-width: 800px;
    height: 90vh;
    background: #e5ddd5;
    border-radius: 12px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  }

  .header {
    background: #075e54;
    color: white;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }

  .avatar {
    width: 40px; height: 40px;
    background: #128c7e;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
  }

  .header-info h2 { font-size: 18px; font-weight: 500; margin: 0; }
  .header-info p  { font-size: 12px; opacity: 0.8; margin: 0; }

  .user-selector {
    background: #f0f2f5;
    padding: 10px 16px;
    border-bottom: 1px solid #ddd;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }

  .user-selector label { font-size: 14px; font-weight: 500; color: #075e54; }
  .user-selector select {
    padding: 6px 12px;
    border-radius: 20px;
    border: 1px solid #ccc;
    background: white;
    font-size: 14px;
    outline: none;
  }

  /* NEW: Clear History button style */
  .clear-btn {
    margin-left: auto;
    background: #dc3545;
    color: white;
    border: none;
    border-radius: 20px;
    padding: 6px 12px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
  }
  .clear-btn:hover { background: #c82333; }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .msg-row {
    display: flex;
    width: 100%;
    animation: fadeIn 0.2s ease;
  }
  .msg-row.user { justify-content: flex-end; }
  .msg-row.bot  { justify-content: flex-start; }

  .user-bubble {
    background: #dcf8c5;
    color: #111;
    padding: 8px 13px;
    border-radius: 16px;
    border-bottom-right-radius: 3px;
    font-size: 14px;
    line-height: 1.5;
    max-width: 70%;
    word-wrap: break-word;
  }

  .bot-block {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    max-width: 85%;
  }

  .bot-bubble {
    display: inline-block;
    background: #ffffff;
    color: #111;
    padding: 8px 13px;
    border-radius: 16px;
    border-bottom-left-radius: 3px;
    font-size: 14px;
    line-height: 1.5;
    word-wrap: break-word;
    box-shadow: 0 1px 2px rgba(0,0,0,0.15);
    max-width: 100%;
  }

  .typing-bubble {
    display: inline-flex;
    gap: 5px;
    align-items: center;
    background: #ffffff;
    padding: 10px 14px;
    border-radius: 16px;
    border-bottom-left-radius: 3px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.15);
  }

  .dot {
    width: 7px; height: 7px;
    background: #aaa;
    border-radius: 50%;
    animation: bounce 1.3s infinite;
  }
  .dot:nth-child(2) { animation-delay: 0.18s; }
  .dot:nth-child(3) { animation-delay: 0.36s; }

  @keyframes bounce {
    0%, 60%, 100% { transform: translateY(0); }
    30%           { transform: translateY(-5px); }
  }

  .products-row {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 10px;
  }

  .product-card {
    background: #ffffff;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    width: 180px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
  }

  .product-card img {
    width: 100%;
    height: 160px;
    object-fit: cover;
    display: block;
    background: #f0f0f0;
  }

  .card-info {
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
  }

  .card-name  { font-size: 13px; font-weight: 600; color: #111; line-height: 1.3; }
  .card-price { font-size: 15px; font-weight: 700; color: #075e54; }
  .card-desc  { font-size: 12px; color: #666; line-height: 1.4; flex: 1; margin-top: 2px; }

  .card-btn {
    margin-top: 8px;
    display: inline-block;
    background: #075e54;
    color: #fff;
    border: none;
    padding: 7px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
    align-self: flex-start;
  }
  .card-btn:hover { background: #128c7e; }

  .input-area {
    background: #f0f2f5;
    padding: 12px 16px;
    display: flex;
    gap: 12px;
    align-items: center;
    border-top: 1px solid #ddd;
    flex-shrink: 0;
  }

  .input-area input {
    flex: 1;
    padding: 10px 16px;
    border: none;
    border-radius: 24px;
    background: white;
    font-size: 14px;
    outline: none;
  }

  .send-btn {
    background: #075e54;
    border: none;
    width: 42px; height: 42px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer;
    transition: background 0.2s;
    flex-shrink: 0;
  }
  .send-btn:hover { background: #128c7e; }
  .send-btn svg { width: 20px; height: 20px; fill: white; }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
  }
</style>
</head>
<body>
<div class="chat-container">

  <div class="header">
    <div class="avatar">🛍️</div>
    <div class="header-info">
      <h2>SmartShopAI</h2>
      <p>AI Shopping Assistant</p>
    </div>
  </div>

  <div class="user-selector">
    <label>👤 User:</label>
    <select id="userIdSelect">
      <option value="alice">Alice</option>
      <option value="bob">Bob</option>
      <option value="charlie">Charlie</option>
      <option value="david" selected>David</option>
    </select>
    <!-- NEW: Clear History button -->
    <button id="clearHistoryBtn" class="clear-btn">🗑️ Clear History</button>
  </div>

  <div class="messages" id="messages"></div>

  <div class="input-area">
    <input type="text" id="userInput" placeholder="Type a message" autofocus />
    <button class="send-btn" onclick="sendMessage()">
      <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg>
    </button>
  </div>

</div>

<script>
const messagesDiv = document.getElementById('messages');

function scrollToBottom() {
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function esc(text) {
  const d = document.createElement('div');
  d.textContent = String(text || '');
  return d.innerHTML;
}

function buildProductCard(p) {
  return `
    <div class="product-card">
      <img src="${esc(p.image_url)}" alt="${esc(p.name)}" onerror="this.style.display='none'" />
      <div class="card-info">
        <div class="card-name">${esc(p.name || 'Product')}</div>
        <div class="card-price">${esc(p.price || '')}</div>
        <div class="card-desc">${esc(p.description || '')}</div>
        ${p.order_link ? `<button class="card-btn" onclick="window.open('${esc(p.order_link)}','_blank')">🛒 Order Now</button>` : ''}
      </div>
    </div>`;
}

function addMessage(role, content, products, extra) {
  products = Array.isArray(products) ? products : [];
  extra    = extra || {};

  if (products.length === 0 && extra.image_url) {
    products = [{
      name:        extra.name        || '',
      price:       extra.price       || '',
      description: extra.description || '',
      image_url:   extra.image_url,
      order_link:  extra.order_link  || '',
    }];
  }

  const row = document.createElement('div');
  row.className = `msg-row ${role}`;

  if (role === 'user') {
    if (!content || !content.trim()) return;
    row.innerHTML = `<div class="user-bubble">${esc(content).replace(/\\n/g,'<br>')}</div>`;
  } else {
    const hasText     = content && content.trim();
    const hasProducts = products.length > 0;
    if (!hasText && !hasProducts) return;

    let inner = '';
    if (hasText) {
      inner += `<div class="bot-bubble">${esc(content).replace(/\\n/g,'<br>')}</div>`;
    }
    if (hasProducts) {
      inner += `<div class="products-row">${products.map(buildProductCard).join('')}</div>`;
    }
    row.innerHTML = `<div class="bot-block">${inner}</div>`;
  }

  messagesDiv.appendChild(row);
  scrollToBottom();
}

function showTyping() {
  const row = document.createElement('div');
  row.className = 'msg-row bot';
  row.id = 'typing-row';
  row.innerHTML = `<div class="bot-block"><div class="typing-bubble"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div></div>`;
  messagesDiv.appendChild(row);
  scrollToBottom();
}

function hideTyping() {
  const el = document.getElementById('typing-row');
  if (el) el.remove();
}

async function loadHistory(userId) {
  messagesDiv.innerHTML = '';
  showTyping();
  try {
    const res = await fetch(`/history/${userId}`);
    if (!res.ok) throw new Error('History fetch failed');
    const history = await res.json();
    hideTyping();
    history.forEach(m => addMessage(m.role, m.content, m.products, {
      image_url:  m.image_url,
      order_link: m.order_link,
    }));
  } catch (err) {
    hideTyping();
    addMessage('bot', '👋 Hello! How can I help you today?');
  }
}

async function sendMessage() {
  const input  = document.getElementById('userInput');
  const userId = document.getElementById('userIdSelect').value;
  const text   = input.value.trim();
  if (!text) return;
  input.value = '';

  addMessage('user', text);
  showTyping();

  try {
    const res  = await fetch('/reply', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ user_id: userId, message: text }),
    });
    if (!res.ok) throw new Error('Reply failed');
    const data = await res.json();
    hideTyping();
    addMessage('bot', data.reply, data.products, {
      image_url:  data.image_url,
      order_link: data.order_link,
    });
  } catch (err) {
    hideTyping();
    addMessage('bot', '❌ Sorry, something went wrong. Please try again.');
  }
}

// NEW: Clear history function
async function clearHistory() {
  const userId = document.getElementById('userIdSelect').value;
  if (!confirm(`Are you sure you want to delete all chat history for ${userId}?`)) return;
  try {
    const response = await fetch(`/history/${userId}`, { method: 'DELETE' });
    if (response.ok) {
      loadHistory(userId); // reload history after deletion
    } else {
      alert('Failed to clear history.');
    }
  } catch (err) {
    console.error(err);
    alert('Error clearing history.');
  }
}

document.getElementById('userIdSelect').addEventListener('change', e => {
  loadHistory(e.target.value);
});

document.getElementById('userInput').addEventListener('keypress', e => {
  if (e.key === 'Enter') sendMessage();
});

// NEW: Attach clear button event
document.getElementById('clearHistoryBtn').addEventListener('click', clearHistory);

loadHistory(document.getElementById('userIdSelect').value);
</script>
</body>
</html>
"""

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


# NEW: Delete all history for a user
@app.delete("/history/{user_id}")
def delete_chat_history(user_id: str, db: Session = Depends(get_db)):
    deleted = db.query(ChatHistory).filter(ChatHistory.user_id == user_id).delete()
    db.commit()
    return {"deleted": deleted}


@app.post("/reply", response_model=ChatResponse)
def generate_reply(data: ChatRequest, db: Session = Depends(get_db)):
    existing = db.query(ChatHistory).filter(ChatHistory.user_id == data.user_id).first()
    if not existing:
        save_message(data.user_id, "assistant", FIXED_WELCOME, db)
        return ChatResponse(reply=FIXED_WELCOME)

    history = get_history(data.user_id, db)
    history.append({"role": "user", "content": data.message})
    save_message(data.user_id, "user", data.message, db)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history]

    image_url = None
    order_link = None
    products = []

    while True:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=700,
        )

        ai_message = response.choices[0].message

        if ai_message.tool_calls:
            messages.append(ai_message)

            for tool_call in ai_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                tool_result_str = run_tool(tool_name, tool_args)
                tool_result = json.loads(tool_result_str)

                if tool_result.get("found"):
                    if "products" in tool_result:
                        for p in tool_result["products"]:
                            products.append({
                                "name":        p.get("name", ""),
                                "price":       p.get("price", ""),
                                "description": p.get("description", ""),
                                "image_url":   p.get("image_url", ""),
                                "order_link":  p.get("order_link", ""),
                            })
                        if products:
                            image_url  = products[0]["image_url"]
                            order_link = products[0]["order_link"]
                    elif "image_url" in tool_result:
                        image_url  = tool_result["image_url"]
                        order_link = tool_result.get("order_link")
                        products   = [{
                            "name":        tool_result.get("name", ""),
                            "price":       tool_result.get("price", ""),
                            "description": tool_result.get("description", ""),
                            "image_url":   tool_result["image_url"],
                            "order_link":  tool_result.get("order_link", ""),
                        }]

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      tool_result_str,
                })
            continue

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