# AI Smart Home Advisor (Backend)

Production-ready FastAPI backend for the AI Smart Home Advisor.

## Features
- AI-assisted intent extraction and recommendation flow
- Smart product relevance filtering and ranking
- Google OAuth login with guest mode fallback
- Session-based auth and chat history persistence (SQLite)
- Manual search and product comparison APIs

## Tech Stack
- Python 3.10+
- FastAPI
- Uvicorn
- Authlib (Google OAuth)
- SQLite
- Requests/HTTPX

## Project Structure
- app/ : FastAPI application package
- main.py : local/entrypoint convenience launcher
- requirements.txt : Python dependencies
- Procfile : Railway process entry
- .env.example : environment template
- run.sh : optional startup script

## Local Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   pip install -r requirements.txt
3. Create env file from template:
   copy .env.example .env
4. Fill real values in .env.
5. Start app:
   uvicorn app.main:app --host 127.0.0.1 --port 8000

## Railway Deployment
1. Push repository to GitHub.
2. In Railway, create a new project from your GitHub repo.
3. Set root directory to backend (if monorepo).
4. Railway will use Procfile automatically:
   web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
5. Add environment variables in Railway settings:
   - GROQ_API_KEY
   - SERPAPI_KEY
   - GOOGLE_CLIENT_ID
   - GOOGLE_CLIENT_SECRET
   - GOOGLE_REDIRECT_URI
   - SESSION_SECRET_KEY
   - SEARCH_MODE (optional)
   - REQUEST_TIMEOUT (optional)
   - SESSION_COOKIE_SECURE=true

## Required Environment Variables
- GROQ_API_KEY: Groq API key
- SERPAPI_KEY: SerpAPI key
- GOOGLE_CLIENT_ID: Google OAuth client ID
- GOOGLE_CLIENT_SECRET: Google OAuth client secret
- GOOGLE_REDIRECT_URI: OAuth callback URL
- SESSION_SECRET_KEY: secret for session signing

## Security Notes
- Do not commit `.env`.
- Rotate keys before production if they were ever exposed.
- Keep `SESSION_COOKIE_SECURE=true` in production (HTTPS).
