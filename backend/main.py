"""Railway entrypoint convenience module.

This file allows running `python main.py` in local/dev contexts while
keeping the app object inside `app.main`.
"""

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
