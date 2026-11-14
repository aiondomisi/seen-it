import aiosqlite
from util.normalizedUrl import normalize_url
from util.resolverUrl import resolve_url
import os

DATABASE = os.environ.get("DATABASE_PATH", "data/seenit.db")


MIGRATIONS = [
    # V1
    """ 
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT NOT NULL,
        channel_id TEXT NOT NULL,
        message_id TEXT NOT NULL UNIQUE,
        author_id TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        original_url TEXT NOT NULL,
        normalized_url TEXT NOT NULL,
        FOREIGN KEY (message_id)
            REFERENCES messages(id)
            ON DELETE CASCADE
    );
     CREATE TABLE IF NOT EXISTS duplicate_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        original_message_id TEXT NOT NULL,
        content_type TEXT NOT NULL,
        detected_at TEXT NOT NULL
    )
    """,
    # V2 add image table
    """
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            hash TEXT NOT NULL,
            FOREIGN KEY (message_id)
                REFERENCES messages(id)
                ON DELETE CASCADE
        );
    """,
]


async def init_database():
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("PRAGMA user_version") as cur:
            (version,) = await cur.fetchone()

            for i, sql in enumerate(MIGRATIONS[version:], start=version + 1):
                await db.executescript("BEGIN;" + sql)
                await db.execute(f"PRAGMA user_version = {i}")
                await db.commit()


async def save_message(
    guild_id: int, channel_id: int, message_id: int, author_id: int, created_at: str
) -> int | None:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            """
            INSERT INTO messages (
                guild_id,
                channel_id,
                message_id,
                author_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(guild_id),
                str(channel_id),
                str(message_id),
                str(author_id),
                created_at,
            ),
        )

        await db.commit()
        return cursor.lastrowid


async def save_link(
    message_id: int,
    original_url: str,
):
    async with aiosqlite.connect(DATABASE) as db:
        normalized_url = normalize_url(await resolve_url(original_url))
        await db.execute(
            """
            INSERT INTO links (
                message_id,
                original_url,
                normalized_url
            )
            VALUES (?, ?, ?)
            """,
            (
                str(message_id),
                str(original_url),
                normalized_url,
            ),
        )

        await db.commit()


async def find_link(url: str, guild_id: int, channel_id: int):
    normalized_url = normalize_url(await resolve_url(url))

    channel_filter = ""
    params = [normalized_url, str(guild_id)]
    if os.environ.get("CHECKED_BY_CHANNEL", "").lower() == "true":
        channel_filter = "AND messages.channel_id = ?"
        params.append(str(channel_id))

    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
            f"""
            SELECT
                links.original_url,
                messages.message_id,
                messages.channel_id,
                messages.author_id,
                messages.created_at,
                messages.guild_id
            FROM links
            JOIN messages
                ON links.message_id = messages.id
            WHERE links.normalized_url = ?
            AND messages.guild_id = ?
            {channel_filter}
            LIMIT 1
            """,
            params,
        ) as cursor:
            return await cursor.fetchone()


async def save_image(message_id: int, image_hash: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT INTO images (message_id, hash) VALUES (?, ?)",
            (message_id, image_hash),
        )
        await db.commit()


async def find_image(image_hash: str, guild_id: int, channel_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        channel_filter = ""
        params = [str(guild_id)]
        if os.environ.get("CHECKED_BY_CHANNEL", "").lower() == "true":
            channel_filter = "AND messages.channel_id = ?"
            params.append(str(channel_id))

        async with db.execute(
            f"""
            SELECT
                images.hash,
                messages.message_id,
                messages.channel_id,
                messages.author_id,
                messages.created_at,
                messages.guild_id
            FROM images
            JOIN messages
                ON images.message_id = messages.id
            WHERE messages.guild_id = ?
            {channel_filter}
            """,
            params,
        ) as cursor:
            rows = await cursor.fetchall()

    threshold = int(os.environ.get("IMAGE_COMPARISON_THRESHOLD", "5"))

    target = int(image_hash, 16)
    for row in rows:
        if bin(int(row[0], 16) ^ target).count("1") <= threshold:
            return row
    return None
