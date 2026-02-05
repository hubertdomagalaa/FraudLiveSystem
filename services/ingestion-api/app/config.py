from shared.config import ServiceSettings


class IngestionSettings(ServiceSettings):
    service_name: str = "ingestion-api"
    queue_backend: str = "noop"
    queue_url: str | None = None
