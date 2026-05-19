import os

_REQUIRED_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}


class _LazyProxy:
    """Defers LLMClient construction until first method call — avoids import-time auth errors."""

    def __init__(self, provider: str, model: str) -> None:
        self._provider = provider
        self._model = model
        self._client = None

    def _get(self):
        if self._client is None:
            env_var = _REQUIRED_KEYS.get(self._provider)
            if env_var and not os.environ.get(env_var):
                raise RuntimeError(
                    f"{env_var} is required for the '{self._provider}' provider. "
                    f"Add it to your .env.local file."
                )
            from abstractionClient import LLMClient
            self._client = LLMClient(provider=self._provider, model=self._model)
        return self._client

    def generate(self, *args, **kwargs):
        return self._get().generate(*args, **kwargs)

    def upload_file(self, *args, **kwargs):
        return self._get().upload_file(*args, **kwargs)

    def delete_file(self, *args, **kwargs):
        return self._get().delete_file(*args, **kwargs)


ingestion_client = _LazyProxy("gemini", "gemini-2.5-flash")
query_client_sonnet = _LazyProxy("claude", "claude-sonnet-4-6")
query_client_haiku = _LazyProxy("claude", "claude-haiku-4-5-20251001")


def make_client(provider: str, model: str, **kwargs):
    """Construct a one-off LLMClient — use for per-request options like api_key."""
    from abstractionClient import LLMClient
    return LLMClient(provider=provider, model=model, **kwargs)
