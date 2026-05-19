import asyncio
import os
import tempfile
from functools import partial
from typing import Any


async def run_llm(fn, *args, **kwargs) -> Any:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(fn, *args, **kwargs))


async def generate_with_images(client, images: list[bytes], prompt: str, **kwargs) -> Any:
    """Upload one or more image byte arrays, generate a response, then clean up."""
    tmps: list[str] = []
    handles: list[Any] = []
    for img in images:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(img)
            tmps.append(f.name)
        handle = await run_llm(client.upload_file, tmps[-1], display_name="image.png")
        handles.append(handle)
    response = None
    try:
        response = await run_llm(client.generate, prompt, files=handles, **kwargs)
    finally:
        for handle in handles:
            try:
                await run_llm(client.delete_file, handle)
            except Exception:
                pass
        for tmp in tmps:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    return response


async def generate_with_image(client, image: bytes, prompt: str, **kwargs) -> Any:
    return await generate_with_images(client, [image], prompt, **kwargs)
