from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from shared.events import EventEnvelope


@dataclass(slots=True)
class StreamRecord:
    message_id: str
    event: EventEnvelope


class RedisStreamBroker:
    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self._client: Redis | None = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("RedisStreamBroker is not connected")
        return self._client

    async def connect(self) -> None:
        self._client = Redis.from_url(self.redis_url, decode_responses=True)
        await self.client.ping()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def create_consumer_group(self, stream: str, group: str) -> None:
        try:
            await self.client.xgroup_create(name=stream, groupname=group, id="0-0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def publish(self, stream: str, event: EventEnvelope) -> str:
        return await self.client.xadd(stream, {"data": event.model_dump_json(mode="json")})

    async def read_group(
        self,
        *,
        stream: str,
        group: str,
        consumer: str,
        count: int,
        block_ms: int,
    ) -> list[StreamRecord]:
        response = await self.client.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=count,
            block=block_ms,
        )
        return self._parse_records(response)

    async def autoclaim(
        self,
        *,
        stream: str,
        group: str,
        consumer: str,
        min_idle_ms: int,
        start_id: str = "0-0",
        count: int = 10,
    ) -> tuple[str, list[StreamRecord]]:
        response = await self.client.xautoclaim(
            name=stream,
            groupname=group,
            consumername=consumer,
            min_idle_time=min_idle_ms,
            start_id=start_id,
            count=count,
        )
        if not response:
            return start_id, []
        next_start = response[0]
        messages = response[1] if len(response) > 1 else []
        return next_start, self._parse_records([(stream, messages)])

    async def ack(self, stream: str, group: str, message_id: str) -> None:
        await self.client.xack(stream, group, message_id)

    async def get_group_lag(self, stream: str, group: str) -> int:
        groups = await self.client.xinfo_groups(stream)
        for entry in groups:
            if entry.get("name") == group:
                lag = entry.get("lag")
                return int(lag) if lag is not None else 0
        return 0

    def _parse_records(self, response: Any) -> list[StreamRecord]:
        records: list[StreamRecord] = []
        for _, messages in response:
            for message_id, fields in messages:
                raw = fields.get("data")
                if not raw:
                    continue
                event = EventEnvelope.model_validate_json(raw)
                records.append(StreamRecord(message_id=message_id, event=event))
        return records
