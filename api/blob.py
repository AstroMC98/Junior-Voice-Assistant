import os
import base64
import httpx

_BLOB_API_BASE = "https://blob.vercel-storage.com"


async def upload_image(filename: str, data: bytes) -> str:
    token = os.environ.get("BLOB_READ_WRITE_TOKEN", "")

    # Local dev fallback: return a data URL when no valid token is configured
    if not token or os.environ.get("BLOB_LOCAL_FALLBACK") == "1":
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"

    headers = {
        "authorization": f"Bearer {token}",
        "x-api-version": "7",
        "x-content-type": "image/png",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.put(
            f"{_BLOB_API_BASE}/{filename}",
            content=data,
            headers=headers,
            params={"access": "public"},
        )
        if not response.is_success:
            raise Exception(f"Blob upload failed {response.status_code}: {response.text}")
        return response.json()["url"]
