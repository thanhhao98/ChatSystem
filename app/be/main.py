"""Main entrypoint for ChatSystem Backend Server.
Configures FastAPI app, CORS middleware for Frontend, and route registration.
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.be.api import api_router


def create_app() -> FastAPI:
    """Application factory configuring routes and middlewares."""
    application = FastAPI(
        title="ChatSystem — SGOD Assistant Backend API",
        description="Backend API phục vụ Chatbot AI hỗ trợ gọi 22 tools SGOD thật và xác thực đa tầng.",
        version="2.0.0",
    )

    # ── CORS Middleware for Frontend React / Vite ─────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite default
            "http://127.0.0.1:5173",
            "http://localhost:3000",  # CRA default
            "http://127.0.0.1:3000",
            "*",                      # Allow all during internal testing
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register Routers ──────────────────────────────────────────────────────
    application.include_router(api_router)

    return application


app = create_app()

if __name__ == "__main__":
    uvicorn.run("app.be.main:app", host="0.0.0.0", port=8000, reload=True)
