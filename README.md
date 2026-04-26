# 🏠 Smart Home Appliance Buyer Guide

A production-ready AI-powered platform for discovering and comparing smart home appliances. Search, filter, and compare 100+ devices across multiple retailers with real-time pricing.

![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.104+-green.svg)
![Bootstrap 5](https://img.shields.io/badge/bootstrap-5.3-purple.svg)

## ✨ Features

### 🔍 Smart Search
- **100+ Products**: Comprehensive database of smart home devices
- **Multi-Mode Search**:
  - **Static Mode**: Instant search from curated database (no API needed)
  - **Google Shopping**: Real-time prices via SerpAPI integration
  - **Amazon API**: Ready for Amazon Product Advertising API (optional)
- **Auto Fallback**: Seamlessly falls back if APIs are unavailable

### 🎯 Advanced Filtering
- **13 Categories**: Thermostats, Speakers, Cameras, Locks, Lights, Vacuums, and more
- **Sort Options**: Most Relevant, Highest Rated, Price Low-to-High, Price High-to-Low
- **Category Filtering**: Browse by device type

### 🛒 E-Commerce Integration
- **One-Click Buy**: Direct links to Amazon and Flipkart
- **Price Comparison**: See prices across retailers
- **Real-Time Availability**: Updated pricing from live sources

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Optional: Configure search mode
uvicorn app.main:app --reload
```

Open browser: `http://localhost:8000`

## 📚 Detailed Documentation

- **Setup & Testing Guide**: See [SETUP.md](SETUP.md)
- **Configuration Options**: See [.env.example](.env.example)

## 🏗️ Architecture

- **Backend**: FastAPI + Python 3.12
- **Frontend**: Bootstrap 5 (CDN)
- **Search Modes**: Static (100+ products), Google Shopping (real-time), Amazon API (optional)
- **Database**: In-memory products database with full text search

## 🚢 Deployment

```bash
docker-compose up --build
```

## 📝 License

MIT License - Free for personal and commercial use.

