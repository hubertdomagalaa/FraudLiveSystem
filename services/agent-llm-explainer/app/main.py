from fastapi import FastAPI

from app.api.routes.agent import router as agent_router
from app.config import LLMExplainerSettings
from shared.logging import configure_logging
from shared.observability import build_metrics_middleware, metrics_endpoint

settings = LLMExplainerSettings()
configure_logging(settings.service_name, settings.log_level)

app = FastAPI(title="LLM Explanation Agent", version="0.1.0")
app.middleware("http")(build_metrics_middleware(settings.service_name))
app.add_api_route("/metrics", metrics_endpoint, methods=["GET"])
app.include_router(agent_router, prefix="/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
