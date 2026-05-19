from knowledge_base.voice import whisper_client


async def transcribe_audio(audio_bytes: bytes, audio_format: str = "webm") -> str:
    return await whisper_client.transcribe(audio_bytes, audio_format)
