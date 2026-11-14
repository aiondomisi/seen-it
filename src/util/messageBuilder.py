import re
from datetime import datetime, timezone

import discord


def build_message(template: str, message: discord.Message, duplicates: list) -> str:
    _, _, channel_id, author_id, created_at, guild_id = duplicates[0]
    created = int(
        datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=timezone.utc)
        .timestamp()
    )
    values = {
        "author.mention": message.author.mention,
        "author.name": message.author.display_name,
        "original_author": f"<@{author_id}>",
        "created_at": f"<t:{created}:f>",
        "channel": f"<#{channel_id}>",
        "original_message": "\n".join(
            f"https://discord.com/channels/{d[5]}/{d[2]}/{d[1]}" for d in duplicates
        ),
        "guild": message.guild.name,
    }
    pattern = "|".join(re.escape(k) for k in sorted(values, key=len, reverse=True))
    return re.sub(rf"@({pattern})", lambda m: values[m.group(1)], template)
