"""UrbanShift API — FastAPI entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.session import router as session_router
from routes.profile import router as profile_router

app = FastAPI(
    title="UrbanShift API",
    description="AI-powered urban migrant assistance platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────
app.include_router(session_router)
app.include_router(profile_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "urbanshift-api", "version": "0.1.0"}
