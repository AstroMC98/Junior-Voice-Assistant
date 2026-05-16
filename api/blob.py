import os
import httpx

_BLOB_API_BASE = "https://blob.vercel-storage.com"


async def upload_image(filename: str, data: bytes) -> str:
    token = os.environ["BLOB_READ_WRITE_TOKEN"]
    headers = {
        "Authorization": f"Bearer {token}",
        "x-content-type": "image/png",
        "x-api-version": "7",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.put(
            f"{_BLOB_API_BASE}/{filename}",
            content=data,
            headers=headers,
            params={"access": "public"},
        )
        response.raise_for_status()
        return response.json()["url"]
