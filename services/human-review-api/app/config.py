from shared.config import ServiceSettings
from shared.events import ConsumerGroup


class HumanReviewSettings(ServiceSettings):
    service_name: str = "human-review-api"
    consumer_group: str = ConsumerGroup.HUMAN_REVIEW
    consumer_name: str = "human-review-api-1"
