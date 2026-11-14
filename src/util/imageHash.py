import asyncio
import io

import imagehash
from PIL import Image

MAX_SIZE = 10 * 1024 * 1024  # skip files over 10 MB
MIN_DIMENSION = 64  # skip emotes, stickers, tiny images


def _hash(data: bytes) -> str | None:
    with Image.open(io.BytesIO(data)) as img:
        if img.width < MIN_DIMENSION or img.height < MIN_DIMENSION:
            return None
        return str(imagehash.phash(img))


async def hash_attachment(attachment) -> str | None:
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        return None
    if attachment.size > MAX_SIZE:
        return None
    try:
        data = await attachment.read()
        return await asyncio.to_thread(_hash, data)
    except Exception:
        return None
