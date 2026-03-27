# 🛒 SmartShopAI – AI Shopping Assistant

SmartShopAI is an intelligent shopping assistant chatbot that helps users find products, compare them, and place orders conversationally. It leverages OpenAI's GPT-4o-mini to understand natural language, integrates with a product API (DummyJSON), and stores conversations and orders in Supabase (PostgreSQL).

---

## ✨ Key Features

- 🔍 **Natural Language Product Search** – Ask for products like "show me smartphones under $500" and the bot will ask clarifying questions before searching.

- 🎨 **Rich Product Cards** – Products are displayed as interactive cards with images, prices, descriptions, and ratings.

- 🌍 **Multi-Language Support** – Automatically detects and responds in Iraqi Arabic, English, Kurdish, or Bengali.

- 📦 **Order Placement** – Users can order products by providing their name, email, address, and phone number; orders are stored in Supabase.

- 💬 **Chat History** – Each user's conversation is saved, and you can resume or delete past chats.

- 🌓 **Theme Toggle** – Light/Dark mode support.

- 📱 **Responsive Design** – Works seamlessly on desktop and mobile devices.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI (Python) |
| **AI Model** | OpenAI GPT-4o-mini |
| **Database** | PostgreSQL (Supabase) / SQLite (Local) |
| **Product API** | DummyJSON |
| **Frontend** | HTML / CSS / JavaScript |
| **Hosting** | Vercel (Serverless) |

---

## 📁 Project Structure

```
SmartShopAI/
├── main.py                 # Main FastAPI application
├── database.py             # Database connection and schema
├── models.py               # Data models (Pydantic)
├── tools.py                # AI tools (product search, order placement)
├── system_prompt.txt       # Bot's system prompt
├── static/
│   └── index.html          # Frontend HTML/CSS/JavaScript
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (sensitive)
├── .env.example            # Example environment file
└── README.md               # This file
```


---

## ✨ Screenshots
<img width="1916" height="942" alt="image" src="https://github.com/user-attachments/assets/985b2c9f-1c7e-409e-b133-a623e8d51d4f" />
    
<img width="1919" height="952" alt="image" src="https://github.com/user-attachments/assets/9f89e2a2-d31f-40e2-802c-e9a90eddb2b6" />

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- OpenAI API key
- Supabase project (for production) or SQLite (for local development)
- Git installed

### Step 1: Clone the Repository

```bash
git clone https://github.com/r0nY-0017/SmartShopAI.git
cd SmartShopAI
```

### Step 2: Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables

Create a `.env` file in the root directory and add the following:

```env
# OpenAI API
OPENAI_API_KEY=your-openai-api-key

# Database (optional - SQLite will be used if not set)
DATABASE_URL=postgresql://user:password@host:port/database

```

**Setting up Supabase:**
1. Create an account at [Supabase](https://supabase.com)
2. Create a new project
3. Copy the connection string and paste it into `DATABASE_URL`

### Step 5: Run the Application

```bash
uvicorn main:app --reload
```

Open your browser and navigate to: **http://localhost:8000**

---

## ☁️ Deploy to Vercel

### Prerequisites
- GitHub account
- Vercel account

### Deployment Steps

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Deploy SmartShopAI"
   git push origin main
   ```

2. **Create a Vercel Project:**
   - Log in to [Vercel](https://vercel.com)
   - Click "New Project"
   - Connect your GitHub repository

3. **Add Environment Variables:**
   - Go to Project Settings
   - Open "Environment Variables"
   - Add:
     - `OPENAI_API_KEY` = Your API key
     - `DATABASE_URL` = Your Supabase connection string

4. **Deploy:**
   - Click the "Deploy" button
   - Vercel will automatically install dependencies and run the application

---

## 🔧 Configuration

### Customize the System Prompt

Edit the `system_prompt.txt` file to change the bot's personality, language preferences, and tool usage guidelines.

### Adjust Chat History Limit

Modify `MAX_HISTORY` in `main.py` (default: 20):

```python
MAX_HISTORY = 50  # or any other number
```

### Change Product API

Edit the `tools.py` file to use your own product API instead of DummyJSON.

---

## 🤖 Example Conversation

### Example 1: Product Search

```
👤 User: I need a laptop for programming around $800–1200.

🤖 Bot: Great! Let me ask you a few questions to find the perfect laptop:
- Do you prefer Windows, Mac, or Linux?
- How much RAM do you need? 8GB or 16GB+?

👤 User: Mac, 16GB RAM

🤖 Bot: Perfect! Here are some MacBook options within your budget:
[Product cards displayed]
```

### Example 2: Order Placement

```
👤 User: I want to buy the MacBook Pro.

🤖 Bot: Excellent choice! To complete your order, please provide:
- Full name
- Email address
- Shipping address
- Phone number

👤 User: [Provides details]

🤖 Bot: Your order has been successfully placed! Thank you for shopping with us.
```

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve frontend HTML |
| POST | `/api/chat` | Send a chat message and receive a response |
| GET | `/api/history/{user_id}` | Retrieve chat history |
| DELETE | `/api/history/{user_id}` | Delete chat history |
| GET | `/api/orders/{user_id}` | Retrieve user's orders |

---

## 🐛 Troubleshooting

### Error: "No module named 'openai'"
**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

### Error: "Invalid OpenAI API Key"
**Solution:** 
- Verify that your API key is correct in the `.env` file
- Check your API key in the OpenAI dashboard

### Error: "Database connection failed"
**Solution:**
- Verify your Supabase connection string
- If `DATABASE_URL` is not set, the app will use SQLite

### Error: "CORS error or connection issues"
**Solution:**
- Ensure FastAPI server is running (`uvicorn main:app --reload`)
- Check browser console for specific errors
- Verify all environment variables are set correctly

---

## 📚 Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [Vercel Deployment Guide](https://vercel.com/docs)
- [DummyJSON API](https://dummyjson.com/)

---

## 📝 License

This project is open-source and available under the MIT License. See the `LICENSE` file for details.

---

## 🙏 Acknowledgements

- **OpenAI** – for the GPT-4o-mini model
- **DummyJSON** – for demo product data
- **Supabase** – for PostgreSQL database hosting
- **Vercel** – for serverless deployment infrastructure

---

## 💬 Support & Contributions

Have questions or suggestions? Feel free to open an issue or submit a pull request!

**GitHub:** [r0nY-0017/SmartShopAI](https://github.com/r0nY-0017)

**Email:** [hasan15-5976@diu.edu.bd](hasan15-5976@diu.edu.bd)

---

## 🎯 Roadmap

- [ ] Add user authentication (login/signup)
- [ ] Implement product review system
- [ ] Add wishlist functionality
- [ ] Integration with more payment gateways
- [ ] Advanced search filters
- [ ] Mobile app version

---

**Happy Shopping! 🎉**

*Made with ❤️ by the [me](https://github.com/r0nY-0017/SmartShopAI)
