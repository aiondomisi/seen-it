import json
from pathlib import Path
import discord


def save_message_json(message: discord.Message):
    data = {
        attr: str(getattr(message, attr))
        for attr in dir(message)
        if not attr.startswith("_")
        and attr != "interaction"
        and not callable(getattr(message, attr))
    }

    filename = Path(__file__).resolve().parents[2] / f"{message.author.id}-message.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, default=str)

    print(f"Message saved to: {filename}")
