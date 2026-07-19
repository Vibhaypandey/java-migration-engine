import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers import upload, assessment, migration, build

# ---------------------------------------------------------------------------
# Logging — configured once at import time so all modules share the same setup
# ---------------------------------------------------------------------------
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "root": {"level": "DEBUG" if settings.debug else "INFO", "handlers": ["console"]},
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown hooks (replaces deprecated on_event)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.app_name)
    logger.info("Upload dir : %s", settings.upload_dir)
    logger.info("Workspace  : %s", settings.workspace_dir)
    yield
    logger.info("Shutting down %s", settings.app_name)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_name,
    description="AI-powered Java Migration Assistant — Phase 1: file ingestion",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(upload.router)
app.include_router(assessment.router)
app.include_router(migration.router)
app.include_router(build.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
