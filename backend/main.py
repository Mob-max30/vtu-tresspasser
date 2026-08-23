from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import (
    routes_project,
    routes_agent,
    routes_results,
    routes_analytics,
    routes_webcmd_poc,
    routes_live_results,
)
from database.database import init_db

app = FastAPI(title="VTU Result Intelligence Agent")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    routes_project.router,
    prefix="/api/project",
    tags=["project"],
)

app.include_router(
    routes_agent.router,
    prefix="/api/agent",
    tags=["agent"],
)

app.include_router(
    routes_results.router,
    prefix="/api/results",
    tags=["results"],
)

app.include_router(
    routes_analytics.router,
    prefix="/api/analytics",
    tags=["analytics"],
)

app.include_router(
    routes_webcmd_poc.router,
    prefix="/api/webcmd-poc",
    tags=["webcmd-poc"],
)

app.include_router(
    routes_live_results.router,
    prefix="/api/results-live",
    tags=["live-results"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}