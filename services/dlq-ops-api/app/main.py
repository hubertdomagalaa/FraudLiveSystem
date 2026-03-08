from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.dlq import router as dlq_router
from app.config import DlqOpsSettings
from app.stream_worker import DlqOpsStreamWorker
from shared.broker import RedisStreamBroker
from shared.cors import add_cors_middleware
from shared.database import PlatformDatabase
from shared.logging import configure_logging
from shared.observability import build_metrics_middleware, metrics_endpoint
from shared.rate_limit import InMemoryRateLimiter
from shared.security import JwtAuth
from shared.tracing import build_tracing_middleware, configure_tracing

settings = DlqOpsSettings()
configure_logging(settings.service_name, settings.log_level)
configure_tracing(settings.service_name, settings.tracing_enabled)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = PlatformDatabase(settings.postgres_dsn)
    broker = RedisStreamBroker(settings.redis_url)

    await db.connect()
    await broker.connect()

    worker = DlqOpsStreamWorker(settings=settings, db=db, broker=broker)
    await worker.start()

    app.state.db = db
    app.state.broker = broker
    app.state.worker = worker
    app.state.auth = JwtAuth(
        service_name=settings.service_name,
        enabled=settings.auth_enabled,
        secret=settings.jwt_secret,
        jwks_url=settings.jwt_jwks_url,
        algorithm=settings.jwt_algorithm,
        required_scope=settings.jwt_required_scope,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        leeway_seconds=settings.jwt_leeway_seconds,
    )
    app.state.rate_limiter = InMemoryRateLimiter(
        service_name=settings.service_name,
        enabled=settings.rate_limit_enabled,
        limit=settings.write_rate_limit_requests,
        window_seconds=settings.write_rate_limit_window_seconds,
    )

    try:
        yield
    finally:
        await worker.stop()
        await broker.close()
        await db.close()


app = FastAPI(title='DLQ Ops API', version='1.0.0', lifespan=lifespan)
add_cors_middleware(app, settings.cors_allowed_origins)
app.middleware('http')(build_tracing_middleware(settings.service_name))
app.middleware('http')(build_metrics_middleware(settings.service_name))
app.add_api_route('/metrics', metrics_endpoint, methods=['GET'])
app.include_router(dlq_router, prefix='/v1')


@app.get('/health')
async def health():
    return {'status': 'ok', 'service': settings.service_name}
