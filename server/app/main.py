from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.middleware import register_middleware
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

register_middleware(app)

app.include_router(health.router)
