"""
FastAPI Application Entry Point.
This is the root of the application and is responsible for creating and configuring the FastAPI application.
It runs migrations on startup to ensure the database schema is up to date.

NON-NEGOTIABLE FEATURE
This is the entry point for the FastAPI application.

Why is this inside the tools folder?
- This is a common pattern in FastAPI applications.
- It allows you to register your routes in a single location, hence, it is considered a tool in the broader context of building FastAPI applications.
- It is a single file that is easy to find and modify.
"""

from fastapi import FastAPI

from app.api.middleware import ErrorHandlerMiddleware, RateLimitMiddleware, RequestIdMiddleware
from app.api.routes_chat import router as chat_router
from app.api.routes_evals import router as evals_router
from app.api.routes_health import router as health_router
from app.api.routes_ingest import router as ingest_router
from app.api.routes_search import router as search_router
from app.api.routes_sessions import router as sessions_router
from app.api.routes_traces import router as traces_router
from app.core.logging import configure_logging


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.migrate import run_migrations
    try:
        run_migrations()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to run migrations: %s", e)
    yield

def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title='Stripe Docs RAG', version='0.1.0', lifespan=lifespan)

    # Middleware stack (outermost first)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # Routes
    app.include_router(health_router)
    app.include_router(search_router)
    app.include_router(chat_router)
    app.include_router(sessions_router)
    app.include_router(ingest_router)
    app.include_router(evals_router)
    app.include_router(traces_router)
    return app


app = create_app()
