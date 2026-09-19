from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import auth, health, workflows
from core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Enterprise Agentic Workflow Platform",
    description=(
        "A security-first agentic workflow platform that enables LLMs to "
        "safely execute multi-step enterprise operations through MCP, with "
        "policy enforcement, risk-aware authorization, verification, "
        "recovery, and human-in-the-loop controls."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(workflows.router)
