import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone


class RealtimeBroker:
    def __init__(self):
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)

    async def publish(self, channel: str, event: str, payload: dict | None = None):
        message = json.dumps({
            "channel": channel,
            "event": event,
            "payload": payload or {},
            "published_at": datetime.now(timezone.utc).isoformat(),
        }, default=str)
        for queue in tuple(self._subscribers[channel]):
            if not queue.full():
                queue.put_nowait(message)

    async def stream(self, channel: str):
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers[channel].add(queue)
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=20)
                    yield f"event: update\ndata: {message}\n\n"
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            self._subscribers[channel].discard(queue)


broker = RealtimeBroker()
