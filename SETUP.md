# Smart Home Appliance Buyer Guide - Setup & Testing Guide

## 📋 Prerequisites

- Python 3.8+
- pip (Python package manager)
- Git (optional)

## 🚀 Quick Start (5 minutes)

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Installed packages:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `jinja2` - Template engine
- `python-multipart` - Form data parsing
- `requests` - HTTP library for SerpAPI
- `scikit-learn` - ML utilities
- `python-dotenv` - Environment variable loading

### 2. Configuration

Copy the example environment file:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

**Default configuration** (`.env`):
```
SEARCH_MODE=static
# No API key needed for static mode
```

### 3. Run the Backend

```bash
cd backend
uvicorn app.main:app --reload
```

**Output should show:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### 4. Open in Browser

Navigate to: **http://localhost:8000**

You should see the Smart Home Guide search interface with:
- Search bar for appliances
- Category dropdown (Smart Thermostats, Speakers, Cameras, etc.)
- Sort options (Relevance, Rating, Price)
- Popular search buttons

## 🧪 Testing the System

### Test 1: Search for Products

1. Type "Smart Lock" in search bar → Click "Search Smart Products"
2. Should see 3-4 smart lock products with:
   - Product cards with images
   - ⭐ Ratings (e.g., 4.5/5)
   - Price in INR (₹X,XXX format)
   - Feature tags (WiFi, Mobile App, etc.)
   - "Amazon" and "Flipkart" buy buttons

### Test 2: Filter by Category

1. Click Category dropdown → Select "Smart Locks"
2. Leave search blank (or enter "smart")
3. Should see all smart locks sorted by relevance

### Test 3: Sort Results

1. Search for "WiFi" → See 10+ results
2. Click Sort dropdown → Try each option:
   - "Most Relevant" → Results match query
   - "Highest Rated" → Results ordered by rating (5.0 stars first)
   - "Price: Low to High" → Results ₹3,735 to ₹165,917
   - "Price: High to Low" → Reverse order

### Test 4: Buy Buttons

1. Search for any product
2. Click "Amazon" button → Opens Amazon link in new tab
3. Click "Flipkart" button → Opens Flipkart link in new tab

### Test 5: Popular Searches

1. Click any popular search button (e.g., "Smart Lock", "Robot Vacuum")
2. Auto-populated search with results

### Test 6: API Endpoints

In terminal (or browser):

**Health Check:**
```bash
curl http://localhost:8000/api/health
# Output: {"status":"ok","search_mode":"static"}
```

**Get Categories:**
```bash
curl http://localhost:8000/api/categories
# Output: {"categories":["Smart Locks","Smart Speakers","Security Cameras", ...]}
```

## 🌐 Advanced: Use Live Google Shopping Search

### Get SerpAPI Key

1. Visit: https://serpapi.com
2. Sign up (free account includes 100 queries/month)
3. Copy your API key from dashboard

### Update Configuration

Edit `.env`:
```
SEARCH_MODE=google
SERPAPI_KEY=your_api_key_from_serpapi_here
```

### Restart Backend

```bash
# Stop current server (Ctrl+C)
# Then restart:
uvicorn app.main:app --reload
```

### Test Google Shopping

Search for "Smart Thermostat" → Results now show real-time Google Shopping prices from:
- Amazon
- Best Buy
- Walmart
- Other retailers

**Fallback Behavior:** If SerpAPI fails, automatically uses static database

## 📦 Database Structure

### Products Database (`products_db.py`)

- **100+ Products** with metadata:
  - Name, Category, Description
  - Price (INR), Rating (1-5 stars)
  - Features (list), Keywords (list)
  - Image URL, Amazon/Flipkart links
  - Badge (Top Rated, Best Seller)

### Categories (13 types):
- Smart Thermostats
- Smart Speakers
- Security Cameras
- Smart Locks
- Smart Lights
- Air Purifiers
- Robot Vacuums
- Video Doorbells
- Smart Plugs
- Smart Appliances
- Motion Sensors
- Smart Hubs
- Door/Window Sensors

## 🔍 Search Modes

### Mode 1: Static (Default)
- **Speed:** Instant (no API calls)
- **Results:** Curated 100+ products
- **Setup:** No configuration needed
- **Best for:** Development, testing, offline

### Mode 2: Google Shopping (SerpAPI)
- **Speed:** ~1-2 seconds (real-time)
- **Results:** Live Google Shopping listings
- **Setup:** Requires SerpAPI key
- **Best for:** Production, current prices

### Mode 3: Amazon API (Stub)
- **Status:** Ready for implementation
- **Requires:** AWS PA-API 5.0 credentials
- **Best for:** Amazon-exclusive results

## 🛠️ Troubleshooting

### Port 8000 Already in Use

```bash
# Find process using port 8000
# Windows:
netstat -ano | findstr :8000

# macOS/Linux:
lsof -i :8000

# Kill the process and try again
```

### Missing Dependencies

```bash
pip install -r requirements.txt --upgrade
```

### Templates Not Found

Ensure you're running from the `backend` directory:
```bash
cd backend
uvicorn app.main:app --reload
```

### SerpAPI Errors

- Check API key is correct in `.env`
- Verify free tier hasn't exceeded 100 queries/month
- Check internet connection
- View logs: Server should show fallback message

## 📊 File Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI endpoints
│   ├── products_db.py       # 100+ product database
│   ├── search_service.py    # Search logic (3 modes)
│   ├── templates/
│   │   ├── base.html        # Base template (CSS, navbar)
│   │   ├── index.html       # Home page (search form)
│   │   └── recommendations.html  # Results page (product cards)
│   └── static/              # CSS/JS (future)
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker config
└── .env                    # Configuration (git-ignored)
```

## 🚢 Docker Deployment (Optional)

Build and run with Docker:

```bash
docker-compose up --build
```

Access at: http://localhost:8000

## 📈 Next Steps

### Phase 1 (Current) ✅
- ✅ Backend API with search
- ✅ 100+ product database
- ✅ HTML/Bootstrap frontend
- ✅ Static search mode

### Phase 2 (Recommended)
- [ ] SerpAPI integration testing
- [ ] Product images optimization
- [ ] Pagination for large result sets
- [ ] Search suggestions/autocomplete
- [ ] Dark mode toggle

### Phase 3 (Advanced)
- [ ] PostgreSQL database integration
- [ ] User accounts & wishlists
- [ ] Advanced filtering (price range, brand, features)
- [ ] Trending products calculation
- [ ] Amazon PA-API integration
- [ ] Unit & integration tests

### Phase 4 (Production)
- [ ] Caching with Redis
- [ ] Deployment to cloud (Heroku, AWS, etc.)
- [ ] Domain & SSL certificate
- [ ] Analytics integration
- [ ] Mobile app

## 📞 Support

- **FastAPI Docs:** http://localhost:8000/docs
- **SerpAPI Docs:** https://serpapi.com/docs
- **Bootstrap Docs:** https://getbootstrap.com/docs
- **Jinja2 Docs:** https://jinja.palletsprojects.com

Happy smart home shopping! 🏠✨
