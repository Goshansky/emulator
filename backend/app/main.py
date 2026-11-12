"""FastAPI-приложение эмулятора процессора.

Гарвардская архитектура, трёхадресные команды, 16-битные знаковые данные.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
).split(",")

app = FastAPI(title="Emulator API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
