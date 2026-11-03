"""Main entrypoint for ChatSystem Backend Server.
Configures FastAPI app, CORS middleware for Frontend, and route registration.
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.be import config
from app.be.routes import auth_router, chat_router, tools_router
from app.be.schemas import HealthResponse

app = FastAPI(
    title="ChatSystem — SGOD Assistant Backend API",
    description="Backend API phục vụ Chatbot AI hỗ trợ gọi 22 tools SGOD thật và xác thực đa tầng.",
    version="2.0.0",
)

# ── CORS Middleware for Frontend React / Vite ─────────────────────────────────
app.add_middleware(
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

# ── Register Routers ─────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(tools_router)


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Kiểm tra tình trạng hoạt động của máy chủ Backend và cấu hình kết nối."""
    return HealthResponse(
        status="ok",
        sgod_gateway=config.SGOD_BASE_URL,
        gemini_configured=bool(config.GEMINI_API_KEY),
        gemini_model=config.GEMINI_MODEL,
    )


if __name__ == "__main__":
    uvicorn.run("app.be.main:app", host="0.0.0.0", port=8000, reload=True)
