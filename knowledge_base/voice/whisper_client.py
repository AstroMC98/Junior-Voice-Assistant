import io
from openai import AsyncOpenAI

client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global client
    if client is None:
        client = AsyncOpenAI()
    return client


async def transcribe(audio_bytes: bytes, audio_format: str = "webm") -> str:
    c = _get_client()
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = f"audio.{audio_format}"
    transcript = await c.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="text",
    )
    return transcript
