import os
from upstash_redis import Redis
from api.models import Guide

_client: Redis | None = None


def _get_client() -> Redis:
    global _client
    if _client is None:
        _client = Redis(
            url=os.environ["KV_REST_API_URL"],
            token=os.environ["KV_REST_API_TOKEN"],
        )
    return _client


async def get_guide(guide_id: str) -> Guide | None:
    raw = _get_client().get(f"guide:{guide_id}")
    if raw is None:
        return None
    if isinstance(raw, dict):
        return Guide(**raw)
    return Guide.model_validate_json(raw)


async def save_guide(guide: Guide) -> None:
    _get_client().set(f"guide:{guide.id}", guide.model_dump_json())
