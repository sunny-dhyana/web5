import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import admin, auth, disputes, orders, payouts, products, users, wallet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Mercury Marketplace API...")
    init_db()
    logger.info("Database ready")
    yield
    logger.info("Shutting down Mercury Marketplace API")


app = FastAPI(
    title="Mercury Marketplace API",
    description="Backend for Mercury — a modern online marketplace platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(wallet.router, prefix="/api/wallet", tags=["Wallet"])
app.include_router(disputes.router, prefix="/api/disputes", tags=["Disputes"])
app.include_router(payouts.router, prefix="/api/payouts", tags=["Payouts"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

FRONTEND_DIR = settings.frontend_build_dir
FRONTEND_ASSETS = os.path.join(FRONTEND_DIR, "assets")

if os.path.isdir(FRONTEND_ASSETS):
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS), name="static-assets")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Mercury Marketplace"}


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(request: Request, full_path: str):
    index_html = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index_html):
        return FileResponse(index_html)
    return JSONResponse(
        status_code=503,
        content={"detail": "Frontend not built. Run 'npm run build' in the frontend directory."},
    )
